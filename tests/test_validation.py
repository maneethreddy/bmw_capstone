from src.validation.validators import remove_duplicate_events, validate_event, validate_event_batch


VALID_EVENT = {
    "vehicle_id": "BMW-100",
    "timestamp": "2026-09-17T10:30:00+00:00",
    "speed": 70.5,
    "battery_level": 82.3,
    "temperature": 52.4,
    "fault_code": "NONE",
}


INVALID_EVENT = {
    "vehicle_id": "",
    "timestamp": "not-a-date",
    "speed": -5,
    "battery_level": 120,
    "temperature": 150,
    "fault_code": "",
}


def test_validate_event_accepts_valid_records():
    result = validate_event(VALID_EVENT)

    assert result.valid is True
    assert result.errors == []
    assert result.normalized_event["vehicle_id"] == "BMW-100"


def test_validate_event_rejects_missing_fields():
    incomplete = {"vehicle_id": "BMW-101", "speed": 60}

    result = validate_event(incomplete)

    assert result.valid is False
    assert any("Missing required field" in error for error in result.errors)


def test_validate_event_rejects_invalid_values():
    result = validate_event(INVALID_EVENT)

    assert result.valid is False
    assert len(result.errors) >= 1


def test_validate_event_rejects_invalid_vehicle_and_fault_code():
    invalid = VALID_EVENT | {"vehicle_id": "not-a-bmw-id", "fault_code": "UNKNOWN"}

    result = validate_event(invalid)

    assert result.valid is False
    assert "vehicle_id has an invalid format" in result.errors
    assert "fault_code is invalid" in result.errors


def test_validate_event_batch_separates_valid_and_invalid():
    batch = [VALID_EVENT, INVALID_EVENT]

    result = validate_event_batch(batch)

    assert len(result.valid_events) == 1
    assert len(result.invalid_events) == 1


def test_remove_duplicate_events_removes_duplicates():
    events = [VALID_EVENT, VALID_EVENT.copy(), VALID_EVENT.copy()]

    cleaned = remove_duplicate_events(events)

    assert len(cleaned) == 1
    assert cleaned[0]["vehicle_id"] == "BMW-100"
