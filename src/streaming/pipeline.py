"""PySpark Structured Streaming pipeline functions.

This module assembles the end-to-end streaming pipeline:

1. :func:`read_kafka_events` — subscribe to the Kafka topic.
2. :func:`parse_and_validate_events` — deserialise JSON, apply schema,
   normalise fields, and split the stream into valid / invalid branches.
3. :func:`aggregate_events` — compute 5-minute tumbling window aggregates
   per vehicle (average speed, battery level, max temperature, fault count).
4. :func:`build_streaming_pipeline` — convenience wrapper that composes
   all three steps.

Example::

    from src.streaming.spark_session import SparkSessionConfig, create_spark_session
    from src.streaming.pipeline import build_streaming_pipeline

    spark = create_spark_session(SparkSessionConfig())
    valid, invalid, aggregates = build_streaming_pipeline(
        spark, "localhost:9092", "bmw-telemetry"
    )
"""

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
    """Return the PySpark schema for a raw BMW telemetry event.

    Returns:
        A :class:`~pyspark.sql.types.StructType` with six fields:
        ``vehicle_id``, ``timestamp``, ``speed``, ``battery_level``,
        ``temperature``, and ``fault_code``.
    """
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
    """Create a Kafka readStream starting from the latest offsets.

    Args:
        spark: Active :class:`~pyspark.sql.SparkSession`.
        bootstrap_servers: Comma-separated Kafka broker addresses
            (e.g. ``"localhost:9092"``).
        topic: Name of the Kafka topic to subscribe to.

    Returns:
        An unstarted streaming :class:`~pyspark.sql.DataFrame` with the
        raw Kafka columns (``key``, ``value``, ``timestamp``, etc.).
    """
    return (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap_servers)
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .option("failOnDataLoss", "false")
        .load()
    )


def parse_and_validate_events(
    raw_stream: DataFrame, watermark_delay: str = "2 minutes"
) -> Tuple[DataFrame, DataFrame]:
    """Parse, normalise, and validate raw Kafka events.

    The function performs the following steps:

    1. Casts the Kafka ``value`` column to a JSON string and parses it
       against :func:`telemetry_schema`.
    2. Routes malformed JSON to the *invalid* branch.
    3. Normalises ``vehicle_id`` (upper-case, trimmed) and
       ``fault_code`` (upper-case, dashes replaced by underscores).
    4. Applies field-level range and format checks; invalid records are
       routed to the *invalid* branch.
    5. Applies an event-time watermark and deduplicates on
       ``(vehicle_id, event_timestamp)``.

    Args:
        raw_stream: Raw Kafka streaming DataFrame from
            :func:`read_kafka_events`.
        watermark_delay: Maximum late-arrival tolerance as a Spark
            interval string (e.g. ``"2 minutes"``).

    Returns:
        A two-tuple ``(valid_events, invalid_events)``:

        - **valid_events** — watermarked, deduplicated DataFrame ready
          for aggregation.
        - **invalid_events** — DataFrame with columns
          ``json_payload``, ``error_reason``, and ``kafka_timestamp``.
    """
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
    """Aggregate already-watermarked events by event-time window and vehicle.

    Groups events into tumbling windows and computes per-vehicle KPIs:
    average speed, average battery level, maximum temperature, total event
    count, and fault count.

    Args:
        valid_events: Watermarked streaming DataFrame produced by
            :func:`parse_and_validate_events`. Must have an
            ``event_timestamp`` column with an active watermark.
        window_duration: Tumbling window size as a Spark interval string
            (e.g. ``"5 minutes"``).

    Returns:
        Streaming DataFrame with columns: ``vehicle_id``,
        ``window_start``, ``window_end``, ``average_speed``,
        ``average_battery_level``, ``maximum_temperature``,
        ``fault_count``, ``event_count``.
    """
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
    """Convenience wrapper that composes the full streaming pipeline.

    Calls :func:`read_kafka_events`, :func:`parse_and_validate_events`,
    and :func:`aggregate_events` in sequence.

    Args:
        spark: Active :class:`~pyspark.sql.SparkSession`.
        bootstrap_servers: Comma-separated Kafka broker addresses.
        topic: Kafka topic name.
        window_duration: Tumbling window size (default ``"5 minutes"``).
        watermark_delay: Late-data tolerance (default ``"2 minutes"``).

    Returns:
        A three-tuple ``(valid_events, invalid_events, aggregates)``:

        - **valid_events** — validated, watermarked raw events.
        - **invalid_events** — rejected events with error reasons.
        - **aggregates** — windowed vehicle KPI aggregates.
    """
    raw_stream = read_kafka_events(spark, bootstrap_servers, topic)
    valid_events, invalid_events = parse_and_validate_events(raw_stream, watermark_delay)
    return valid_events, invalid_events, aggregate_events(valid_events, window_duration)
