"""Athena client wrapper for the BMW Capstone P11 API.

Executes SQL queries against the bmw_capstone_p11 Glue/Athena database and
returns results as plain Python dicts.

Credentials are resolved exclusively from the standard AWS credential chain:
  1. Environment variables (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)
  2. ~/.aws/credentials file (configured via `aws configure`)
  3. IAM instance / task role (EC2 / ECS / Lambda)

NEVER hard-code credentials here or in any file committed to Git.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# How long to wait between Athena polling attempts (seconds)
_POLL_INTERVAL = 0.5
# Maximum polling time before raising a timeout error (seconds)
_MAX_WAIT = 120


class AthenaClient:
    """Run SQL queries against AWS Athena and return results as dicts."""

    def __init__(
        self,
        database: Optional[str] = None,
        results_bucket: Optional[str] = None,
        results_prefix: Optional[str] = None,
        region: Optional[str] = None,
        client: Any = None,
    ) -> None:
        self.database = database or os.getenv("ATHENA_DATABASE", "bmw_capstone_p11")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.results_bucket = results_bucket or os.getenv("S3_BUCKET", "m-bmw-capstone-p11-raw")
        self.results_prefix = results_prefix or os.getenv("ATHENA_RESULTS_PREFIX", "athena-results")
        # Allow injecting a mock client for unit tests
        self._client = client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        """Return (and lazily create) the boto3 Athena client."""
        if self._client is None:
            import boto3  # deferred so boto3 is optional at import time

            self._client = boto3.client("athena", region_name=self.region)
        return self._client

    @property
    def _output_location(self) -> str:
        return f"s3://{self.results_bucket}/{self.results_prefix}/"

    def _start_query(self, sql: str) -> str:
        """Submit a query and return the QueryExecutionId."""
        response = self._get_client().start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": self.database},
            ResultConfiguration={"OutputLocation": self._output_location},
        )
        return response["QueryExecutionId"]

    def _wait_for_query(self, query_id: str) -> None:
        """Poll until the query succeeds or raises on failure/timeout."""
        deadline = time.monotonic() + _MAX_WAIT
        client = self._get_client()
        while True:
            resp = client.get_query_execution(QueryExecutionId=query_id)
            state = resp["QueryExecution"]["Status"]["State"]
            if state == "SUCCEEDED":
                return
            if state in ("FAILED", "CANCELLED"):
                reason = resp["QueryExecution"]["Status"].get("StateChangeReason", "unknown")
                raise RuntimeError(f"Athena query {state}: {reason}")
            if time.monotonic() > deadline:
                raise TimeoutError(f"Athena query timed out after {_MAX_WAIT}s")
            time.sleep(_POLL_INTERVAL)

    def _fetch_results(self, query_id: str) -> List[Dict[str, Any]]:
        """Fetch all result pages and return as a list of dicts."""
        client = self._get_client()
        paginator = client.get_paginator("get_query_results")
        pages = paginator.paginate(QueryExecutionId=query_id)

        rows: List[Dict[str, Any]] = []
        headers: List[str] = []

        for page_num, page in enumerate(pages):
            result_set = page["ResultSet"]
            if page_num == 0:
                # First row of first page is always the header
                headers = [c["VarCharValue"] for c in result_set["Rows"][0]["Data"]]
                data_rows = result_set["Rows"][1:]
            else:
                data_rows = result_set["Rows"]

            for row in data_rows:
                values = [cell.get("VarCharValue", None) for cell in row["Data"]]
                rows.append(dict(zip(headers, values)))

        return rows

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute *sql* and return results as a list of dicts.

        All values are returned as strings (Athena's native representation).
        Callers are responsible for type conversion where needed.
        """
        logger.debug("Athena query: %s", sql.strip()[:200])
        query_id = self._start_query(sql)
        self._wait_for_query(query_id)
        results = self._fetch_results(query_id)
        logger.debug("Athena returned %d rows for query %s", len(results), query_id)
        return results
