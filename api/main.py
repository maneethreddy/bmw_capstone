"""BMW Capstone P11 — FastAPI application.

Endpoints:
  GET /api/health     — liveness check
  GET /api/summary    — fleet-level KPI aggregates
  GET /api/telemetry  — latest N aggregated windows
  GET /api/faults     — windows with fault_count > 0

AWS/Athena calls are made server-side only using the standard credential
chain. Credentials are NEVER sent to or stored in the React frontend.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.athena_client import AthenaClient
from api.local_reader import get_local_faults, get_local_summary, get_local_telemetry
from api.pipeline_manager import pipeline_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error classification — safe, no credentials or account IDs exposed
# ---------------------------------------------------------------------------

_ACCESS_DENIED_MARKERS = (
    "AccessDeniedException",
    "AccessDenied",
    "not authorized to perform",
    "explicit deny",
)


def _classify_athena_error(exc: Exception) -> Dict[str, str]:
    """Return a frontend-safe error payload for a failed Athena call.

    Returns one of two error_type values:
      - 'aws_access_denied'   : IAM / permissions restriction
      - 'athena_query_failed' : any other Athena / runtime failure

    The raw exception message is NEVER forwarded to the client to avoid
    leaking account IDs, ARNs, IAM policy names, or credential hints.
    """
    raw = str(exc)
    if any(marker in raw for marker in _ACCESS_DENIED_MARKERS):
        return {
            "error_type": "aws_access_denied",
            "message": "Athena query access denied. Check AWS IAM permissions.",
        }
    return {
        "error_type": "athena_query_failed",
        "message": "Athena query failed.",
    }

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="BMW Capstone P11 — Telemetry API",
    description=(
        "Exposes Athena-backed analytical results for the BMW Connected "
        "Mobility Real-Time Vehicle Streaming capstone project."
    ),
    version="1.0.0",
)

# Allow any localhost/127.0.0.1 port (e.g. 5173, 5174, 3000) and standard HTTP methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Shared Athena client (one per process, lazy-init)
# ---------------------------------------------------------------------------

_athena: Optional[AthenaClient] = None


def get_athena() -> AthenaClient:
    global _athena
    if _athena is None:
        _athena = AthenaClient()
    return _athena


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

ATHENA_TABLE = os.getenv("ATHENA_TABLE", "telemetry_aggregates")
ATHENA_DB = os.getenv("ATHENA_DATABASE", "bmw_capstone_p11")


def _table() -> str:
    return f'"{ATHENA_DB}"."{ATHENA_TABLE}"'


def _safe_float(value: Optional[str], default: float = 0.0) -> float:
    """Convert a string value from Athena to float, with a safe fallback."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value: Optional[str], default: int = 0) -> int:
    """Convert a string value from Athena to int, with a safe fallback."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _coerce_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce Athena string values to the correct Python types."""
    return {
        "vehicle_id": row.get("vehicle_id", ""),
        "window_start": row.get("window_start", ""),
        "window_end": row.get("window_end", ""),
        "average_speed": _safe_float(row.get("average_speed")),
        "average_battery_level": _safe_float(row.get("average_battery_level")),
        "maximum_temperature": _safe_float(row.get("maximum_temperature")),
        "fault_count": _safe_int(row.get("fault_count")),
        "event_count": _safe_int(row.get("event_count")),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> Dict[str, Any]:
    """Liveness check — always returns 200 if the API server is up."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "bmw-capstone-p11-api",
        "version": "1.0.0",
    }


@app.get("/api/telemetry")
def get_telemetry(
    limit: int = Query(default=100, ge=1, le=1000, description="Max rows to return"),
) -> List[Dict[str, Any]]:
    """Return the most recent aggregated windows, newest first.

    Queries Athena in production; falls back to local PySpark output
    when Athena is unavailable.
    """
    sql = f"""
        SELECT
            vehicle_id,
            CAST(window_start AS VARCHAR) AS window_start,
            CAST(window_end   AS VARCHAR) AS window_end,
            average_speed,
            average_battery_level,
            maximum_temperature,
            fault_count,
            event_count
        FROM {_table()}
        ORDER BY window_start DESC, vehicle_id
        LIMIT {limit}
    """
    try:
        rows = get_athena().run_query(sql)
        return [_coerce_row(r) for r in rows]
    except Exception as exc:
        logger.info("Athena telemetry unavailable (%s); checking local PySpark output", exc)
        local_rows = get_local_telemetry(limit=limit)
        if local_rows:
            return local_rows
        raise HTTPException(status_code=503, detail=_classify_athena_error(exc)) from exc


@app.get("/api/summary")
def get_summary() -> Dict[str, Any]:
    """Return fleet-level KPI aggregates for the dashboard summary cards.

    Queries Athena in production; falls back to local PySpark output
    when Athena is unavailable.
    """
    sql = f"""
        SELECT
            COUNT(DISTINCT vehicle_id)                              AS total_vehicles,
            COUNT(*)                                                AS total_windows,
            SUM(event_count)                                        AS total_events,
            SUM(fault_count)                                        AS total_faults,
            ROUND(AVG(average_speed),         2)                   AS avg_speed,
            ROUND(AVG(average_battery_level), 2)                   AS avg_battery,
            ROUND(MAX(maximum_temperature),   2)                   AS max_temperature,
            CAST(MIN(window_start) AS VARCHAR)                      AS earliest_window,
            CAST(MAX(window_end)   AS VARCHAR)                      AS latest_window
        FROM {_table()}
    """
    try:
        rows = get_athena().run_query(sql)
    except Exception as exc:
        logger.info("Athena summary unavailable (%s); checking local PySpark output", exc)
        local_summary = get_local_summary()
        if local_summary["total_windows"] > 0:
            return local_summary
        raise HTTPException(status_code=503, detail=_classify_athena_error(exc)) from exc

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

    r = rows[0]
    return {
        "total_vehicles": _safe_int(r.get("total_vehicles")),
        "total_windows": _safe_int(r.get("total_windows")),
        "total_events": _safe_int(r.get("total_events")),
        "total_faults": _safe_int(r.get("total_faults")),
        "avg_speed": _safe_float(r.get("avg_speed")),
        "avg_battery": _safe_float(r.get("avg_battery")),
        "max_temperature": _safe_float(r.get("max_temperature")),
        "earliest_window": r.get("earliest_window"),
        "latest_window": r.get("latest_window"),
    }


@app.get("/api/faults")
def get_faults(
    limit: int = Query(default=50, ge=1, le=500, description="Max fault rows to return"),
) -> List[Dict[str, Any]]:
    """Return windows where fault_count > 0, most recent first.

    Queries Athena in production; falls back to local PySpark output
    when Athena is unavailable.
    """
    sql = f"""
        SELECT
            vehicle_id,
            CAST(window_start AS VARCHAR) AS window_start,
            CAST(window_end   AS VARCHAR) AS window_end,
            fault_count,
            event_count,
            average_speed,
            average_battery_level,
            maximum_temperature
        FROM {_table()}
        WHERE fault_count > 0
        ORDER BY window_start DESC, fault_count DESC
        LIMIT {limit}
    """
    try:
        rows = get_athena().run_query(sql)
        return [_coerce_row(r) for r in rows]
    except Exception as exc:
        logger.info("Athena faults unavailable (%s); checking local PySpark output", exc)
        local_rows = get_local_faults(limit=limit)
        if local_rows:
            return local_rows
        raise HTTPException(status_code=503, detail=_classify_athena_error(exc)) from exc




# ---------------------------------------------------------------------------
# 3 Terminal-Equivalent Pipeline Control Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/pipeline/start-kafka")
def start_kafka() -> Dict[str, Any]:
    """Execute Terminal 1 command: docker compose up -d kafka."""
    try:
        return pipeline_manager.start_kafka()
    except RuntimeError as exc:
        logger.error("Kafka command failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "command": "docker compose up -d kafka",
                "error": str(exc),
            },
        ) from exc


@app.post("/api/pipeline/start-spark")
def start_spark() -> Dict[str, Any]:
    """Execute Terminal 2 command: python -m src.streaming.run_streaming ..."""
    try:
        return pipeline_manager.start_spark()
    except RuntimeError as exc:
        logger.error("PySpark streaming command failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "command": "python -m src.streaming.run_streaming --window-duration \"1 minute\" --watermark-delay \"30 seconds\" --checkpoint ./checkpoints/demo",
                "error": str(exc),
            },
        ) from exc


@app.post("/api/pipeline/generate-data")
def generate_data() -> Dict[str, Any]:
    """Execute Terminal 3 command: python -m src.generator.cli --count 20 --interval 0.2."""
    try:
        return pipeline_manager.generate_data()
    except RuntimeError as exc:
        logger.error("Telemetry generator command failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "command": "python -m src.generator.cli --count 20 --interval 0.2",
                "error": str(exc),
            },
        ) from exc


