"""Spark session factory for the BMW streaming pipeline.

Provides :class:`SparkSessionConfig` for configuration and
:func:`create_spark_session` for constructing the
:class:`~pyspark.sql.SparkSession` with the Kafka integration JAR
automatically configured.
"""

import os
from typing import Any, Dict, Optional


class SparkSessionConfig:
    """Holds Spark session configuration values.

    Values are resolved from constructor arguments first, then from
    environment variables, and finally from hard-coded defaults.

    Attributes:
        app_name: Spark application name shown in the Spark UI.
        master: Spark master URL (e.g. ``"local[*]"`` or
            ``"spark://host:7077"``).
        java_home: Optional path to the JAVA_HOME directory. When
            ``None`` the JVM is located automatically.
    """

    def __init__(
        self,
        app_name: str = "bmw-capstone-p11",
        master: Optional[str] = None,
        java_home: Optional[str] = None,
    ):
        """Initialise configuration, falling back to environment variables.

        Args:
            app_name: Human-readable Spark application name.
            master: Spark master URL; reads ``SPARK_MASTER`` env var when
                ``None`` (default ``"local[*]"``).
            java_home: Path to JAVA_HOME; reads ``JAVA_HOME`` env var when
                ``None``.
        """
        self.app_name = app_name
        self.master = master or os.getenv("SPARK_MASTER", "local[*]")
        self.java_home = java_home or os.getenv("JAVA_HOME")

    def as_dict(self) -> Dict[str, Any]:
        """Return the config as a plain dictionary.

        Returns:
            A dict with keys ``appName``, ``master``, and ``java_home``.
        """
        return {
            "appName": self.app_name,
            "master": self.master,
            "java_home": self.java_home,
        }


def create_spark_session(config: Optional[SparkSessionConfig] = None) -> Any:
    """Create and return a configured :class:`~pyspark.sql.SparkSession`.

    The Kafka integration JAR is added via ``spark.jars.packages`` so
    Spark downloads it automatically on first run. JVM startup errors
    are intentionally propagated to the caller.

    Args:
        config: Optional :class:`SparkSessionConfig`. When ``None`` a
            default config is constructed from environment variables.

    Returns:
        An active :class:`~pyspark.sql.SparkSession` ready for
        Structured Streaming.

    Raises:
        Exception: Any exception raised by PySpark or the JVM during
            session initialisation.
    """
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
    """Factory shortcut for :class:`SparkSessionConfig`.

    Args:
        **kwargs: Forwarded directly to :class:`SparkSessionConfig`.

    Returns:
        A new :class:`SparkSessionConfig` instance.
    """
    return SparkSessionConfig(**kwargs)
