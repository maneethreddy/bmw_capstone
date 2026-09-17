import json

from src.kafka.producer import KafkaProducerConfig, TelemetryKafkaProducer


class FakeFuture:
    def __init__(self):
        self.error_callback = None

    def add_errback(self, callback):
        self.error_callback = callback


class FakeProducer:
    def __init__(self):
        self.calls = []

    def send(self, topic, key, value):
        self.calls.append((topic, key, value))
        return FakeFuture()

    def flush(self):
        return None

    def close(self):
        return None


def test_kafka_config_and_serialization():
    fake = FakeProducer()
    producer = TelemetryKafkaProducer(
        KafkaProducerConfig(bootstrap_servers="kafka:9092", topic="telemetry", retries=4),
        producer=fake,
    )
    event = {"vehicle_id": "BMW-1", "speed": 42.0}

    producer.send(event)

    assert fake.calls == [("telemetry", "BMW-1", event)]
    assert json.loads(json.dumps(fake.calls[0][2])) == event
    assert producer.config.retries == 4
