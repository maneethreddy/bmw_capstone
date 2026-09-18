"""CloudWatch metrics and logging sink.

Emits custom metrics to Amazon CloudWatch under the ``BMW/CapstoneP11``
namespace and optionally sends log events to a CloudWatch Logs log group.

Credentials are resolved from the standard AWS credential chain.
Never hard-code credentials in source code.

If CloudWatch is unavailable (no credentials, wrong region, etc.) the
``emit_*`` methods log a warning and return without raising so the
streaming pipeline continues uninterrupted.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

LOG_GROUP = "/bmw-capstone-p11/streaming"


class CloudWatchMetrics:
    """Publish custom metrics and log events to Amazon CloudWatch."""

    def __init__(
        self,
        namespace: str = "BMW/CapstoneP11",
        region: Optional[str] = None,
        client: Any = None,
        logs_client: Any = None,
    ) -> None:
        self.namespace = namespace
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        # Allow injecting mock clients for unit tests
        self._client = client
        self._logs_client = logs_client
        self._log_stream_created = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3  # deferred import

            self._client = boto3.client("cloudwatch", region_name=self.region)
        return self._client

    def _get_logs_client(self) -> Any:
        if self._logs_client is None:
            import boto3

            self._logs_client = boto3.client("logs", region_name=self.region)
        return self._logs_client

    # ------------------------------------------------------------------
    # Single metric
    # ------------------------------------------------------------------

    def put(self, metric_name: str, value: float, unit: str = "Count") -> None:
        """Emit a single metric data point."""
        try:
            self._get_client().put_metric_data(
                Namespace=self.namespace,
                MetricData=[{"MetricName": metric_name, "Value": value, "Unit": unit}],
            )
        except Exception as exc:
            logger.warning("CloudWatch put metric '%s' failed: %s", metric_name, exc)

    # ------------------------------------------------------------------
    # Structured batch metrics (called once per micro-batch)
    # ------------------------------------------------------------------

    def emit_batch_metrics(
        self,
        *,
        batches_processed: int = 1,
        records_processed: int = 0,
        aggregated_records: int = 0,
        invalid_records: int = 0,
        pipeline_errors: int = 0,
    ) -> None:
        """Emit all per-batch operational metrics in a single API call."""
        metric_data: List[Any] = [
            {"MetricName": "BatchesProcessed", "Value": batches_processed, "Unit": "Count"},
            {"MetricName": "RecordsProcessed", "Value": records_processed, "Unit": "Count"},
            {"MetricName": "AggregatedRecords", "Value": aggregated_records, "Unit": "Count"},
            {"MetricName": "InvalidRecords", "Value": invalid_records, "Unit": "Count"},
            {"MetricName": "PipelineErrors", "Value": pipeline_errors, "Unit": "Count"},
        ]
        try:
            self._get_client().put_metric_data(
                Namespace=self.namespace,
                MetricData=metric_data,
            )
            logger.debug(
                "CloudWatch batch metrics emitted: batches=%d records=%d aggregated=%d invalid=%d errors=%d",
                batches_processed,
                records_processed,
                aggregated_records,
                invalid_records,
                pipeline_errors,
            )
        except Exception as exc:
            logger.warning("CloudWatch emit_batch_metrics failed: %s", exc)

    def put_application_status(self, running: bool) -> None:
        """Emit ApplicationStatus (1=running, 0=stopped)."""
        self.put("ApplicationStatus", 1.0 if running else 0.0)

    # ------------------------------------------------------------------
    # CloudWatch Logs
    # ------------------------------------------------------------------

    def _ensure_log_stream(self, log_stream_name: str) -> None:
        """Create the log group and stream if they do not already exist."""
        if self._log_stream_created:
            return
        client = self._get_logs_client()
        try:
            client.create_log_group(logGroupName=LOG_GROUP)
        except client.exceptions.ResourceAlreadyExistsException:
            pass
        except Exception as exc:
            logger.warning("Could not create CloudWatch log group: %s", exc)
            return
        try:
            client.create_log_stream(
                logGroupName=LOG_GROUP,
                logStreamName=log_stream_name,
            )
        except client.exceptions.ResourceAlreadyExistsException:
            pass
        except Exception as exc:
            logger.warning("Could not create CloudWatch log stream: %s", exc)
            return
        self._log_stream_created = True

    def log_event(self, message: str, log_stream_name: str = "streaming-pipeline") -> None:
        """Put a log event to CloudWatch Logs."""
        self._ensure_log_stream(log_stream_name)
        try:
            self._get_logs_client().put_log_events(
                logGroupName=LOG_GROUP,
                logStreamName=log_stream_name,
                logEvents=[
                    {
                        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                        "message": message,
                    }
                ],
            )
        except Exception as exc:
            logger.warning("CloudWatch log_event failed: %s", exc)
