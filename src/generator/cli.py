import argparse
import logging
import time

from src.generator.telemetry_generator import generate_telemetry_event
from src.kafka.producer import TelemetryKafkaProducer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate BMW telemetry and publish it to Kafka.")
    parser.add_argument("--count", type=int, default=0, help="Number of events; 0 means run until interrupted.")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between events.")
    parser.add_argument("--vehicle-id", default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    producer = TelemetryKafkaProducer()
    emitted = 0
    try:
        while args.count == 0 or emitted < args.count:
            event = generate_telemetry_event(vehicle_id=args.vehicle_id)
            producer.send(event)
            emitted += 1
            logging.info("Published event %s for %s", emitted, event["vehicle_id"])
            if args.count == 0 or emitted < args.count:
                time.sleep(args.interval)
        producer.flush()
    except KeyboardInterrupt:
        logging.info("Stopping telemetry generator")
    finally:
        producer.close()


if __name__ == "__main__":
    main()
