from datetime import datetime

from src.generator.telemetry_generator import (
    generate_telemetry_batch,
    generate_telemetry_event,
)


def test_generate_telemetry_event_has_required_fields():
    event = generate_telemetry_event(vehicle_id="BMW-101")

    assert set(event.keys()) == {
        "vehicle_id",
        "timestamp",
        "speed",
        "battery_level",
        "temperature",
        "fault_code",
    }
    assert event["vehicle_id"] == "BMW-101"
    assert isinstance(event["timestamp"], str)
    assert isinstance(event["speed"], (int, float))
    assert isinstance(event["battery_level"], (int, float))
    assert isinstance(event["temperature"], (int, float))
    assert isinstance(event["fault_code"], str)


def test_generate_telemetry_event_ranges_are_reasonable():
    event = generate_telemetry_event(vehicle_id=42)

    assert 0 <= event["speed"] <= 250
    assert 0 <= event["battery_level"] <= 100
    assert -20 <= event["temperature"] <= 120
    assert event["fault_code"] in {"NONE", "TEMP_HIGH", "BATTERY_LOW", "ENGINE_FAULT"}


def test_generate_telemetry_batch_returns_expected_count():
    events = generate_telemetry_batch(5, vehicle_ids=["BMW-1", "BMW-2"])

    assert len(events) == 5
    assert all("vehicle_id" in event for event in events)
    assert all("timestamp" in event for event in events)


def test_generate_telemetry_batch_has_valid_timestamps():
    events = generate_telemetry_batch(3)

    for event in events:
        datetime.fromisoformat(event["timestamp"])


def test_generator_supports_custom_vehicle_ids():
    events = generate_telemetry_batch(2, vehicle_ids=["BMW-900", "BMW-901"])

    assert {event["vehicle_id"] for event in events}.issubset({"BMW-900", "BMW-901"})
