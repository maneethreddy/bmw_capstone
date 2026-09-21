"""Telemetry event normalisation utilities.

Normalises raw telemetry field values so they conform to the canonical
format expected by the validation and aggregation layers:

- ``vehicle_id`` — stripped and upper-cased.
- ``timestamp`` — parsed from ISO-8601 (Z-suffix supported) and
  re-serialised via :meth:`datetime.isoformat`.
- Numeric fields (``speed``, ``battery_level``, ``temperature``) —
  coerced to ``float``.
- ``fault_code`` — mapped to the canonical uppercase representation
  via :data:`FAULT_CODE_MAP`.
"""

from datetime import datetime
from typing import Any, Dict, Iterable, List


FAULT_CODE_MAP = {
    "none": "NONE",
    "temp_high": "TEMP_HIGH",
    "battery_low": "BATTERY_LOW",
    "engine_fault": "ENGINE_FAULT",
    "temphigh": "TEMP_HIGH",
    "batterylow": "BATTERY_LOW",
    "enginefault": "ENGINE_FAULT",
}


def _normalize_timestamp(value: Any) -> str:
    if value is None:
        raise ValueError("timestamp is required")

    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    dt = datetime.fromisoformat(text)
    return dt.isoformat()


def _normalize_fault_code(value: Any) -> str:
    if value is None:
        return "NONE"
    code = str(value).strip().upper().replace("-", "_")
    return FAULT_CODE_MAP.get(code.lower(), code)


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a single raw telemetry event in-place (copy).

    Args:
        event: Raw telemetry event dictionary.  Must contain at minimum
            ``vehicle_id`` and ``timestamp`` keys.

    Returns:
        A new dictionary with all fields normalised.

    Raises:
        ValueError: If ``timestamp`` is ``None`` or cannot be parsed as
            ISO-8601.
    """
    normalized = dict(event)
    normalized["vehicle_id"] = str(normalized.get("vehicle_id", "")).strip().upper()
    normalized["timestamp"] = _normalize_timestamp(normalized.get("timestamp"))
    normalized["speed"] = float(normalized.get("speed", 0))
    normalized["battery_level"] = float(normalized.get("battery_level", 0))
    normalized["temperature"] = float(normalized.get("temperature", 0))
    normalized["fault_code"] = _normalize_fault_code(normalized.get("fault_code"))
    return normalized


def normalize_event_batch(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalise a batch of raw telemetry events.

    Args:
        events: Iterable of raw event dictionaries.

    Returns:
        List of normalised event dictionaries in the same order.
    """
    return [normalize_event(event) for event in events]
