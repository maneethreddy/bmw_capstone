"""Pure-Python tumbling-window aggregation for BMW telemetry events.

This module provides an in-process alternative to the PySpark window
aggregation in :mod:`src.streaming.pipeline`.  It is primarily used in
unit tests and local (non-Spark) execution paths.

Example::

    from src.aggregation.window_aggregator import aggregate_events_by_window

    summaries = aggregate_events_by_window(events, window_seconds=300)
"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List


def _parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def aggregate_events_by_window(events: Iterable[Dict[str, Any]], window_seconds: int = 300) -> List[Dict[str, Any]]:
    """Aggregate telemetry events into fixed-duration tumbling windows.

    Events are grouped by ``vehicle_id`` and the floor of their UTC
    timestamp to the nearest ``window_seconds`` boundary.

    Args:
        events: Iterable of telemetry event dictionaries.  Each event
            must have the keys ``vehicle_id``, ``timestamp``,
            ``speed``, ``battery_level``, ``temperature``, and
            ``fault_code``.
        window_seconds: Window duration in seconds.  Must be positive.
            Defaults to ``300`` (5 minutes).

    Returns:
        List of window summary dictionaries sorted by
        ``(vehicle_id, window_start)``, each with keys:

        - ``vehicle_id``
        - ``window_start`` (ISO-8601 string of window start boundary)
        - ``window_seconds``
        - ``avg_speed``
        - ``avg_battery_level``
        - ``max_temperature``
        - ``fault_count``
        - ``event_count``

    Raises:
        ValueError: If ``window_seconds <= 0``.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")

    grouped: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)

    for event in events:
        ts = _parse_ts(str(event["timestamp"]))
        epoch_seconds = int(ts.timestamp())
        bucket_epoch = epoch_seconds - (epoch_seconds % window_seconds)
        bucket = datetime.fromtimestamp(bucket_epoch, tz=ts.tzinfo)
        grouped[(event["vehicle_id"], bucket.isoformat())].append(event)

    summaries: List[Dict[str, Any]] = []
    for (vehicle_id, window_start_str), window_events in grouped.items():
        speeds = [float(item["speed"]) for item in window_events]
        battery_levels = [float(item["battery_level"]) for item in window_events]
        temperatures = [float(item["temperature"]) for item in window_events]
        fault_count = sum(1 for item in window_events if str(item.get("fault_code", "NONE")).upper() != "NONE")

        summaries.append(
            {
                "vehicle_id": vehicle_id,
                "window_start": window_start_str,
                "window_seconds": window_seconds,
                "avg_speed": round(sum(speeds) / len(speeds), 2) if speeds else 0.0,
                "avg_battery_level": round(sum(battery_levels) / len(battery_levels), 2) if battery_levels else 0.0,
                "max_temperature": max(temperatures) if temperatures else 0.0,
                "fault_count": fault_count,
                "event_count": len(window_events),
            }
        )

    return sorted(summaries, key=lambda item: (item["vehicle_id"], item["window_start"]))
