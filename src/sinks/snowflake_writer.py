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
    def __init__(self, connection_factory: Any = None):
        self.connection_factory = connection_factory

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
