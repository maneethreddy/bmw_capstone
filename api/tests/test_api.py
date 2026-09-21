"""Unit tests for the BMW Capstone P11 FastAPI endpoints.

The Athena client is fully mocked so these tests run without any AWS
credentials and without touching real infrastructure.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.pipeline_manager import pipeline_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ROWS = [
    {
        "vehicle_id": "BMW-100",
        "window_start": "2026-09-17 10:00:00.000",
        "window_end": "2026-09-17 10:05:00.000",
        "average_speed": "85.3",
        "average_battery_level": "72.5",
        "maximum_temperature": "45.2",
        "fault_count": "0",
        "event_count": "12",
    },
    {
        "vehicle_id": "BMW-200",
        "window_start": "2026-09-17 10:00:00.000",
        "window_end": "2026-09-17 10:05:00.000",
        "average_speed": "62.1",
        "average_battery_level": "55.0",
        "maximum_temperature": "91.7",
        "fault_count": "3",
        "event_count": "8",
    },
]

SUMMARY_ROW = [
    {
        "total_vehicles": "2",
        "total_windows": "2",
        "total_events": "20",
        "total_faults": "3",
        "avg_speed": "73.7",
        "avg_battery": "63.75",
        "max_temperature": "91.7",
        "earliest_window": "2026-09-17 10:00:00.000",
        "latest_window": "2026-09-17 10:05:00.000",
    }
]

FAULT_ROWS = [SAMPLE_ROWS[1]]  # BMW-200 has fault_count=3


@pytest.fixture()
def mock_athena():
    """Patch AthenaClient.run_query globally for the duration of each test."""
    with patch("api.main.get_athena") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        yield mock_client


@pytest.fixture()
def client(mock_athena):
    """FastAPI test client with mocked Athena."""
    from api.main import app  # imported here so the mock is already in place
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_has_status_ok(self, client):
        data = client.get("/api/health").json()
        assert data["status"] == "ok"

    def test_health_has_timestamp(self, client):
        data = client.get("/api/health").json()
        assert "timestamp" in data
        # Should be parseable as an ISO datetime
        datetime.fromisoformat(data["timestamp"])

    def test_health_has_service_name(self, client):
        data = client.get("/api/health").json()
        assert data["service"] == "bmw-capstone-p11-api"

    def test_health_does_not_contain_aws_credentials(self, client):
        body = client.get("/api/health").text
        for token in ["ACCESS_KEY", "SECRET", "SESSION_TOKEN", "aws_secret"]:
            assert token.lower() not in body.lower(), f"Credential token found: {token}"


# ---------------------------------------------------------------------------
# /api/telemetry
# ---------------------------------------------------------------------------


class TestTelemetry:
    def test_telemetry_returns_200(self, client, mock_athena):
        mock_athena.run_query.return_value = SAMPLE_ROWS
        resp = client.get("/api/telemetry")
        assert resp.status_code == 200

    def test_telemetry_returns_list(self, client, mock_athena):
        mock_athena.run_query.return_value = SAMPLE_ROWS
        data = client.get("/api/telemetry").json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_telemetry_row_has_required_fields(self, client, mock_athena):
        mock_athena.run_query.return_value = SAMPLE_ROWS
        row = client.get("/api/telemetry").json()[0]
        required = [
            "vehicle_id", "window_start", "window_end",
            "average_speed", "average_battery_level",
            "maximum_temperature", "fault_count", "event_count",
        ]
        for field in required:
            assert field in row, f"Missing field: {field}"

    def test_telemetry_numeric_fields_are_correct_types(self, client, mock_athena):
        mock_athena.run_query.return_value = SAMPLE_ROWS
        row = client.get("/api/telemetry").json()[0]
        assert isinstance(row["average_speed"], float)
        assert isinstance(row["average_battery_level"], float)
        assert isinstance(row["maximum_temperature"], float)
        assert isinstance(row["fault_count"], int)
        assert isinstance(row["event_count"], int)

    def test_telemetry_respects_limit_param(self, client, mock_athena):
        mock_athena.run_query.return_value = SAMPLE_ROWS
        resp = client.get("/api/telemetry?limit=10")
        assert resp.status_code == 200
        # Verify the limit was forwarded in the SQL (the mock returns whatever we set)
        call_sql = mock_athena.run_query.call_args[0][0]
        assert "10" in call_sql

    def test_telemetry_limit_out_of_range_returns_422(self, client, mock_athena):
        resp = client.get("/api/telemetry?limit=0")
        assert resp.status_code == 422

    def test_telemetry_athena_error_returns_503(self, client, mock_athena):
        mock_athena.run_query.side_effect = RuntimeError("Athena connection failed")
        with patch("api.main.get_local_telemetry", return_value=[]):
            resp = client.get("/api/telemetry")
            assert resp.status_code == 503

    def test_telemetry_empty_result_returns_empty_list(self, client, mock_athena):
        mock_athena.run_query.return_value = []
        data = client.get("/api/telemetry").json()
        assert data == []

    def test_telemetry_does_not_expose_aws_credentials(self, client, mock_athena):
        mock_athena.run_query.return_value = SAMPLE_ROWS
        body = client.get("/api/telemetry").text
        for token in ["ACCESS_KEY", "SECRET_ACCESS", "SESSION_TOKEN"]:
            assert token.lower() not in body.lower()


# ---------------------------------------------------------------------------
# /api/summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_returns_200(self, client, mock_athena):
        mock_athena.run_query.return_value = SUMMARY_ROW
        resp = client.get("/api/summary")
        assert resp.status_code == 200

    def test_summary_has_all_kpi_fields(self, client, mock_athena):
        mock_athena.run_query.return_value = SUMMARY_ROW
        data = client.get("/api/summary").json()
        for field in [
            "total_vehicles", "total_windows", "total_events", "total_faults",
            "avg_speed", "avg_battery", "max_temperature",
            "earliest_window", "latest_window",
        ]:
            assert field in data, f"Missing KPI: {field}"

    def test_summary_vehicle_count(self, client, mock_athena):
        mock_athena.run_query.return_value = SUMMARY_ROW
        data = client.get("/api/summary").json()
        assert data["total_vehicles"] == 2

    def test_summary_total_faults(self, client, mock_athena):
        mock_athena.run_query.return_value = SUMMARY_ROW
        data = client.get("/api/summary").json()
        assert data["total_faults"] == 3

    def test_summary_empty_athena_returns_zeroes(self, client, mock_athena):
        mock_athena.run_query.return_value = []
        data = client.get("/api/summary").json()
        assert data["total_vehicles"] == 0
        assert data["total_faults"] == 0

    def test_summary_athena_error_returns_503(self, client, mock_athena):
        mock_athena.run_query.side_effect = RuntimeError("timeout")
        with patch("api.main.get_local_summary", return_value={"total_windows": 0}):
            resp = client.get("/api/summary")
            assert resp.status_code == 503


# ---------------------------------------------------------------------------
# /api/faults
# ---------------------------------------------------------------------------


class TestFaults:
    def test_faults_returns_200(self, client, mock_athena):
        mock_athena.run_query.return_value = FAULT_ROWS
        resp = client.get("/api/faults")
        assert resp.status_code == 200

    def test_faults_returns_only_fault_rows(self, client, mock_athena):
        mock_athena.run_query.return_value = FAULT_ROWS
        data = client.get("/api/faults").json()
        assert all(row["fault_count"] > 0 for row in data)

    def test_faults_row_has_vehicle_id(self, client, mock_athena):
        mock_athena.run_query.return_value = FAULT_ROWS
        data = client.get("/api/faults").json()
        assert data[0]["vehicle_id"] == "BMW-200"

    def test_faults_fault_count_is_int(self, client, mock_athena):
        mock_athena.run_query.return_value = FAULT_ROWS
        data = client.get("/api/faults").json()
        assert isinstance(data[0]["fault_count"], int)

    def test_faults_empty_when_no_faults(self, client, mock_athena):
        mock_athena.run_query.return_value = []
        data = client.get("/api/faults").json()
        assert data == []

    def test_faults_athena_error_returns_503(self, client, mock_athena):
        mock_athena.run_query.side_effect = TimeoutError("query timed out")
        with patch("api.main.get_local_faults", return_value=[]):
            resp = client.get("/api/faults")
            assert resp.status_code == 503

    def test_faults_sql_filters_by_fault_count(self, client, mock_athena):
        mock_athena.run_query.return_value = FAULT_ROWS
        client.get("/api/faults")
        call_sql = mock_athena.run_query.call_args[0][0]
        assert "fault_count > 0" in call_sql


# ---------------------------------------------------------------------------
# Security: no credentials in any response
# ---------------------------------------------------------------------------


class TestNoCredentialsExposed:
    CREDENTIAL_TOKENS = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "aws_secret",
        "AKIA",  # Access key prefix
        "aws_access",
    ]

    @pytest.mark.parametrize("endpoint", ["/api/health", "/api/telemetry", "/api/summary", "/api/faults"])
    def test_endpoint_does_not_expose_credentials(self, client, mock_athena, endpoint):
        mock_athena.run_query.return_value = SAMPLE_ROWS if endpoint != "/api/summary" else SUMMARY_ROW
        body = client.get(endpoint).text.lower()
        for token in self.CREDENTIAL_TOKENS:
            assert token.lower() not in body, f"Credential token '{token}' found in {endpoint} response"


# ---------------------------------------------------------------------------
# Error classification: structured 503 detail
# ---------------------------------------------------------------------------


class TestErrorClassification:
    """503 responses must use the structured {error_type, message} payload.

    These tests verify that:
      1. AccessDeniedException-style errors produce error_type='aws_access_denied'
      2. Other failures produce error_type='athena_query_failed'
      3. The raw AWS exception string is NEVER forwarded to the client.
      4. Sensitive tokens (account IDs, ARNs, policy names) are not present.
    """

    @pytest.fixture(autouse=True)
    def _no_local_data(self):
        with patch("api.main.get_local_telemetry", return_value=[]), \
             patch("api.main.get_local_summary", return_value={"total_windows": 0}), \
             patch("api.main.get_local_faults", return_value=[]):
            yield

    # Strings that look like real AWS AccessDeniedException messages
    ACCESS_DENIED_EXCEPTIONS = [
        RuntimeError("An error occurred (AccessDeniedException) when calling the "
                     "StartQueryExecution operation: User: arn:aws:iam::123456789012:user/test "
                     "is not authorized to perform: athena:StartQueryExecution with an "
                     "explicit deny in an identity-based policy: arn:aws:iam::123456789012:policy/CohortWindowDeny"),
        RuntimeError("AccessDenied: you are not authorized"),
        RuntimeError("not authorized to perform: athena:StartQueryExecution"),
        RuntimeError("explicit deny in an identity-based policy"),
    ]

    OTHER_EXCEPTIONS = [
        RuntimeError("Athena connection failed"),
        TimeoutError("query timed out after 120s"),
        RuntimeError("Internal Server Error"),
    ]

    @pytest.mark.parametrize("exc", ACCESS_DENIED_EXCEPTIONS)
    def test_access_denied_produces_aws_access_denied_type(self, client, mock_athena, exc):
        mock_athena.run_query.side_effect = exc
        resp = client.get("/api/summary")
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["error_type"] == "aws_access_denied"

    @pytest.mark.parametrize("exc", OTHER_EXCEPTIONS)
    def test_other_exceptions_produce_athena_query_failed_type(self, client, mock_athena, exc):
        mock_athena.run_query.side_effect = exc
        resp = client.get("/api/summary")
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert detail["error_type"] == "athena_query_failed"

    def test_503_detail_has_message_field(self, client, mock_athena):
        mock_athena.run_query.side_effect = RuntimeError("timeout")
        resp = client.get("/api/summary")
        assert "message" in resp.json()["detail"]

    def test_aws_access_denied_message_is_safe(self, client, mock_athena):
        mock_athena.run_query.side_effect = RuntimeError(
            "AccessDeniedException: arn:aws:iam::532404260630:policy/CohortWindowDeny"
        )
        body = client.get("/api/summary").text
        # Raw ARN / account ID / policy name must NOT appear in the response
        assert "532404260630" not in body
        assert "CohortWindowDeny" not in body
        assert "arn:aws" not in body

    @pytest.mark.parametrize("endpoint", ["/api/telemetry", "/api/summary", "/api/faults"])
    def test_all_endpoints_use_structured_503(self, client, mock_athena, endpoint):
        mock_athena.run_query.side_effect = RuntimeError("AccessDeniedException: denied")
        resp = client.get(endpoint)
        assert resp.status_code == 503
        detail = resp.json()["detail"]
        assert isinstance(detail, dict), "503 detail must be a dict, not a plain string"
        assert "error_type" in detail
        assert "message" in detail

    def test_no_raw_exception_string_in_aws_access_denied_response(self, client, mock_athena):
        raw_msg = "An error occurred (AccessDeniedException) when calling StartQueryExecution"
        mock_athena.run_query.side_effect = RuntimeError(raw_msg)
        body = client.get("/api/telemetry").text
        assert "AccessDeniedException" not in body
        assert "StartQueryExecution" not in body

    def test_no_raw_exception_string_in_athena_failed_response(self, client, mock_athena):
        raw_msg = "Internal boto3 error with secret details: abc123"
        mock_athena.run_query.side_effect = RuntimeError(raw_msg)
        body = client.get("/api/telemetry").text
        assert "abc123" not in body
        assert "boto3" not in body


# ---------------------------------------------------------------------------
# 3 Terminal-Equivalent Pipeline Control Tests
# ---------------------------------------------------------------------------

class TestStartKafka:
    def test_start_kafka_success(self, client):
        with patch.object(
            pipeline_manager,
            "start_kafka",
            return_value={
                "status": "success",
                "command": "docker compose up -d kafka",
                "output": "Container kafka Started",
            },
        ):
            resp = client.post("/api/pipeline/start-kafka")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["command"] == "docker compose up -d kafka"
            assert "Started" in data["output"]

    def test_start_kafka_failure_shows_actual_error(self, client):
        err_msg = "Cannot connect to the Docker daemon at unix:///var/run/docker.sock"
        with patch.object(pipeline_manager, "start_kafka", side_effect=RuntimeError(err_msg)):
            resp = client.post("/api/pipeline/start-kafka")
            assert resp.status_code == 500
            detail = resp.json()["detail"]
            assert detail["status"] == "failed"
            assert detail["command"] == "docker compose up -d kafka"
            assert err_msg in detail["error"]


class TestStartSpark:
    def test_start_spark_success(self, client):
        with patch.object(
            pipeline_manager,
            "start_spark",
            return_value={
                "status": "success",
                "command": "python -m src.streaming.run_streaming ...",
                "output": "PySpark streaming started.",
            },
        ):
            resp = client.post("/api/pipeline/start-spark")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert "started" in data["output"]

    def test_start_spark_failure_shows_actual_error(self, client):
        err_msg = "PySpark streaming exited immediately (code 1): Java not found"
        with patch.object(pipeline_manager, "start_spark", side_effect=RuntimeError(err_msg)):
            resp = client.post("/api/pipeline/start-spark")
            assert resp.status_code == 500
            detail = resp.json()["detail"]
            assert detail["status"] == "failed"
            assert err_msg in detail["error"]


class TestGenerateData:
    def test_generate_data_success(self, client):
        with patch.object(
            pipeline_manager,
            "generate_data",
            return_value={
                "status": "success",
                "command": "python -m src.generator.cli --count 20 --interval 0.2",
                "output": "Generated 20 events.",
            },
        ):
            resp = client.post("/api/pipeline/generate-data")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["command"] == "python -m src.generator.cli --count 20 --interval 0.2"
            assert "20 events" in data["output"]

    def test_generate_data_failure_shows_actual_error(self, client):
        err_msg = "KafkaTimeoutError: Failed to update metadata after 30.0 secs."
        with patch.object(pipeline_manager, "generate_data", side_effect=RuntimeError(err_msg)):
            resp = client.post("/api/pipeline/generate-data")
            assert resp.status_code == 500
            detail = resp.json()["detail"]
            assert detail["status"] == "failed"
            assert err_msg in detail["error"]


# ---------------------------------------------------------------------------
# Local PySpark Fallback Tests (Cases A, B, C, D)
# ---------------------------------------------------------------------------

LOCAL_SPARK_SAMPLE = [
    {
        "vehicle_id": "BMW-684",
        "window_start": "2026-09-20 23:35:00",
        "window_end": "2026-09-20 23:36:00",
        "average_speed": 190.43,
        "average_battery_level": 82.99,
        "maximum_temperature": 62.15,
        "fault_count": 0,
        "event_count": 1,
    },
    {
        "vehicle_id": "BMW-927",
        "window_start": "2026-09-20 23:35:00",
        "window_end": "2026-09-20 23:36:00",
        "average_speed": 13.7,
        "average_battery_level": 36.56,
        "maximum_temperature": 5.42,
        "fault_count": 1,
        "event_count": 1,
    },
]

LOCAL_SPARK_SUMMARY = {
    "total_vehicles": 2,
    "total_windows": 2,
    "total_events": 2,
    "total_faults": 1,
    "avg_speed": 102.07,
    "avg_battery": 59.78,
    "max_temperature": 62.15,
    "earliest_window": "2026-09-20 23:35:00",
    "latest_window": "2026-09-20 23:36:00",
}


class TestLocalFallbackCases:
    """Tests specifically verifying:
    A) Athena available -> Athena data is returned.
    B) Athena unavailable -> local PySpark aggregated data is returned.
    C) No local data -> return an appropriate empty response, not fake values.
    D) Existing frontend response format remains unchanged.
    """

    def test_case_a_athena_available_returns_athena_data(self, client, mock_athena):
        """Case A: When Athena succeeds, Athena data is returned."""
        mock_athena.run_query.return_value = SAMPLE_ROWS
        resp = client.get("/api/telemetry")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["vehicle_id"] == "BMW-100"

    def test_case_b_athena_unavailable_returns_local_spark_telemetry(self, client, mock_athena):
        """Case B: When Athena fails, returns local PySpark data."""
        mock_athena.run_query.side_effect = RuntimeError("AccessDeniedException: denied")
        with patch("api.main.get_local_telemetry", return_value=LOCAL_SPARK_SAMPLE):
            resp = client.get("/api/telemetry")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["vehicle_id"] == "BMW-684"
            assert data[0]["average_speed"] == 190.43

    def test_case_b_athena_unavailable_returns_local_spark_summary(self, client, mock_athena):
        """Case B: When Athena fails, returns local PySpark summary."""
        mock_athena.run_query.side_effect = RuntimeError("AccessDeniedException: denied")
        with patch("api.main.get_local_summary", return_value=LOCAL_SPARK_SUMMARY):
            resp = client.get("/api/summary")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_vehicles"] == 2
            assert data["total_faults"] == 1
            assert data["avg_speed"] == 102.07

    def test_case_b_athena_unavailable_returns_local_spark_faults(self, client, mock_athena):
        """Case B: When Athena fails, returns local PySpark faults."""
        mock_athena.run_query.side_effect = RuntimeError("AccessDeniedException: denied")
        faults_only = [LOCAL_SPARK_SAMPLE[1]]  # BMW-927 has fault_count=1
        with patch("api.main.get_local_faults", return_value=faults_only):
            resp = client.get("/api/faults")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["vehicle_id"] == "BMW-927"
            assert data[0]["fault_count"] == 1

    def test_case_c_no_local_data_returns_empty_or_zeroes(self, tmp_path):
        """Case C: When no local data exists, reader returns empty structures, never fake data."""
        from api.local_reader import get_local_faults, get_local_summary, get_local_telemetry

        empty_log = tmp_path / "empty_spark.log"
        empty_log.write_text("")

        # Telemetry should be empty list
        assert get_local_telemetry(log_path=empty_log) == []

        # Faults should be empty list
        assert get_local_faults(log_path=empty_log) == []

        # Summary should be zeroes, never fake values
        summary = get_local_summary(log_path=empty_log)
        assert summary["total_vehicles"] == 0
        assert summary["total_windows"] == 0
        assert summary["total_events"] == 0
        assert summary["total_faults"] == 0
        assert summary["avg_speed"] == 0.0
        assert summary["avg_battery"] == 0.0
        assert summary["max_temperature"] == 0.0
        assert summary["earliest_window"] is None
        assert summary["latest_window"] is None

    def test_case_d_response_schema_matches_frontend(self, client, mock_athena):
        """Case D: The response schema matches the exact keys expected by the frontend."""
        mock_athena.run_query.side_effect = RuntimeError("AccessDenied")
        with patch("api.main.get_local_telemetry", return_value=LOCAL_SPARK_SAMPLE), \
             patch("api.main.get_local_summary", return_value=LOCAL_SPARK_SUMMARY), \
             patch("api.main.get_local_faults", return_value=[LOCAL_SPARK_SAMPLE[1]]):

            # Check /api/telemetry
            tel_row = client.get("/api/telemetry").json()[0]
            required_tel = [
                "vehicle_id", "window_start", "window_end",
                "average_speed", "average_battery_level",
                "maximum_temperature", "fault_count", "event_count",
            ]
            for k in required_tel:
                assert k in tel_row

            # Check /api/summary
            sum_data = client.get("/api/summary").json()
            required_sum = [
                "total_vehicles", "total_windows", "total_events", "total_faults",
                "avg_speed", "avg_battery", "max_temperature",
                "earliest_window", "latest_window",
            ]
            for k in required_sum:
                assert k in sum_data

            # Check /api/faults
            fault_row = client.get("/api/faults").json()[0]
            assert "vehicle_id" in fault_row
            assert fault_row["fault_count"] > 0




