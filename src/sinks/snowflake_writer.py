"""Legacy Snowflake telemetry sink (not used in production).

This module is retained for reference only.  In the production
architecture Athena queries the curated S3 Parquet data directly;
Snowflake is intentionally not used.

.. note::
   Requires the ``snowflake-connector-python`` package which is **not**
   listed as a project dependency.  Install it manually if you need this
   writer.
"""

import logging
import os
from typing import Any, Iterable, Mapping

logger = logging.getLogger(__name__)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS BMW_TELEMETRY_AGGREGATES (
    VEHICLE_ID VARCHAR NOT NULL,
    WINDOW_START TIMESTAMP_TZ NOT NULL,
    WINDOW_END TIMESTAMP_TZ NOT NULL,
    AVERAGE_SPEED FLOAT,
    AVERAGE_BATTERY_LEVEL FLOAT,
    MAXIMUM_TEMPERATURE FLOAT,
    FAULT_COUNT INTEGER,
    EVENT_COUNT INTEGER
)
"""


class SnowflakeTelemetryWriter:
    """Write telemetry aggregate records to a Snowflake table.

    Creates the target table automatically if it does not exist.

    Args:
        connection_factory: Optional callable that returns a Snowflake
            connection.  When ``None`` a real connection is created from
            environment variables (``SNOWFLAKE_ACCOUNT``,
            ``SNOWFLAKE_USER``, ``SNOWFLAKE_PASSWORD``,
            ``SNOWFLAKE_DATABASE``, ``SNOWFLAKE_SCHEMA``,
            optionally ``SNOWFLAKE_WAREHOUSE``).
    """

    def _connect(self) -> Any:
        if self.connection_factory:
            return self.connection_factory()
        import snowflake.connector

        required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"]
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise ValueError(f"Missing Snowflake configuration: {', '.join(missing)}")
        return snowflake.connector.connect(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            password=os.environ["SNOWFLAKE_PASSWORD"],
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.environ["SNOWFLAKE_DATABASE"],
            schema=os.environ["SNOWFLAKE_SCHEMA"],
        )

    def write_records(self, records: Iterable[Mapping[str, Any]]) -> None:
        """Write an iterable of aggregate records to Snowflake.

        Creates the ``BMW_TELEMETRY_AGGREGATES`` table if needed, then
        bulk-inserts all records in a single ``executemany`` call.

        Args:
            records: Iterable of aggregate record mappings with keys:
                ``vehicle_id``, ``window_start``, ``window_end``,
                ``average_speed``, ``average_battery_level``,
                ``maximum_temperature``, ``fault_count``,
                ``event_count``.

        Raises:
            ValueError: If required Snowflake environment variables are
                not set and no ``connection_factory`` was provided.
        """
        rows = [
            (
                item["vehicle_id"], item["window_start"], item["window_end"], item.get("average_speed"),
                item.get("average_battery_level"), item.get("maximum_temperature"), item.get("fault_count"),
                item.get("event_count"),
            )
            for item in records
        ]
        if not rows:
            return
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.execute(CREATE_TABLE_SQL)
            cursor.executemany(
                "INSERT INTO BMW_TELEMETRY_AGGREGATES VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", rows
            )
            connection.commit()
        finally:
            connection.close()
