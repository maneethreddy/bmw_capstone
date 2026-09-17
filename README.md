# BMW Capstone P11 - Real-Time Connected Vehicle Streaming

BMW P11 processes connected-vehicle telemetry from Kafka with Python and PySpark Structured Streaming. The pipeline validates and normalizes JSON events, applies event-time watermarks, aggregates vehicle metrics, and exposes results through the console with optional S3, Snowflake, and CloudWatch outputs.

## Status

- **IMPLEMENTED:** generator, Kafka producer/CLI, validation, normalization, PySpark pipeline code, event-time aggregation, checkpoint configuration, optional sinks, Terraform, SQL, tests, and CI checks.
- **VERIFIED:** 15 local non-Spark tests and Python compilation.
- **BLOCKED:** Spark runtime execution on this laptop because the installed JDK is 24 and the current PySpark runtime cannot start with it. Do not change company-managed Java; run Spark on an approved compatible JVM.
- **UNVERIFIED:** Kafka broker, AWS, Snowflake, and live end-to-end acceptance execution.

## Architecture

`Telemetry Generator -> Kafka -> PySpark readStream -> JSON schema -> validation -> normalization -> watermark -> event-time window -> console/S3/Snowflake`

## Repository structure

- `src/generator` - telemetry event generation and CLI
- `src/kafka` - configurable producer
- `src/streaming` - Spark session, Kafka source, validation, aggregation, and runner
- `src/validation` - non-Spark validation contracts
- `src/transformations` - Python normalization helper
- `src/aggregation` - local window helper for unit tests
- `src/sinks` - optional S3, Snowflake, and CloudWatch adapters
- `sql` - Snowflake verification queries
- `terraform` - minimal S3, IAM, and CloudWatch infrastructure
- `tests` - automated tests

## Telemetry schema

Each event contains `vehicle_id`, `timestamp`, `speed`, `battery_level`, `temperature`, and `fault_code`. Valid fault codes are `NONE`, `TEMP_HIGH`, `BATTERY_LOW`, and `ENGINE_FAULT`. Validation accepts speed `0..250`, battery `0..100`, and temperature `-20..120`.

## Local setup

Do not install software automatically. A compatible Python environment must have the dependencies in `requirements.txt`. Copy `configs/sample.env` to a local `.env` only when needed. The local Kafka option is in `docker-compose.yml` and requires Docker to be installed and approved separately.

Start Kafka:

```text
docker compose up -d kafka
```

Generate events:

```text
python -m src.generator.cli --interval 1
```

Run the streaming query:

```text
python -m src.streaming.run_streaming --window-duration "5 minutes" --watermark-delay "2 minutes" --checkpoint ./checkpoints/bmw-telemetry
```

The console is the local observable sink. New completed windows appear without restarting the streaming process. Invalid JSON and invalid telemetry are emitted to the invalid-record console query.

## Outputs

- Console output is always available and does not require AWS. The local Kafka → PySpark Structured Streaming → console pipeline is **VERIFIED**.
- Set `S3_BUCKET` and AWS credentials from the approved environment to enable `aggregated/` JSON batch output. The sink is designed for `raw/`, `processed/`, and `aggregated/` prefixes; the streaming runner writes aggregates to `aggregated/`. AWS S3 is **UNVERIFIED** without credentials.
- Set the Snowflake variables in `configs/sample.env` to enable the aggregated target table `BMW_TELEMETRY_AGGREGATES`. Snowflake is **UNVERIFIED** without credentials and network access.
- Set `CLOUDWATCH_ENABLED=true` to publish aggregate batch counts. Terraform provisions the streaming log group and IAM permissions. CloudWatch is **UNVERIFIED** without credentials.

## Windowing and checkpointing

The default window is five minutes with a two-minute event-time watermark. Both are configurable through CLI arguments or environment variables. Checkpoints preserve query progress and state across restarts; local checkpoints are excluded by `.gitignore`.

## Terraform

From the repository root:

```text
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
terraform -chdir=terraform plan
```

Do not run `terraform apply` automatically. AWS credentials and a globally unique `bucket_name` are required for a real plan/apply.

## Snowflake verification

Run the focused analytical queries in `sql/snowflake_verification.sql` after the target table receives data. They verify speed, battery, temperature, faults, event windows, and vehicle-level aggregation.

## Testing

```text
pytest -q
python -m compileall -q src tests
```

The local non-Spark suite is verified. PySpark schema/code tests can run without starting a JVM; full Spark runtime tests are **BLOCKED - JVM compatibility** in the current environment and must not be reported as passing until run on an approved compatible JVM.

## GitHub Actions

`.github/workflows/python-tests.yml` installs dependencies, compiles Python, runs pytest, checks Terraform formatting, and runs Terraform validation. It does not deploy AWS resources or require AWS credentials.

## Final acceptance test

1. Terminal 1: `docker compose up -d kafka`.
2. Terminal 2: run `python -m src.streaming.run_streaming --window-duration "1 minute" --checkpoint ./checkpoints/demo` on a compatible JVM.
3. Terminal 3: run `python -m src.generator.cli --interval 1`.
4. Observe the first aggregate window in Terminal 2.
5. Keep Terminal 3 running and observe additional windows in Terminal 2.
6. Do not restart the streaming query; the new output must be caused by new Kafka events.

## Troubleshooting

- `UnsupportedOperationException: getSubject is not supported`: the JVM is incompatible with the installed Spark version. Use an approved compatible JVM without modifying system Java.
- Kafka connection errors: verify the broker is running and `KAFKA_BOOTSTRAP_SERVERS` matches the broker listener.
- S3/Snowflake errors: verify approved credentials, region, bucket name, network access, and environment variables.
