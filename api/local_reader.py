"""Local PySpark streaming output reader.

Provides fallback telemetry and summary metrics when AWS Athena is unavailable.
Reads the actual aggregated windows produced by the PySpark streaming pipeline
(from local structured output or the streaming log).

Never produces fake or mock data. If no local output exists, returns empty structures.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SPARK_LOG = PROJECT_DIR / ".spark.log"


def read_local_spark_rows(log_path: Path = DEFAULT_SPARK_LOG) -> List[Dict[str, Any]]:
    """Parse aggregated window rows from the PySpark streaming output.

    Maintains latest window state per (vehicle_id, window_start, window_end).
    Returns rows sorted by window_start DESC, vehicle_id.
    """
    if not log_path.exists():
        return []

    windows: Dict[tuple[str, str, str], Dict[str, Any]] = {}

    try:
        content = log_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        logger.warning("Failed to read spark log: %s", exc)
        return []

    current_batch: Optional[int] = None

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("Batch:"):
            try:
                current_batch = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
            continue

        if not line.startswith("|") or not line.endswith("|"):
            continue

        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 8:
            continue

        # Check if line is a data row (vehicle_id matches BMW- pattern)
        vehicle_id = parts[0]
        if not vehicle_id.startswith("BMW-"):
            continue

        try:
            row = {
                "vehicle_id": vehicle_id,
                "window_start": parts[1],
                "window_end": parts[2],
                "average_speed": float(parts[3]),
                "average_battery_level": float(parts[4]),
                "maximum_temperature": float(parts[5]),
                "fault_count": int(parts[6]),
                "event_count": int(parts[7]),
                "batch_id": current_batch,
            }
            key = (vehicle_id, row["window_start"], row["window_end"])
            # In update mode, subsequent batches update earlier window states
            windows[key] = row
        except (ValueError, IndexError):
            continue

    rows = list(windows.values())
    rows.sort(key=lambda r: (r["window_start"], r["vehicle_id"]), reverse=True)
    return rows


def get_local_telemetry(limit: int = 100, log_path: Path = DEFAULT_SPARK_LOG) -> List[Dict[str, Any]]:
    """Return latest N aggregated telemetry windows from local PySpark output."""
    rows = read_local_spark_rows(log_path)
    return rows[:limit]


def get_local_summary(log_path: Path = DEFAULT_SPARK_LOG) -> Dict[str, Any]:
    """Compute fleet-level KPI summary from local PySpark output."""
    rows = read_local_spark_rows(log_path)
    if not rows:
        return {
            "total_vehicles": 0,
            "total_windows": 0,
            "total_events": 0,
            "total_faults": 0,
            "avg_speed": 0.0,
            "avg_battery": 0.0,
            "max_temperature": 0.0,
            "earliest_window": None,
            "latest_window": None,
        }

    total_vehicles = len(set(r["vehicle_id"] for r in rows))
    total_windows = len(rows)
    total_events = sum(r["event_count"] for r in rows)
    total_faults = sum(r["fault_count"] for r in rows)
    avg_speed = round(sum(r["average_speed"] for r in rows) / total_windows, 2)
    avg_battery = round(sum(r["average_battery_level"] for r in rows) / total_windows, 2)
    max_temperature = round(max(r["maximum_temperature"] for r in rows), 2)
    earliest_window = min(r["window_start"] for r in rows)
    latest_window = max(r["window_end"] for r in rows)

    return {
        "total_vehicles": total_vehicles,
        "total_windows": total_windows,
        "total_events": total_events,
        "total_faults": total_faults,
        "avg_speed": avg_speed,
        "avg_battery": avg_battery,
        "max_temperature": max_temperature,
        "earliest_window": earliest_window,
        "latest_window": latest_window,
    }


def get_local_faults(limit: int = 50, log_path: Path = DEFAULT_SPARK_LOG) -> List[Dict[str, Any]]:
    """Return windows where fault_count > 0 from local PySpark output."""
    rows = read_local_spark_rows(log_path)
    fault_rows = [r for r in rows if r.get("fault_count", 0) > 0]
    fault_rows.sort(key=lambda r: (r["window_start"], r["fault_count"]), reverse=True)
    return fault_rows[:limit]
