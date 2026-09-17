import os
from typing import Any, Dict, Optional


class SparkSessionConfig:
    def __init__(
        self,
        app_name: str = "bmw-capstone-p11",
        master: Optional[str] = None,
        java_home: Optional[str] = None,
    ):
        self.app_name = app_name
        self.master = master or os.getenv("SPARK_MASTER", "local[*]")
        self.java_home = java_home or os.getenv("JAVA_HOME")

    def as_dict(self) -> Dict[str, Any]:
        return {
            "appName": self.app_name,
            "master": self.master,
            "java_home": self.java_home,
        }


def create_spark_session(config: Optional[SparkSessionConfig] = None) -> Any:
    """Create the Spark session; JVM startup errors are intentionally propagated."""
    from pyspark.sql import SparkSession

    active_config = config or SparkSessionConfig()
    kafka_package = os.getenv(
        "SPARK_KAFKA_PACKAGE",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3",
    )
    builder = (
        SparkSession.builder.appName(active_config.app_name)
        .master(active_config.master)
        .config("spark.jars.packages", kafka_package)
    )
    return builder.getOrCreate()


def create_spark_session_config(**kwargs: Any) -> SparkSessionConfig:
    return SparkSessionConfig(**kwargs)
