"""Telemetry event validation functions.

Validates individual events and batches against the BMW connected vehicle
data model rules:

- ``vehicle_id`` must match ``BMW-[A-Za-z0-9-]+``.
- ``timestamp`` must be a timezone-aware ISO-8601 datetime.
- ``speed`` must be in ``[0, 250]`` km/h.
- ``battery_level`` must be in ``[0, 100]`` %.
- ``temperature`` must be in ``[-20, 120]`` \u00b0C.
- ``fault_code`` must be one of :data:`VALID_FAULT_CODES`.

Example::

    from src.validation.validators import validate_event

    result = validate_event({"vehicle_id": "BMW-123", ...})
    if result.valid:
        process(result.normalized_event)
    else:
        log_errors(result.errors)
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple

from src.validation.schemas import REQUIRED_FIELDS, BatchValidationResult, ValidationResult

logger = logging.getLogger(__name__)
VALID_FAULT_CODES = {"NONE", "TEMP_HIGH", "BATTERY_LOW", "ENGINE_FAULT"}


def _normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(event)
    normalized["vehicle_id"] = str(normalized.get("vehicle_id", "")).strip()
    if isinstance(normalized.get("fault_code"), str):
        normalized["fault_code"] = normalized["fault_code"].strip()
    return normalized


def validate_event(event: Dict[str, Any]) -> ValidationResult:
    """Validate a single telemetry event against all field-level rules.

    The event is first normalised (whitespace stripped, types coerced)
    before validation rules are applied.

    Args:
        event: Raw telemetry event dictionary.

    Returns:
        A :class:`~src.validation.schemas.ValidationResult`.  When
        ``valid`` is ``False`` the ``errors`` list explains all failures.
    """
    errors: List[str] = []
    normalized = _normalize_event(event)

    missing = [field for field in REQUIRED_FIELDS if field not in normalized]
    if missing:
        errors.extend(f"Missing required field: {field}" for field in missing)
        return ValidationResult(valid=False, errors=errors, normalized_event={})

    if not normalized.get("vehicle_id"):
        errors.append("vehicle_id is null or empty")
    elif not re.fullmatch(r"BMW-[A-Za-z0-9-]+", normalized["vehicle_id"]):
        errors.append("vehicle_id has an invalid format")

    try:
        dt = datetime.fromisoformat(str(normalized["timestamp"]).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            errors.append("timestamp must include timezone information")
    except ValueError:
        errors.append("timestamp is not a valid ISO-8601 datetime")

    for field_name in ["speed", "battery_level", "temperature"]:
        value = normalized.get(field_name)
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            errors.append(f"{field_name} is not numeric")
            continue

        if field_name == "speed" and not (0 <= numeric_value <= 250):
            errors.append("speed is out of expected range 0..250")
        if field_name == "battery_level" and not (0 <= numeric_value <= 100):
            errors.append("battery_level is out of expected range 0..100")
        if field_name == "temperature" and not (-20 <= numeric_value <= 120):
            errors.append("temperature is out of expected range -20..120")

    fault_code = normalized.get("fault_code")
    if not isinstance(fault_code, str) or fault_code.strip().upper() not in VALID_FAULT_CODES:
        errors.append("fault_code is invalid")

    if errors:
        logger.warning("Invalid telemetry event: %s", errors)
        return ValidationResult(valid=False, errors=errors, normalized_event={})

    return ValidationResult(valid=True, errors=[], normalized_event=normalized)


def validate_event_batch(events: Iterable[Dict[str, Any]]) -> BatchValidationResult:
    """Validate an iterable of telemetry events.

    Args:
        events: Iterable of raw telemetry event dictionaries.

    Returns:
        A :class:`~src.validation.schemas.BatchValidationResult` with
        separate lists for valid and invalid events plus all error
        messages.
    """
    valid_events: List[Dict[str, Any]] = []
    invalid_events: List[Dict[str, Any]] = []
    invalid_reasons: List[str] = []

    for event in events:
        result = validate_event(event)
        if result.valid:
            valid_events.append(result.normalized_event)
        else:
            invalid_events.append(event)
            invalid_reasons.extend(result.errors)

    return BatchValidationResult(
        valid_events=valid_events,
        invalid_events=invalid_events,
        invalid_reasons=invalid_reasons,
    )


def remove_duplicate_events(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate events from an iterable, preserving order.

    Two events are considered duplicates when all their key-value pairs
    are identical.  Only the first occurrence is kept; subsequent
    duplicates are logged at WARNING level and discarded.

    Args:
        events: Iterable of telemetry event dictionaries.

    Returns:
        De-duplicated list of events in original order.
    """
    seen = set()
    unique_events: List[Dict[str, Any]] = []

    for event in events:
        signature = tuple(sorted((key, str(value)) for key, value in event.items()))
        if signature in seen:
            logger.warning("Duplicate event found: %s", event)
            continue
        seen.add(signature)
        unique_events.append(event)

    return unique_events
