import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class S3TelemetryWriter:
    def __init__(self, bucket: str | None = None, region: str | None = None):
        self.bucket = bucket or os.getenv("S3_BUCKET")
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self._client = None

    def _client_or_raise(self) -> Any:
        if not self.bucket:
            raise ValueError("S3_BUCKET must be configured before using the S3 sink")
        if self._client is None:
            import boto3

            self._client = boto3.client("s3", region_name=self.region)
        return self._client

    def write_batch(self, dataframe: Any, batch_id: int, prefix: str = "aggregated") -> None:
        client = self._client_or_raise()
        records = [json.loads(value) for value in dataframe.toJSON().collect()]
        if not records:
            return
        key = f"{prefix}/batch-{batch_id}.json"
        client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=("\n".join(json.dumps(record) for record in records) + "\n").encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Wrote %s records to s3://%s/%s", len(records), self.bucket, key)

    def write_records(self, records: list[dict[str, Any]], batch_id: int, prefix: str) -> None:
        client = self._client_or_raise()
        if not records:
            return
        key = f"{prefix}/batch-{batch_id}.json"
        client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=("\n".join(json.dumps(record) for record in records) + "\n").encode("utf-8"),
            ContentType="application/json",
        )
