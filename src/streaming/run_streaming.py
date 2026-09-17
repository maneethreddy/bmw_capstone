import argparse
import logging
import os

from src.streaming.pipeline import build_streaming_pipeline
from src.streaming.spark_session import SparkSessionConfig, create_spark_session
from src.sinks.cloudwatch import CloudWatchMetrics
from src.sinks.s3_writer import S3TelemetryWriter
from src.sinks.snowflake_writer import SnowflakeTelemetryWriter

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the BMW PySpark Structured Streaming pipeline.")
    parser.add_argument("--bootstrap-servers", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    parser.add_argument("--topic", default=os.getenv("KAFKA_TOPIC", "bmw-telemetry"))
    parser.add_argument("--window-duration", default=os.getenv("SPARK_WINDOW_DURATION", "5 minutes"))
    parser.add_argument("--watermark-delay", default=os.getenv("SPARK_WATERMARK_DELAY", "2 minutes"))
    parser.add_argument("--checkpoint", default=os.getenv("SPARK_CHECKPOINT_LOCATION", "./checkpoints/bmw-telemetry"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    spark = create_spark_session(SparkSessionConfig())
    _valid_events, invalid_events, aggregates = build_streaming_pipeline(
        spark,
        args.bootstrap_servers,
        args.topic,
        args.window_duration,
        args.watermark_delay,
    )
    s3_writer = S3TelemetryWriter() if os.getenv("S3_BUCKET") else None
    snowflake_writer = SnowflakeTelemetryWriter() if os.getenv("SNOWFLAKE_ACCOUNT") else None
    metrics = CloudWatchMetrics() if os.getenv("CLOUDWATCH_ENABLED", "false").lower() == "true" else None

    if metrics:
        metrics.put("ApplicationStatus", 1)

    def invalid_outputs(dataframe, batch_id):
        count = dataframe.count()
        if count:
            dataframe.show(truncate=False)
        if metrics:
            metrics.put("InvalidRecords", count)

    def optional_outputs(dataframe, batch_id):
        records = [row.asDict(recursive=True) for row in dataframe.collect()]
        if s3_writer:
            s3_writer.write_records(records, batch_id, "aggregated")
        if snowflake_writer:
            snowflake_writer.write_records(records)
        if metrics:
            metrics.put("AggregatedRecords", len(records))

    invalid_query = invalid_events.writeStream.outputMode("append").foreachBatch(invalid_outputs).option(
        "checkpointLocation", f"{args.checkpoint}/invalid"
    ).start()
    aggregate_query = aggregates.writeStream.outputMode("update").format("console").option("truncate", "false").option(
        "checkpointLocation", args.checkpoint
    ).start()
    output_query = aggregates.writeStream.outputMode("update").foreachBatch(optional_outputs).option(
        "checkpointLocation", f"{args.checkpoint}/outputs"
    ).start()
    try:
        aggregate_query.awaitTermination()
    except Exception:
        logger.exception("Streaming query failed")
        if metrics:
            metrics.put("StreamingErrors", 1)
        raise
    finally:
        if metrics:
            metrics.put("ApplicationStatus", 0)
        output_query.stop()
        invalid_query.stop()


if __name__ == "__main__":
    main()
