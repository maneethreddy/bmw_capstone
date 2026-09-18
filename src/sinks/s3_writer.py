"""S3 telemetry sink.

Writes raw JSON events and curated Parquet aggregates to S3 using date-based
partitioning so Athena can discover and query the data efficiently.

Layout::

    s3://<bucket>/
        raw/telemetry/date=YYYY-MM-DD/batch-<id>.json
        curated/telemetry/date=YYYY-MM-DD/batch-<id>.parquet

Credentials are resolved from the standard AWS credential chain
(environment variables, ~/.aws/credentials, IAM role, etc.).
Never hard-code credentials in source code.
"""

from __future__ import annotations

import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class S3TelemetryWriter:
    """Write telemetry batches to S3 in raw (JSON) and curated (Parquet) formats."""

    def __init__(
        self,
        bucket: Optional[str] = None,
        region: Optional[str] = None,
        client: Any = None,
    ) -> None:
        self.bucket = bucket or os.getenv("S3_BUCKET")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        # Allow injecting a mock client for unit tests
        self._client = client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Return (and lazily create) the boto3 S3 client."""
        if self._client is None:
            import boto3  # deferred import so boto3 is optional at import time

            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def _require_bucket(self) -> str:
        if not self.bucket:
            raise ValueError(
                "S3_BUCKET environment variable must be set before using the S3 sink"
            )
        return self.bucket

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_raw_records(
        self,
        records: List[Dict[str, Any]],
        batch_id: int,
        date: Optional[str] = None,
    ) -> None:
        """Write raw telemetry events as JSON (newline-delimited) to the raw prefix."""
        if not records:
            return
        bucket = self._require_bucket()
        partition = date or self._today()
        key = f"raw/telemetry/date={partition}/batch-{batch_id}.json"
        body = ("\n".join(json.dumps(r) for r in records) + "\n").encode("utf-8")
        try:
            self._get_client().put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
            )
            logger.info(
                "S3 raw write complete: s3://%s/%s (%d records)", bucket, key, len(records)
            )
        except Exception as exc:
            logger.error("S3 raw write failed for key %s: %s", key, exc)
            raise

    def write_curated_records(
        self,
        records: List[Dict[str, Any]],
        batch_id: int,
        date: Optional[str] = None,
    ) -> None:
        """Write curated aggregate records as Parquet to the curated prefix.

        Falls back to JSON if the ``pyarrow`` package is not installed, so
        the application can still run without the optional dependency.
        """
        if not records:
            return
        bucket = self._require_bucket()
        partition = date or self._today()

        try:
            import pyarrow as pa  # type: ignore
            import pyarrow.parquet as pq  # type: ignore

            table = pa.Table.from_pylist(records)
            buf = io.BytesIO()
            pq.write_table(table, buf)
            buf.seek(0)
            key = f"curated/telemetry/date={partition}/batch-{batch_id}.parquet"
            self._get_client().put_object(
                Bucket=bucket,
                Key=key,
                Body=buf.read(),
                ContentType="application/octet-stream",
            )
            logger.info(
                "S3 curated Parquet write complete: s3://%s/%s (%d records)",
                bucket,
                key,
                len(records),
            )
        except ImportError:
            logger.warning("pyarrow not installed — falling back to JSON for curated write")
            key = f"curated/telemetry/date={partition}/batch-{batch_id}.json"
            body = ("\n".join(json.dumps(r) for r in records) + "\n").encode("utf-8")
            try:
                self._get_client().put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=body,
                    ContentType="application/json",
                )
                logger.info(
                    "S3 curated JSON fallback write complete: s3://%s/%s (%d records)",
                    bucket,
                    key,
                    len(records),
                )
            except Exception as exc:
                logger.error("S3 curated JSON write failed for key %s: %s", key, exc)
                raise
        except Exception as exc:
            logger.error("S3 curated write failed for key %s: %s", key, exc)
            raise

    # ------------------------------------------------------------------
    # Legacy compatibility (used by older run_streaming path)
    # ------------------------------------------------------------------

    def write_batch(
        self,
        dataframe: Any,
        batch_id: int,
        prefix: str = "aggregated",
    ) -> None:
        """Write a PySpark DataFrame batch as JSON to a legacy prefix.

        Retained for backward compatibility. Prefer ``write_curated_records``.
        """
        records = [json.loads(v) for v in dataframe.toJSON().collect()]
        if not records:
            return
        bucket = self._require_bucket()
        key = f"{prefix}/batch-{batch_id}.json"
        body = ("\n".join(json.dumps(r) for r in records) + "\n").encode("utf-8")
        try:
            self._get_client().put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
            )
            logger.info(
                "S3 legacy write complete: s3://%s/%s (%d records)", bucket, key, len(records)
            )
        except Exception as exc:
            logger.error("S3 legacy write failed for key %s: %s", key, exc)
            raise

    def write_records(
        self,
        records: List[Dict[str, Any]],
        batch_id: int,
        prefix: str,
    ) -> None:
        """Write records JSON to an arbitrary prefix (backward compat)."""
        if not records:
            return
        bucket = self._require_bucket()
        key = f"{prefix}/batch-{batch_id}.json"
        body = ("\n".join(json.dumps(r) for r in records) + "\n").encode("utf-8")
        try:
            self._get_client().put_object(
                Bucket=bucket,
                Key=key,
                Body=body,
                ContentType="application/json",
            )
        except Exception as exc:
            logger.error("S3 write failed for key %s: %s", key, exc)
            raise
