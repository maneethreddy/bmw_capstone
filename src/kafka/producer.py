"""Kafka producer for BMW telemetry events.

Provides :class:`KafkaProducerConfig` (frozen dataclass) for configuration
and :class:`TelemetryKafkaProducer` for publishing individual events or
batches to the ``bmw-telemetry`` topic.

Example::

    from src.kafka.producer import TelemetryKafkaProducer

    producer = TelemetryKafkaProducer()
    producer.send({"vehicle_id": "BMW-123", "speed": 95.0, ...})
    producer.flush()
    producer.close()
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

try:
    from kafka import KafkaProducer
except ImportError:  # pragma: no cover
    KafkaProducer = None

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KafkaProducerConfig:
    """Immutable configuration for :class:`TelemetryKafkaProducer`.

    Attributes:
        bootstrap_servers: Comma-separated Kafka broker addresses.
        topic: Target Kafka topic name.
        retries: Number of send retries on transient errors.
        request_timeout_ms: Per-request timeout in milliseconds.
        linger_ms: Batching linger time in milliseconds.
    """

    bootstrap_servers: str = "localhost:9092"
    topic: str = "bmw-telemetry"
    retries: int = 3
    request_timeout_ms: int = 10000
    linger_ms: int = 10

    @classmethod
    def from_environment(cls) -> "KafkaProducerConfig":
        """Construct a config from environment variables.

        Reads ``KAFKA_BOOTSTRAP_SERVERS``, ``KAFKA_TOPIC``,
        ``KAFKA_RETRIES``, ``KAFKA_REQUEST_TIMEOUT_MS``, and
        ``KAFKA_LINGER_MS``, falling back to the field defaults.

        Returns:
            A new :class:`KafkaProducerConfig` populated from the
            environment.
        """
        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", cls.bootstrap_servers),
            topic=os.getenv("KAFKA_TOPIC", cls.topic),
            retries=int(os.getenv("KAFKA_RETRIES", cls.retries)),
            request_timeout_ms=int(os.getenv("KAFKA_REQUEST_TIMEOUT_MS", cls.request_timeout_ms)),
            linger_ms=int(os.getenv("KAFKA_LINGER_MS", cls.linger_ms)),
        )


class TelemetryKafkaProducer:
    """High-level Kafka producer for BMW telemetry events.

    Wraps ``kafka-python``'s :class:`~kafka.KafkaProducer` with
    JSON serialisation, vehicle-ID-based keying, and delivery error
    logging. Gracefully handles the case where ``kafka-python`` is not
    installed (raises :exc:`RuntimeError` on :meth:`send`).

    Args:
        config: Producer configuration.  Defaults to
            :meth:`KafkaProducerConfig.from_environment` when ``None``.
        producer: Inject a pre-built producer instance (useful in tests).
    """

    def __init__(self, config: Optional[KafkaProducerConfig] = None, producer: Any = None):
        """Initialise the producer.

        Args:
            config: Optional :class:`KafkaProducerConfig`.
            producer: Optional pre-built producer (test injection).
        """
        self.config = config or KafkaProducerConfig.from_environment()
        self._producer = None

        if producer is not None:
            self._producer = producer
        elif KafkaProducer is not None:
            self._producer = KafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers.split(","),
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                key_serializer=lambda key: str(key).encode("utf-8") if key is not None else None,
                acks="all",
                retries=self.config.retries,
                request_timeout_ms=self.config.request_timeout_ms,
                linger_ms=self.config.linger_ms,
            )

    def send(self, event: Dict[str, Any], key: Optional[str] = None) -> Any:
        """Send a single telemetry event to Kafka.

        Args:
            event: Telemetry event dictionary.  Must contain at least
                ``vehicle_id``.
            key: Optional partition key.  Defaults to
                ``event["vehicle_id"]``.

        Returns:
            A Kafka ``FutureRecordMetadata`` future.

        Raises:
            RuntimeError: If the underlying Kafka producer is unavailable
                (``kafka-python`` not installed or broker not reachable).
        """
        if self._producer is None:
            raise RuntimeError("Kafka producer is unavailable. Install kafka-python or configure a Kafka broker.")
        message_key = key or str(event.get("vehicle_id", "unknown"))
        future = self._producer.send(self.config.topic, key=message_key, value=event)
        if hasattr(future, "add_errback"):
            future.add_errback(self._on_delivery_error)
        return future

    @staticmethod
    def _on_delivery_error(error: BaseException) -> None:
        logger.error("Kafka delivery failed: %s", error)

    def send_batch(self, events: Iterable[Dict[str, Any]]) -> None:
        """Send an iterable of telemetry events.

        Args:
            events: Iterable of event dictionaries, each passed to
                :meth:`send` keyed by ``vehicle_id``.
        """
        for event in events:
            self.send(event, key=str(event.get("vehicle_id", "unknown")))

    def flush(self) -> None:
        """Block until all outstanding messages have been delivered."""
        if self._producer is not None:
            self._producer.flush()

    def close(self) -> None:
        """Close the underlying Kafka producer connection."""
        if self._producer is not None:
            self._producer.close()
