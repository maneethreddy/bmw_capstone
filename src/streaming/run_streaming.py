"""BMW PySpark Structured Streaming runner.

Architecture
------------
Telemetry Generator → Kafka → PySpark readStream
    → JSON parse + schema → validation → normalization
    → event-time watermark → window aggregation
    → console (always)
    → S3 curated Parquet (when S3_BUCKET is set)
    → CloudWatch metrics (when CLOUDWATCH_ENABLED=true)

Snowflake is intentionally not used; Athena queries the curated S3 data.

Environment variables (see configs/sample.env)
-----------------------------------------------
KAFKA_BOOTSTRAP_SERVERS  default: localhost:9092
KAFKA_TOPIC              default: bmw-telemetry
SPARK_MASTER             default: local[*]
SPARK_WINDOW_DURATION    default: 5 minutes
SPARK_WATERMARK_DELAY    default: 2 minutes
SPARK_CHECKPOINT_LOCATION  default: ./checkpoints/bmw-telemetry
S3_BUCKET                required for S3 sink (leave blank to skip)
AWS_REGION               default: us-east-1
CLOUDWATCH_ENABLED       set to 'true' to emit metrics
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import datetime, timezone

from src.streaming.pipeline import build_streaming_pipeline
from src.streaming.spark_session import SparkSessionConfig, create_spark_session
from src.sinks.cloudwatch import CloudWatchMetrics
from src.sinks.s3_writer import S3TelemetryWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the BMW PySpark Structured Streaming pipeline."
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    )
    parser.add_argument(
        "--topic",
        default=os.getenv("KAFKA_TOPIC", "bmw-telemetry"),
    )
    parser.add_argument(
        "--window-duration",
        default=os.getenv("SPARK_WINDOW_DURATION", "5 minutes"),
    )
    parser.add_argument(
        "--watermark-delay",
        default=os.getenv("SPARK_WATERMARK_DELAY", "2 minutes"),
    )
    parser.add_argument(
        "--checkpoint",
        default=os.getenv("SPARK_CHECKPOINT_LOCATION", "./checkpoints/bmw-telemetry"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    logger.info("Starting BMW Connected Vehicle Streaming pipeline")
    logger.info(
        "Config: window=%s  watermark=%s  topic=%s  brokers=%s  checkpoint=%s",
        args.window_duration,
        args.watermark_delay,
        args.topic,
        args.bootstrap_servers,
        args.checkpoint,
    )

    spark = create_spark_session(SparkSessionConfig())

    _valid_events, invalid_events, aggregates = build_streaming_pipeline(
        spark,
        args.bootstrap_servers,
        args.topic,
        args.window_duration,
        args.watermark_delay,
    )

    # ---- Optional sinks ------------------------------------------------
    s3_bucket = os.getenv("S3_BUCKET")
    s3_writer = S3TelemetryWriter() if s3_bucket else None
    if s3_writer:
        logger.info("S3 sink enabled: bucket=%s region=%s", s3_bucket, os.getenv("AWS_REGION", "us-east-1"))
    else:
        logger.info("S3 sink disabled (S3_BUCKET not set)")

    cloudwatch_enabled = os.getenv("CLOUDWATCH_ENABLED", "false").lower() == "true"
    metrics: CloudWatchMetrics | None = CloudWatchMetrics() if cloudwatch_enabled else None
    if metrics:
        logger.info("CloudWatch metrics enabled")
        metrics.put_application_status(running=True)
        metrics.log_event("BMW streaming pipeline started")
    else:
        logger.info("CloudWatch metrics disabled (set CLOUDWATCH_ENABLED=true to enable)")

    # ---- Streaming queries ----------------------------------------------

    def process_invalid(dataframe, batch_id: int) -> None:
        count = dataframe.count()
        if count:
            logger.warning("Batch %d: %d invalid records", batch_id, count)
            dataframe.show(truncate=False)
        if metrics:
            metrics.emit_batch_metrics(invalid_records=count)

    def process_aggregates(dataframe, batch_id: int) -> None:
        records = [row.asDict(recursive=True) for row in dataframe.collect()]
        count = len(records)
        logger.info("Batch %d: %d aggregated records", batch_id, count)

        if s3_writer and records:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            try:
                s3_writer.write_curated_records(records, batch_id, date=today)
            except Exception:
                logger.exception("S3 curated write failed for batch %d", batch_id)

        if metrics:
            metrics.emit_batch_metrics(
                batches_processed=1,
                records_processed=count,
                aggregated_records=count,
            )
            metrics.log_event(
                f"Batch {batch_id}: {count} aggregated records written"
            )

    # Invalid events query — append mode
    invalid_query = (
        invalid_events.writeStream
        .outputMode("append")
        .foreachBatch(process_invalid)
        .option("checkpointLocation", f"{args.checkpoint}/invalid")
        .start()
    )

    # Console query — always on so you can see live output
    console_query = (
        aggregates.writeStream
        .outputMode("update")
        .format("console")
        .option("truncate", "false")
        .option("checkpointLocation", f"{args.checkpoint}/console")
        .start()
    )

    # Output query — S3 + CloudWatch
    output_query = (
        aggregates.writeStream
        .outputMode("update")
        .foreachBatch(process_aggregates)
        .option("checkpointLocation", f"{args.checkpoint}/outputs")
        .start()
    )

    logger.info("All streaming queries started. Awaiting termination (Ctrl-C to stop).")

    try:
        console_query.awaitTermination()
    except KeyboardInterrupt:
        logger.info("Interrupted — shutting down streaming queries")
    except Exception:
        logger.exception("Streaming query failed")
        if metrics:
            metrics.emit_batch_metrics(pipeline_errors=1)
            metrics.log_event("Streaming pipeline error — see application logs")
        raise
    finally:
        if metrics:
            metrics.put_application_status(running=False)
            metrics.log_event("BMW streaming pipeline stopped")
        for q in (output_query, invalid_query):
            try:
                q.stop()
            except Exception:
                pass
        logger.info("All streaming queries stopped")


if __name__ == "__main__":
    main()
