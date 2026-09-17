from typing import Any, Dict, Tuple

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    avg,
    col,
    count,
    from_json,
    lit,
    max as spark_max,
    regexp_replace,
    sum as spark_sum,
    trim,
    to_timestamp,
    upper,
    when,
    window,
)
from pyspark.sql.types import DoubleType, StringType, StructField, StructType


FAULT_CODES = ["NONE", "TEMP_HIGH", "BATTERY_LOW", "ENGINE_FAULT"]


def telemetry_schema() -> StructType:
    return StructType(
        [
            StructField("vehicle_id", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("speed", DoubleType(), True),
            StructField("battery_level", DoubleType(), True),
            StructField("temperature", DoubleType(), True),
            StructField("fault_code", StringType(), True),
        ]
    )


def read_kafka_events(spark: SparkSession, bootstrap_servers: str, topic: str) -> DataFrame:
    return spark.readStream.format("kafka").option("kafka.bootstrap.servers", bootstrap_servers).option(
        "subscribe", topic
    ).option("startingOffsets", "latest").load()


def parse_and_validate_events(
    raw_stream: DataFrame, watermark_delay: str = "2 minutes"
) -> Tuple[DataFrame, DataFrame]:
    parsed = raw_stream.selectExpr("CAST(value AS STRING) AS json_payload", "timestamp AS kafka_timestamp").withColumn(
        "event", from_json(col("json_payload"), telemetry_schema())
    )
    invalid_json = parsed.filter(col("event").isNull()).select(
        "json_payload", lit("malformed_json").alias("error_reason"), "kafka_timestamp"
    )

    events = parsed.filter(col("event").isNotNull()).select("event.*", "json_payload", "kafka_timestamp")
    events = events.withColumn("vehicle_id", upper(trim(col("vehicle_id"))))
    events = events.withColumn("fault_code", upper(regexp_replace(trim(col("fault_code")), "-", "_")))
    events = events.withColumn("event_timestamp", to_timestamp(col("timestamp")))

    invalid_values = events.filter(
        col("vehicle_id").isNull()
        | (col("vehicle_id") == "")
        | (~col("vehicle_id").rlike(r"^BMW-[A-Z0-9-]+$"))
        | col("event_timestamp").isNull()
        | (~col("timestamp").rlike(r"(Z|[+-][0-9]{2}:[0-9]{2})$"))
        | col("speed").isNull()
        | (col("speed") < 0)
        | (col("speed") > 250)
        | col("battery_level").isNull()
        | (col("battery_level") < 0)
        | (col("battery_level") > 100)
        | col("temperature").isNull()
        | (col("temperature") < -20)
        | (col("temperature") > 120)
        | col("fault_code").isNull()
        | (~col("fault_code").isin(FAULT_CODES))
    ).select("json_payload", lit("invalid_telemetry_values").alias("error_reason"), "kafka_timestamp")

    valid = events.filter(
        col("vehicle_id").isNotNull()
        & (col("vehicle_id") != "")
        & col("vehicle_id").rlike(r"^BMW-[A-Z0-9-]+$")
        & col("event_timestamp").isNotNull()
        & col("timestamp").rlike(r"(Z|[+-][0-9]{2}:[0-9]{2})$")
        & col("speed").between(0, 250)
        & col("battery_level").between(0, 100)
        & col("temperature").between(-20, 120)
        & col("fault_code").isin(FAULT_CODES)
    ).withWatermark("event_timestamp", watermark_delay).dropDuplicates(["vehicle_id", "event_timestamp"])

    return valid, invalid_json.unionByName(invalid_values)


def aggregate_events(valid_events: DataFrame, window_duration: str = "5 minutes") -> DataFrame:
    """Aggregate already-watermarked events by event-time window and vehicle."""
    return valid_events.groupBy(window(col("event_timestamp"), window_duration), col("vehicle_id")).agg(
        avg("speed").alias("average_speed"),
        avg("battery_level").alias("average_battery_level"),
        spark_max("temperature").alias("maximum_temperature"),
        count(lit(1)).alias("event_count"),
        spark_sum(when(col("fault_code") != "NONE", 1).otherwise(0)).alias("fault_count"),
    ).select(
        col("vehicle_id"),
        col("window.start").alias("window_start"),
        col("window.end").alias("window_end"),
        col("average_speed"),
        col("average_battery_level"),
        col("maximum_temperature"),
        col("fault_count"),
        col("event_count"),
    )


def build_streaming_pipeline(
    spark: SparkSession,
    bootstrap_servers: str,
    topic: str,
    window_duration: str = "5 minutes",
    watermark_delay: str = "2 minutes",
) -> Tuple[DataFrame, DataFrame, DataFrame]:
    raw_stream = read_kafka_events(spark, bootstrap_servers, topic)
    valid_events, invalid_events = parse_and_validate_events(raw_stream, watermark_delay)
    return valid_events, invalid_events, aggregate_events(valid_events, window_duration)
