# BMW Capstone P11 — Real-Time Connected Vehicle Streaming

**Participant 11 · BMW TechWorks 5-Day Capstone**

---

## Business Problem

Modern BMW vehicles generate continuous telemetry data — speed, battery level, engine temperature, and fault codes — at high frequency from thousands of connected vehicles simultaneously. BMW's Connected Mobility division needs to:

1. **Ingest** this telemetry in real-time without losing events.
2. **Detect** vehicle faults and abnormal conditions as they happen.
3. **Aggregate** per-vehicle metrics over configurable time windows.
4. **Store** both raw and curated data durably for auditing and analysis.
5. **Query** aggregated results for operational reporting.
6. **Monitor** pipeline health and data throughput continuously.

This project implements a production-style streaming pipeline that addresses all five needs.

---

## Architecture

```
Telemetry Generator
       │  (simulates BMW vehicle sensors)
       ▼
     Kafka
       │  (durable event transport, decouples producer from consumer)
       ▼
PySpark Structured Streaming
       │  readStream from Kafka → JSON parse → schema enforcement
       │  → validation → normalization → watermark → event-time window
       ▼
   ┌───────────────────────┐
   │  Window Aggregation   │
   │  (1-min tumbling)     │
   │  · avg_speed          │
   │  · avg_battery_level  │
   │  · max_temperature    │
   │  · fault_count        │
   └───────────────────────┘
       │
       ├──▶ Console (always on — local verification)
       │
       ├──▶ S3 curated/ (Parquet, date-partitioned)
       │         s3://<bucket>/curated/telemetry/date=YYYY-MM-DD/
       │
       └──▶ CloudWatch Metrics & Logs
                 Namespace: BMW/CapstoneP11
                 Log group: /bmw-capstone-p11/streaming

                         ▼
                      Athena
          (queries curated Parquet via Glue Data Catalog)

Supporting Infrastructure:
  Terraform  → provisions S3, IAM, CloudWatch, Glue, Athena resources
  GitHub Actions → CI/CD (Python tests, Terraform fmt/validate)
```

---

## Why Each Component Exists

| Component | Role |
|---|---|
| **Telemetry Generator** | Simulates BMW vehicle sensors. Generates realistic JSON events with all required fields and publishes them to Kafka at a configurable rate. |
| **Kafka** | Durable, fault-tolerant message bus. Decouples the producer (vehicle/generator) from the consumer (PySpark). Events survive PySpark restarts. |
| **PySpark Structured Streaming** | The core engine. Reads Kafka continuously, enforces schema, validates data quality, normalises fields, and computes event-time window aggregations at scale. |
| **Validation** | Rejects malformed events (wrong vehicle ID format, out-of-range numeric values, invalid timestamps) before they corrupt aggregates. |
| **Transformation/Normalisation** | Standardises vehicle IDs (uppercase), fault codes, and timestamp formats so aggregations are consistent regardless of source formatting. |
| **Window Aggregation** | Groups events by vehicle and configurable time window; computes the four required business metrics (Avg Speed, Avg Battery, Max Temp, Fault Count). |
| **S3** | Durable object storage for both raw JSON telemetry and curated Parquet aggregates. Parquet enables efficient columnar querying by Athena. |
| **Athena** | Serverless SQL query engine that reads Parquet data directly from S3. No separate database server needed. The Glue Data Catalog holds table metadata. |
| **CloudWatch** | Monitors pipeline health: records processed per batch, invalid event rate, aggregated records, pipeline errors, and application up/down status. |
| **Terraform** | Infrastructure as code for S3 bucket (versioned, encrypted, private), IAM roles, CloudWatch log group, and Glue/Athena catalog resources. |
| **GitHub Actions** | CI/CD: runs pytest, compileall, Terraform fmt, and Terraform validate on every push/PR. Java 17 is configured so PySpark tests run in CI. |

---

## Telemetry Schema

Each event published to Kafka is a JSON object:

