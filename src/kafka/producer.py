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
    bootstrap_servers: str = "localhost:9092"
    topic: str = "bmw-telemetry"
    retries: int = 3
    request_timeout_ms: int = 10000
    linger_ms: int = 10

    @classmethod
    def from_environment(cls) -> "KafkaProducerConfig":
        return cls(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", cls.bootstrap_servers),
            topic=os.getenv("KAFKA_TOPIC", cls.topic),
            retries=int(os.getenv("KAFKA_RETRIES", cls.retries)),
            request_timeout_ms=int(os.getenv("KAFKA_REQUEST_TIMEOUT_MS", cls.request_timeout_ms)),
            linger_ms=int(os.getenv("KAFKA_LINGER_MS", cls.linger_ms)),
        )


class TelemetryKafkaProducer:
    def __init__(self, config: Optional[KafkaProducerConfig] = None, producer: Any = None):
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
        for event in events:
            self.send(event, key=str(event.get("vehicle_id", "unknown")))

    def flush(self) -> None:
        if self._producer is not None:
            self._producer.flush()

    def close(self) -> None:
        if self._producer is not None:
            self._producer.close()
