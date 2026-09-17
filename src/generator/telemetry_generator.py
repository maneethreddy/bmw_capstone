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