```json
{
  "vehicle_id":    "BMW-101",
  "timestamp":     "2026-09-18T10:00:00.000+00:00",
  "speed":         92.4,
  "battery_level": 78.3,
  "temperature":   42.1,
  "fault_code":    "NONE"
}
```

| Field | Type | Valid Range | Valid Values |
|---|---|---|---|
| `vehicle_id` | string | — | Pattern: `BMW-[A-Z0-9-]+` |
| `timestamp` | ISO-8601 string | — | Must include timezone (`Z` or `±HH:MM`) |
| `speed` | double | 0 – 250 km/h | — |
| `battery_level` | double | 0 – 100 % | — |
| `temperature` | double | -20 – 120 °C | — |
| `fault_code` | string | — | `NONE`, `TEMP_HIGH`, `BATTERY_LOW`, `ENGINE_FAULT` |

---

## Local Setup

### Prerequisites

- Python 3.10+ with virtual environment
- Docker Desktop (for Kafka)
- Java 17 (required by PySpark 3.5.x)
  - Mac: `brew install openjdk@17`
  - Set `JAVA_HOME` before running PySpark:
    ```bash
    export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
    ```
- AWS CLI configured (for S3/CloudWatch/Athena sinks — optional for local run)

### Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Configuration

```bash
cp configs/sample.env .env
# Edit .env with your values — it is excluded from Git
```

---

## Running Locally (3-Terminal Demo)

### Terminal 1 — Start Kafka

```bash
docker compose up -d kafka
docker compose ps   # verify kafka is "Up"
```

### Terminal 2 — Start PySpark Streaming

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
source .venv/bin/activate

python -m src.streaming.run_streaming \
  --window-duration "1 minute" \
  --watermark-delay "30 seconds" \
  --checkpoint ./checkpoints/demo
```

The console will print aggregated windows as events arrive.
**Leave this running** — do not restart it.

### Terminal 3 — Generate Telemetry

```bash
source .venv/bin/activate

# First burst
python -m src.generator.cli --count 20 --interval 0.2

# Wait ~90 seconds for the window to close, then send a second burst:
python -m src.generator.cli --count 20 --interval 0.2
```

### Primary Acceptance Criterion ✅

> **"New events appear in analytical output without restarting the pipeline."**

Proven by:
1. PySpark running in Terminal 2 (never restarted).
2. First batch of events → first micro-batch output in Terminal 2.
3. Second batch of events → second micro-batch output in Terminal 2 (same process).

---

## Verification Status

| Component | Implemented | Locally Tested | AWS Live-Verified |
|---|---|---|---|
| Telemetry Generator | ✅ | ✅ | N/A |
| Kafka Producer | ✅ | ✅ | N/A |
| PySpark Structured Streaming | ✅ | ✅ **VERIFIED** | N/A |
| Validation | ✅ | ✅ | N/A |
| Transformation | ✅ | ✅ | N/A |
| Window Aggregation (PySpark) | ✅ | ✅ **VERIFIED** | N/A |
| Console Sink | ✅ | ✅ **VERIFIED** | N/A |
| S3 Curated Parquet Sink | ✅ | ✅ (mocked) | Pending credentials |
| S3 Raw JSON Sink | ✅ | ✅ (mocked) | Pending credentials |
| CloudWatch Metrics | ✅ | ✅ (mocked) | Pending credentials |
| CloudWatch Logs | ✅ | ✅ (mocked) | Pending credentials |
| Athena SQL Queries | ✅ | N/A (SQL only) | Pending credentials |
| Glue Data Catalog | ✅ (Terraform) | N/A | Pending Terraform apply |
| Terraform fmt | ✅ | ✅ **PASSED** | N/A |
| Terraform validate | ✅ | ✅ **PASSED** | N/A |
| GitHub Actions CI | ✅ | Triggers on push | N/A |
| pytest (67 tests) | ✅ | ✅ **67/67 PASSED** | N/A |

---

## Running Tests

```bash
source .venv/bin/activate
pytest -v
python -m compileall -q src tests
```

**Expected: 67 passed, 0 failed.**

Test coverage:
- `test_telemetry_generator.py` — event generation, field presence, ranges
- `test_validation.py` — valid/invalid events, missing fields, out-of-range values
- `test_transformations.py` — vehicle ID normalisation, fault code mapping, timestamps
- `test_aggregation.py` — avg speed (80.0), avg battery (60.0), max temp (50.0), fault count (2), windows
- `test_kafka.py` — producer config, serialisation, mock delivery
- `test_sinks.py` — S3 bucket, partition keys, Parquet writes, CloudWatch metrics, error handling
- `test_spark_pipeline.py` — PySpark schema field types, public API, FAULT_CODES constants

---

## Terraform (Infrastructure as Code)

### Resources Provisioned

| Resource | Purpose |
|---|---|
| `aws_s3_bucket` | Telemetry storage (versioned, AES-256 encrypted, private) |
| `aws_cloudwatch_log_group` | Application logs (`/bmw-capstone-p11/streaming`) |
| `aws_iam_role` + `aws_iam_role_policy` | Least-privilege: S3 write, CloudWatch logs/metrics, Glue read, Athena query |
| `aws_glue_catalog_database` | Metadata database for Athena |
| `aws_glue_catalog_table` | External Parquet table pointing at `s3://<bucket>/curated/telemetry/` |

