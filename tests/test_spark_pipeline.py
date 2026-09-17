import pytest

from src.streaming.pipeline import telemetry_schema


pyspark = pytest.importorskip("pyspark")


def test_telemetry_schema_contains_required_fields():
    schema = telemetry_schema()

    assert schema.fieldNames() == [
        "vehicle_id",
        "timestamp",
        "speed",
        "battery_level",
        "temperature",
        "fault_code",
    ]
    assert schema["speed"].dataType.typeName() == "double"
