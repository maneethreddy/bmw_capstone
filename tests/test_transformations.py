from src.transformations.normalizer import normalize_event, normalize_event_batch


def test_normalize_event_standardizes_fields():
    event = {
        "vehicle_id": " bmw-42 ",
        "timestamp": "2026-09-17T10:30:00Z",
        "speed": "70.5",
        "battery_level": "82.3",
        "temperature": "52.4",
        "fault_code": "temp_high",
    }

    normalized = normalize_event(event)

    assert normalized["vehicle_id"] == "BMW-42"
    assert normalized["timestamp"] == "2026-09-17T10:30:00+00:00"
    assert normalized["speed"] == 70.5
    assert normalized["battery_level"] == 82.3
    assert normalized["temperature"] == 52.4
    assert normalized["fault_code"] == "TEMP_HIGH"


def test_normalize_event_batch_returns_cleaned_records():
    events = [
        {
            "vehicle_id": " bmw-90 ",
            "timestamp": "2026-09-17T10:31:00Z",
            "speed": "65",
            "battery_level": "80",
            "temperature": "40",
            "fault_code": "none",
        },
        {
            "vehicle_id": "BMW-91",
            "timestamp": "2026-09-17T10:32:00+00:00",
            "speed": 61,
            "battery_level": 79,
            "temperature": 38,
            "fault_code": "ENGINE_FAULT",
        },
    ]

    normalized = normalize_event_batch(events)

    assert len(normalized) == 2
    assert normalized[0]["fault_code"] == "NONE"
    assert normalized[1]["vehicle_id"] == "BMW-91"