### Commands

```bash
# Format check (run before commit)
terraform -chdir=terraform fmt -check -recursive

# Validate without AWS credentials
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate

# Plan (requires AWS credentials)
terraform -chdir=terraform plan

# Apply (requires AWS credentials — review plan first)
terraform -chdir=terraform apply
```

> ⚠️ **Do not run `terraform apply` without reviewing the plan first.**

---

## Athena Queries

After the streaming pipeline writes curated Parquet data to S3:

1. Run the table setup (or let Terraform provision it):
   ```sql
   -- See sql/athena_setup.sql
   MSCK REPAIR TABLE bmw_capstone_p11.telemetry_aggregates;
   ```

2. Run analytical queries — see `sql/athena_queries.sql`:

```sql
-- Q1: All windows — four required metrics
SELECT vehicle_id, window_start, window_end,
       ROUND(average_speed, 2)         AS avg_speed_kmh,
       ROUND(average_battery_level, 2) AS avg_battery_pct,
       ROUND(maximum_temperature, 2)   AS max_temp_celsius,
       fault_count, event_count
FROM bmw_capstone_p11.telemetry_aggregates
ORDER BY window_start DESC LIMIT 50;

-- Q6: Latest window per vehicle (proves new events arrive without restart)
SELECT vehicle_id, MAX(window_end) AS latest_window
FROM bmw_capstone_p11.telemetry_aggregates
GROUP BY vehicle_id ORDER BY latest_window DESC;
```

---

## Modifying a Business Rule (Day-5 Demo)

The business rules are in [`src/streaming/pipeline.py`](src/streaming/pipeline.py).

**Example: Change the window from 5 minutes to 2 minutes**

```python
# Before (line ~93):
def aggregate_events(valid_events: DataFrame, window_duration: str = "5 minutes") -> DataFrame:

# After:
def aggregate_events(valid_events: DataFrame, window_duration: str = "2 minutes") -> DataFrame:
```

Or pass it at runtime without changing code:
```bash
python -m src.streaming.run_streaming --window-duration "2 minutes"
```

**Effect on output:** Smaller windows produce more frequent results with fewer events each. The console will print windows at 2-minute intervals instead of 5-minute intervals.

**Example: Lower the fault threshold to flag TEMP_HIGH only**

Change in `pipeline.py` line ~100:
```python
# Before — count any non-NONE fault:
spark_sum(when(col("fault_code") != "NONE", 1).otherwise(0)).alias("fault_count"),

# After — count TEMP_HIGH specifically:
spark_sum(when(col("fault_code") == "TEMP_HIGH", 1).otherwise(0)).alias("fault_count"),
```

