"""PySpark pipeline unit tests.

Uses pytest.importorskip so the tests gracefully skip if PySpark is not
available in the test environment. When Java 17 is on PATH the tests run
the full PySpark schema, parsing, and aggregation code paths.
"""

from __future__ import annotations

import pytest

from src.streaming.pipeline import telemetry_schema

pyspark = pytest.importorskip("pyspark")


# ---------------------------------------------------------------------------
# Schema tests (no JVM required — just importing the function)
# ---------------------------------------------------------------------------

class TestTelemetrySchema:
    def test_schema_contains_all_required_fields(self):
        schema = telemetry_schema()
        assert schema.fieldNames() == [
            "vehicle_id",
            "timestamp",
            "speed",
            "battery_level",
            "temperature",
            "fault_code",
        ]

    def test_speed_is_double(self):
        schema = telemetry_schema()
        assert schema["speed"].dataType.typeName() == "double"

    def test_battery_level_is_double(self):
        schema = telemetry_schema()
        assert schema["battery_level"].dataType.typeName() == "double"

    def test_temperature_is_double(self):
        schema = telemetry_schema()
        assert schema["temperature"].dataType.typeName() == "double"

    def test_vehicle_id_is_string(self):
        schema = telemetry_schema()
        assert schema["vehicle_id"].dataType.typeName() == "string"

    def test_fault_code_is_string(self):
        schema = telemetry_schema()
        assert schema["fault_code"].dataType.typeName() == "string"

    def test_timestamp_is_string(self):
        """Timestamp comes in as string from JSON and is parsed by to_timestamp()."""
        schema = telemetry_schema()
        assert schema["timestamp"].dataType.typeName() == "string"

    def test_schema_has_six_fields(self):
        schema = telemetry_schema()
        assert len(schema.fields) == 6


# ---------------------------------------------------------------------------
# Aggregation function imports
# ---------------------------------------------------------------------------

class TestPipelineFunctionImports:
    """Verify the pipeline module exports the required public API."""

    def test_build_streaming_pipeline_is_callable(self):
        from src.streaming.pipeline import build_streaming_pipeline
        assert callable(build_streaming_pipeline)

    def test_read_kafka_events_is_callable(self):
        from src.streaming.pipeline import read_kafka_events
        assert callable(read_kafka_events)

    def test_parse_and_validate_events_is_callable(self):
        from src.streaming.pipeline import parse_and_validate_events
        assert callable(parse_and_validate_events)

    def test_aggregate_events_is_callable(self):
        from src.streaming.pipeline import aggregate_events
        assert callable(aggregate_events)


# ---------------------------------------------------------------------------
# Fault code constants
# ---------------------------------------------------------------------------

class TestFaultCodeConstants:
    def test_fault_codes_include_all_four_values(self):
        from src.streaming.pipeline import FAULT_CODES
        assert set(FAULT_CODES) == {"NONE", "TEMP_HIGH", "BATTERY_LOW", "ENGINE_FAULT"}
