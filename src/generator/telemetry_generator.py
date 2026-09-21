"""Synthetic BMW vehicle telemetry event generator.

Generates randomised telemetry events that conform to the BMW connected
vehicle data model (vehicle ID, speed, battery level, temperature, fault
code). Events are either generated one at a time via
:func:`generate_telemetry_event` or in bulk via
:func:`generate_telemetry_batch`.

Example::

    from src.generator.telemetry_generator import generate_telemetry_batch

    events = generate_telemetry_batch(count=50)
    # [{'vehicle_id': 'BMW-1', 'speed': 87.42, ...}, ...]
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


FAULT_CODES = ["NONE", "TEMP_HIGH", "BATTERY_LOW", "ENGINE_FAULT"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def generate_telemetry_event(
    vehicle_id: Any = None,
    timestamp: Optional[str] = None,
    speed: Optional[float] = None,
    battery_level: Optional[float] = None,
    temperature: Optional[float] = None,
    fault_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a single synthetic BMW telemetry event.

    All parameters are optional; omitted values are filled in with
    random data within the valid operating ranges.

    Args:
        vehicle_id: Vehicle identifier.  If ``None`` a random
            ``BMW-NNN`` string is generated.
        timestamp: ISO-8601 timestamp string.  Defaults to the current
            UTC time with millisecond precision.
        speed: Speed in km/h ``[0, 220]``.  Generated randomly if
            ``None``.
        battery_level: State-of-charge in % ``[10, 100]``.  Generated
            randomly if ``None``.
        temperature: Temperature in \u00b0C ``[-5, 105]``.  Generated
            randomly if ``None``.
        fault_code: One of ``NONE``, ``TEMP_HIGH``, ``BATTERY_LOW``,
            ``ENGINE_FAULT``.  Chosen randomly if ``None``.

    Returns:
        A dictionary with keys ``vehicle_id``, ``timestamp``,
        ``speed``, ``battery_level``, ``temperature``, and
        ``fault_code``.
    """
    if vehicle_id is None:
        vehicle_id = f"BMW-{random.randint(100, 999)}"

    event = {
        "vehicle_id": str(vehicle_id),
        "timestamp": timestamp or _utc_now_iso(),
        "speed": speed if speed is not None else round(random.uniform(0, 220), 2),
        "battery_level": battery_level if battery_level is not None else round(random.uniform(10, 100), 2),
        "temperature": temperature if temperature is not None else round(random.uniform(-5, 105), 2),
        "fault_code": fault_code or random.choice(FAULT_CODES),
    }

    return event


def generate_telemetry_batch(
    count: int,
    vehicle_ids: Optional[List[Any]] = None,
    start_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Generate a batch of synthetic telemetry events.

    Events are distributed round-robin across the provided vehicle IDs,
    each with a timestamp one second after the previous event.

    Args:
        count: Number of events to generate.  Must be ``>= 0``.
        vehicle_ids: List of vehicle identifiers.  Defaults to
            ``["BMW-1", ..., "BMW-10"]`` when ``None``.
        start_time: UTC datetime for the first event.  Defaults to the
            current UTC time when ``None``.

    Returns:
        Ordered list of event dictionaries (see
        :func:`generate_telemetry_event`).

    Raises:
        ValueError: If ``count < 0`` or ``vehicle_ids`` is an empty list.
    """
    if count < 0:
        raise ValueError("count must be non-negative")

    ids = [str(v) for v in (vehicle_ids or [f"BMW-{i}" for i in range(1, 11)])]
    if not ids:
        raise ValueError("vehicle_ids cannot be empty")

    base_time = start_time or datetime.now(timezone.utc)
    batch: List[Dict[str, Any]] = []

    for i in range(count):
        event_time = base_time + timedelta(seconds=i)
        vehicle_id = ids[i % len(ids)]
        batch.append(
            generate_telemetry_event(
                vehicle_id=vehicle_id,
                timestamp=event_time.isoformat(timespec="milliseconds"),
                speed=round(random.uniform(20, 220), 2),
                battery_level=round(random.uniform(15, 100), 2),
                temperature=round(random.uniform(0, 95), 2),
                fault_code=random.choice(FAULT_CODES),
            )
        )

    return batch