**Effect on output:** `fault_count` will now only count TEMP_HIGH events; BATTERY_LOW and ENGINE_FAULT will not increment the counter.

---

## S3 Data Layout

```
s3://<bucket>/
├── raw/
│   └── telemetry/
│       └── date=YYYY-MM-DD/
│           └── batch-<id>.json        (newline-delimited JSON)
└── curated/
    └── telemetry/
        └── date=YYYY-MM-DD/
            └── batch-<id>.parquet     (Snappy-compressed Parquet)
```

---

## CloudWatch Monitoring

When `CLOUDWATCH_ENABLED=true`:

| Metric | Description |
|---|---|
| `ApplicationStatus` | 1 = running, 0 = stopped |
| `BatchesProcessed` | Number of micro-batches processed |
| `RecordsProcessed` | Total records in each batch |
| `AggregatedRecords` | Records written to aggregated output |
| `InvalidRecords` | Records rejected by validation |
| `PipelineErrors` | Streaming query errors |

Log group: `/bmw-capstone-p11/streaming`

---

## Repository Structure

```
bmw_capstone_p11/
├── .github/workflows/python-tests.yml   # CI: pytest + Terraform
├── configs/sample.env                   # Environment variable template
├── sql/
│   ├── athena_setup.sql                 # Glue/Athena table DDL
│   ├── athena_queries.sql               # Analytical queries (Avg Speed, Battery, Temp, Faults)
│   └── snowflake_verification.sql       # LEGACY — not used; Athena is used instead
├── src/
│   ├── aggregation/window_aggregator.py # Python window helper (used in unit tests)
│   ├── generator/
│   │   ├── cli.py                       # CLI: generate and publish N events
│   │   └── telemetry_generator.py       # Random BMW telemetry event generator
│   ├── kafka/producer.py                # Kafka producer (acks=all, retries, serialization)
│   ├── sinks/
│   │   ├── cloudwatch.py                # CloudWatch metrics + logs sink
│   │   └── s3_writer.py                 # S3 raw JSON + curated Parquet sink
│   ├── streaming/
│   │   ├── pipeline.py                  # Core PySpark pipeline (readStream → aggregate)
│   │   ├── run_streaming.py             # Pipeline runner (entry point)
│   │   └── spark_session.py             # Spark session factory
│   ├── transformations/normalizer.py    # Field normalisation (vehicle ID, fault codes)
│   └── validation/
│       ├── schemas.py                   # Validation dataclasses
│       └── validators.py               # Field-level validation logic
├── terraform/
│   ├── main.tf                          # S3, CloudWatch, IAM, Glue Catalog, Athena
│   ├── outputs.tf                       # Resource outputs (bucket name, role ARN, etc.)
│   ├── providers.tf                     # AWS provider ~> 5.0
│   └── variables.tf                     # All configurable variables
├── tests/                               # 67 pytest tests (all passing)
├── docker-compose.yml                   # Local Kafka (apache/kafka:3.7.0, KRaft mode)
├── pyproject.toml                       # Project metadata and pytest config
└── requirements.txt                     # Python dependencies (incl. pyarrow for Parquet)
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `Unable to locate a Java Runtime` | Set `JAVA_HOME` to Java 17: `export JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home` |
| `UnsupportedOperationException: getSubject` | JDK version incompatible with PySpark 3.5. Use Java 17, not Java 24. |
| Kafka connection refused | Run `docker compose up -d kafka` first |
| S3 write fails | Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `S3_BUCKET` |
| CloudWatch fails | Set `CLOUDWATCH_ENABLED=true` and valid AWS credentials |
| No Athena results | Run `MSCK REPAIR TABLE bmw_capstone_p11.telemetry_aggregates` to load partitions |
| Streaming produces no output | Check watermark: events must be within the watermark delay of current time |
