"""Unit tests for S3TelemetryWriter and CloudWatchMetrics.

Both sinks use injectable clients so no real AWS calls are made.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, call

import pytest

from src.sinks.s3_writer import S3TelemetryWriter
from src.sinks.cloudwatch import CloudWatchMetrics


# =============================================================================
# S3TelemetryWriter
# =============================================================================

SAMPLE_RECORDS = [
    {
        "vehicle_id": "BMW-101",
        "window_start": "2026-09-17T10:00:00+00:00",
        "window_end": "2026-09-17T10:05:00+00:00",
        "average_speed": 95.5,
        "average_battery_level": 78.2,
        "maximum_temperature": 42.0,
        "fault_count": 1,
        "event_count": 5,
    },
    {
        "vehicle_id": "BMW-202",
        "window_start": "2026-09-17T10:00:00+00:00",
        "window_end": "2026-09-17T10:05:00+00:00",
        "average_speed": 110.0,
        "average_battery_level": 65.0,
        "maximum_temperature": 55.0,
        "fault_count": 0,
        "event_count": 3,
    },
]


def _make_s3_writer() -> tuple[S3TelemetryWriter, MagicMock]:
    mock_client = MagicMock()
    writer = S3TelemetryWriter(bucket="test-bucket", region="us-east-1", client=mock_client)
    return writer, mock_client


class TestS3WriterRaw:
    def test_write_raw_calls_put_object(self):
        writer, client = _make_s3_writer()
        writer.write_raw_records(SAMPLE_RECORDS, batch_id=7, date="2026-09-17")
        client.put_object.assert_called_once()
        kwargs = client.put_object.call_args.kwargs
        assert kwargs["Bucket"] == "test-bucket"
        assert "raw/telemetry/date=2026-09-17/batch-7.json" == kwargs["Key"]
        assert kwargs["ContentType"] == "application/json"

    def test_write_raw_body_is_newline_delimited_json(self):
        writer, client = _make_s3_writer()
        writer.write_raw_records(SAMPLE_RECORDS, batch_id=1, date="2026-09-17")
        body_bytes = client.put_object.call_args.kwargs["Body"]
        lines = body_bytes.decode("utf-8").strip().split("\n")
        assert len(lines) == 2
        first = json.loads(lines[0])
        assert first["vehicle_id"] == "BMW-101"

    def test_write_raw_empty_records_skips_put(self):
        writer, client = _make_s3_writer()
        writer.write_raw_records([], batch_id=1)
        client.put_object.assert_not_called()

    def test_write_raw_raises_on_missing_bucket(self):
        writer = S3TelemetryWriter(bucket=None, client=MagicMock())
        writer.bucket = None  # force None
        with pytest.raises(ValueError, match="S3_BUCKET"):
            writer.write_raw_records(SAMPLE_RECORDS, batch_id=1)

    def test_write_raw_propagates_s3_errors(self):
        writer, client = _make_s3_writer()
        client.put_object.side_effect = RuntimeError("network error")
        with pytest.raises(RuntimeError, match="network error"):
            writer.write_raw_records(SAMPLE_RECORDS, batch_id=1, date="2026-09-17")

    def test_write_raw_date_partition_key(self):
        writer, client = _make_s3_writer()
        writer.write_raw_records(SAMPLE_RECORDS, batch_id=3, date="2026-01-15")
        key = client.put_object.call_args.kwargs["Key"]
        assert "date=2026-01-15" in key

    def test_write_raw_batch_id_in_key(self):
        writer, client = _make_s3_writer()
        writer.write_raw_records(SAMPLE_RECORDS, batch_id=42, date="2026-09-17")
        key = client.put_object.call_args.kwargs["Key"]
        assert "batch-42" in key


class TestS3WriterCurated:
    def test_write_curated_calls_put_object(self):
        writer, client = _make_s3_writer()
        writer.write_curated_records(SAMPLE_RECORDS, batch_id=5, date="2026-09-17")
        client.put_object.assert_called_once()
        kwargs = client.put_object.call_args.kwargs
        assert kwargs["Bucket"] == "test-bucket"
        assert "curated/telemetry/date=2026-09-17" in kwargs["Key"]

    def test_write_curated_empty_records_skips_put(self):
        writer, client = _make_s3_writer()
        writer.write_curated_records([], batch_id=1)
        client.put_object.assert_not_called()

    def test_write_curated_key_contains_batch_id(self):
        writer, client = _make_s3_writer()
        writer.write_curated_records(SAMPLE_RECORDS, batch_id=99, date="2026-09-17")
        key = client.put_object.call_args.kwargs["Key"]
        assert "batch-99" in key

    def test_write_curated_propagates_s3_errors(self):
        writer, client = _make_s3_writer()
        client.put_object.side_effect = Exception("s3 error")
        with pytest.raises(Exception, match="s3 error"):
            writer.write_curated_records(SAMPLE_RECORDS, batch_id=1, date="2026-09-17")

    def test_write_records_legacy_compat(self):
        """Backward-compat write_records() method works with arbitrary prefix."""
        writer, client = _make_s3_writer()
        writer.write_records(SAMPLE_RECORDS, batch_id=2, prefix="aggregated")
        key = client.put_object.call_args.kwargs["Key"]
        assert key == "aggregated/batch-2.json"


# =============================================================================
# CloudWatchMetrics
# =============================================================================


def _make_cw() -> tuple[CloudWatchMetrics, MagicMock]:
    mock_client = MagicMock()
    cw = CloudWatchMetrics(namespace="BMW/Test", region="us-east-1", client=mock_client)
    return cw, mock_client


class TestCloudWatchMetrics:
    def test_put_calls_put_metric_data(self):
        cw, client = _make_cw()
        cw.put("TestMetric", 42.0)
        client.put_metric_data.assert_called_once()
        args = client.put_metric_data.call_args.kwargs
        assert args["Namespace"] == "BMW/Test"
        assert args["MetricData"][0]["MetricName"] == "TestMetric"
        assert args["MetricData"][0]["Value"] == 42.0

    def test_put_does_not_raise_on_client_error(self):
        cw, client = _make_cw()
        client.put_metric_data.side_effect = Exception("no credentials")
        # Must not raise — pipeline continues without CloudWatch
        cw.put("TestMetric", 1.0)

    def test_put_application_status_running(self):
        cw, client = _make_cw()
        cw.put_application_status(running=True)
        data = client.put_metric_data.call_args.kwargs["MetricData"]
        metric = next(m for m in data if m["MetricName"] == "ApplicationStatus")
        assert metric["Value"] == 1.0

    def test_put_application_status_stopped(self):
        cw, client = _make_cw()
        cw.put_application_status(running=False)
        data = client.put_metric_data.call_args.kwargs["MetricData"]
        metric = next(m for m in data if m["MetricName"] == "ApplicationStatus")
        assert metric["Value"] == 0.0

    def test_emit_batch_metrics_sends_five_metrics(self):
        cw, client = _make_cw()
        cw.emit_batch_metrics(
            batches_processed=1,
            records_processed=20,
            aggregated_records=5,
            invalid_records=2,
            pipeline_errors=0,
        )
        client.put_metric_data.assert_called_once()
        data = client.put_metric_data.call_args.kwargs["MetricData"]
        assert len(data) == 5
        names = {m["MetricName"] for m in data}
        assert "BatchesProcessed" in names
        assert "RecordsProcessed" in names
        assert "AggregatedRecords" in names
        assert "InvalidRecords" in names
        assert "PipelineErrors" in names

    def test_emit_batch_metrics_correct_values(self):
        cw, client = _make_cw()
        cw.emit_batch_metrics(records_processed=30, aggregated_records=10, invalid_records=3)
        data = client.put_metric_data.call_args.kwargs["MetricData"]
        by_name = {m["MetricName"]: m["Value"] for m in data}
        assert by_name["RecordsProcessed"] == 30
        assert by_name["AggregatedRecords"] == 10
        assert by_name["InvalidRecords"] == 3

    def test_emit_batch_metrics_does_not_raise_on_error(self):
        cw, client = _make_cw()
        client.put_metric_data.side_effect = Exception("cw down")
        # Must not raise
        cw.emit_batch_metrics(records_processed=5)

    def test_namespace_is_configurable(self):
        mock_client = MagicMock()
        cw = CloudWatchMetrics(namespace="Custom/NS", client=mock_client)
        cw.put("X", 1.0)
        args = mock_client.put_metric_data.call_args.kwargs
        assert args["Namespace"] == "Custom/NS"
