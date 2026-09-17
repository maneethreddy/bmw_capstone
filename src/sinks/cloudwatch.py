import os
from typing import Any


class CloudWatchMetrics:
    def __init__(self, namespace: str = "BMW/CapstoneP11", region: str | None = None):
        self.namespace = namespace
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self._client = None

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3

            self._client = boto3.client("cloudwatch", region_name=self.region)
        return self._client

    def put(self, metric_name: str, value: float, unit: str = "Count") -> None:
        self._get_client().put_metric_data(
            Namespace=self.namespace,
            MetricData=[{"MetricName": metric_name, "Value": value, "Unit": unit}],
        )
