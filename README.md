# BMW Capstone P11 — Real-Time Connected Vehicle Streaming & Analytics

**Participant 11 · BMW TechWorks Capstone**

---

## Executive Summary & Objective

Modern BMW vehicles generate continuous telemetry streams — including speed, battery level, engine temperature, and diagnostic fault codes — at high velocity across connected vehicle fleets. The objective of this project is to implement an enterprise-grade, end-to-end streaming data pipeline that:

1. **Ingests** vehicle sensor streams at scale with zero event loss.
2. **Validates & Normalises** incoming data quality in real-time.
3. **Aggregates** fleet operational metrics over 1-minute tumbling windows using PySpark Structured Streaming.
4. **Persists** raw events and curated Parquet partitions to AWS S3.
5. **Queries** analytical aggregates serverlessly using AWS Athena.
6. **Delivers** an interactive operational dashboard (FastAPI + React) with one-click pipeline orchestration and live monitoring.

---

## Pipeline Architecture

```
┌────────────────────────┐
│  Telemetry Generator   │  (Simulates BMW connected sensors)
└───────────┬────────────┘
            │ JSON Events (speed, battery, temp, fault_code)
            ▼
┌────────────────────────┐
│      Apache Kafka      │  (Port 9092: Durable distributed message broker)
└───────────┬────────────┘
            │ Topic: telemetry-events
            ▼
┌────────────────────────┐
│   PySpark Streaming    │  (Structured Streaming Engine)
│                        │  · Schema enforcement & validation
│                        │  · 30s watermark for late data handling
│                        │  · 1-min tumbling window aggregations
└─────┬────────────┬─────┘
      │            │
      ▼            ▼
┌───────────┐ ┌───────────────┐
│ Console   │ │    AWS S3     │ (Curated Parquet partitions:
│ Sink / Log│ │               │  s3://<bucket>/curated/telemetry/date=YYYY-MM-DD/)
└─────┬─────┘ └───────┬───────┘
      │               │
      │               ▼
      │       ┌───────────────┐
      │       │  AWS Athena   │ (Serverless SQL via Glue Data Catalog)
      │       └───────┬───────┘
      │               │
      └───────┬───────┘
              ▼
    ┌───────────────────┐
    │  FastAPI Backend  │ (Port 8000: /api/summary, /api/telemetry, /api/faults)
    │                   │ · Production: AWS Athena queries
    │                   │ · Fallback: Live PySpark streaming parser (.spark.log)
    └─────────┬─────────┘
              ▼
    ┌───────────────────┐
    │  React Dashboard  │ (Port 5173: Real-time fleet KPIs, controls,
    │      (Vite)       │  aggregated micro-batches, fault diagnostics)
    └───────────────────┘
```

### Supporting Infrastructure
- **Terraform (`terraform/`)**: Provisions S3 buckets (versioned, AES-256 encrypted), Athena database & workgroup, Glue Catalog external tables, and CloudWatch metrics.
- **GitHub Actions (`.github/workflows/`)**: Continuous integration running Python test suites (Python 3.10, 3.11, 3.12 with Java 17 Temurin) and Terraform validation on every push.

---

## Prerequisites

Before running the project, ensure your environment has:

| Prerequisite | Minimum Version | Purpose |
|---|---|---|
| **Docker & Docker Compose** | Docker Desktop 20+ | Runs the Apache Kafka 3.7 broker container |
| **Python** | 3.10, 3.11, or 3.12 | PySpark pipeline, Telemetry Generator, FastAPI backend |
| **Java (JDK)** | Java 17 (recommended) or 11 | Required by Apache Spark 3.5.3 |
| **Node.js & npm** | Node 18+ (LTS) & npm 9+ | React dashboard dev server & production build |
| **AWS CLI & Credentials** | AWS CLI v2 | Configured credentials with permissions for S3, Athena, and Glue |

> **Setting up Java 17:**
> - **macOS (Homebrew):** `brew install openjdk@17`
> - **Ubuntu / Debian:** `sudo apt install openjdk-17-jdk`
> - `start.sh` automatically detects standard Java 17 installations and sets `JAVA_HOME`.

---

## Quick Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/maneethreddy/bmw_capstone.git
cd bmw_capstone
```

### 1. Python Environment Setup

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Frontend Dependencies Setup

```bash
cd frontend
npm install
cd ..
```

---

## Starting the Project

### Option A: One-Command Startup (Recommended)

Run the master startup script:

```bash
bash start.sh
```

**What `start.sh` does automatically:**
1. Validates and configures `JAVA_HOME` (OpenJDK 17).
2. Checks/creates `.venv` and ensures dependencies are present.
3. Launches Kafka in Docker (`docker compose up -d`).
4. Starts the FastAPI backend server on `http://localhost:8000`.
5. Starts the React Vite development server on `http://localhost:5173`.
6. Automatically opens `http://localhost:5173` in your default browser.
7. Gracefully traps `Ctrl+C` to cleanly stop all background processes and containers.

---

### Option B: Manual Multi-Terminal Startup

If you prefer to observe each component independently in its own terminal:

#### Terminal 1 — Start Kafka
```bash
docker compose up -d kafka
docker compose ps   # verify state is "Up"
```

#### Terminal 2 — Start PySpark Streaming Pipeline
```bash
source .venv/bin/activate
python -m src.streaming.run_streaming \
  --window-duration "1 minute" \
  --watermark-delay "30 seconds" \
  --checkpoint ./checkpoints/demo
```
*Leave this running. As events arrive, PySpark prints tumbling window aggregates to the console.*

#### Terminal 3 — Start FastAPI Backend
```bash
source .venv/bin/activate
uvicorn api.main:app --port 8000
```

#### Terminal 4 — Start React Frontend
```bash
cd frontend
npm run dev -- --port 5173
```
*Open `http://localhost:5173` in your browser.*

---

## Operating the Dashboard

The dashboard provides an intuitive interface for evaluating the full streaming lifecycle:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  BMW Connected Mobility — Real-Time Vehicle Telemetry                    │
├──────────────────────────────────────────────────────────────────────────┤
│  [ ▶ START KAFKA ]       [ ▶ START SPARK ]       [ ⚡ GENERATE DATA ]     │
├──────────────────────────────────────────────────────────────────────────┤
│  Pipeline Flow: Kafka ──▶ Spark ──▶ S3 ──▶ Athena               ● Live   │
├──────────────────────────────────────────────────────────────────────────┤
│  [KPIs] Vehicles: 96 | Events: 296 | Windows: 271 | Faults: 226 | ...     │
├──────────────────────────────────────────────────────────────────────────┤
│  [Aggregated Windows Table] (Batch, Vehicle, Window Start/End, Averages) │
├──────────────────────────────────────────────────────────────────────────┤
│  [Active Fault Monitoring] (ERR_BATTERY_OVERHEAT, ERR_MOTOR_OVERTEMP)    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1. Interactive Pipeline Controls
- **Start Kafka**: Sends a request to FastAPI to execute `docker compose up -d kafka`.
- **Start Spark**: Launches the background PySpark streaming query (`run_streaming.py`) configured with 1-minute tumbling windows and 30-second watermarks.
- **Generate Data**: Executes `python -m src.generator.cli --count 20 --interval 0.2` to publish a new batch of 20 realistic telemetry events to Kafka.

### 2. What Happens When "Generate Data" Is Clicked?
1. The frontend calls `POST /api/pipeline/generate-data`.
2. The telemetry generator creates 20 events representing active BMW test vehicles (speed: 0–250 km/h, battery: 0–100%, temperature: -20–120 °C, diagnostic trouble codes).
3. Events are published to Kafka topic `telemetry-events`.
4. The running PySpark streaming query reads the Kafka stream, validates fields, maps fault codes, enforces watermarks, and computes sliding window aggregates.
5. PySpark emits the micro-batch to console/logs and writes partitioned Parquet files to S3.
6. The FastAPI backend serves the latest batch records.
7. The React dashboard refreshes (via 10-second auto-poll or manual "Refresh Now"), updating the KPI cards, appending new window batches to the table, and reporting active faults.

## Cloud Architecture: AWS S3 & Athena

The production architecture continuously streams, persists, and queries vehicle analytics directly on AWS:

### 1. S3 Curated Lakehouse Storage
- PySpark Structured Streaming partitions curated micro-batch aggregates into Amazon S3 using snappy-compressed Apache Parquet format:
  ```
  s3://<telemetry-bucket>/curated/telemetry/date=YYYY-MM-DD/
  ```
- Raw incoming events are simultaneously persisted for compliance and auditing.

### 2. AWS Athena Serverless SQL Analytics
- The AWS Glue Data Catalog maintains the external table definition `telemetry_aggregates` over the curated Parquet dataset.
- The FastAPI backend queries Athena via Boto3 with parameterized analytical SQL:
  ```sql
  SELECT vehicle_id, window_start, window_end, average_speed,
         average_battery_level, maximum_temperature, fault_count, event_count
  FROM "bmw_capstone_p11"."telemetry_aggregates"
  ORDER BY window_start DESC
  LIMIT 100;
  ```
- Queries run serverlessly against S3 Parquet, returning sub-second operational views to the dashboard.

### 3. Provisioning Cloud Infrastructure (Terraform)
To provision the required AWS resources (S3 buckets, Athena workgroup, Glue Catalog, and IAM policies):
```bash
cd terraform
terraform init
terraform apply
```

### 4. Local Development Fallback
For local workstation development or testing prior to cloud deployment:
- FastAPI includes a local streaming reader (`api/local_reader.py`) that reads micro-batch aggregates directly from PySpark streaming logs (`.spark.log`).
- This allows running and verifying the entire pipeline locally without requiring active cloud connectivity.

---

## Resetting Demo State

To clean up and reset your local demo environment between demonstration runs:

```bash
bash reset_demo.sh
```

**What `reset_demo.sh` does:**
1. Safely terminates background PySpark, FastAPI, and Vite processes.
2. Stops and removes the local Kafka Docker container and resets topic data (`docker compose down -v`).
3. Clears streaming checkpoints (`checkpoints/`).
4. Clears local execution logs (`.spark.log`, `.api.log`, `.frontend.log`) and PID markers.

> **Safety Guarantee:** `reset_demo.sh` only clears local temporary runtime state. It **never** touches Terraform state, AWS cloud infrastructure, or project source code.

---

## Log Locations

When troubleshooting or observing background services, check these local log files in the project root:

| Log File | Component | Description |
|---|---|---|
| `.spark.log` | PySpark Structured Streaming | Micro-batch aggregation tables, trigger statistics, schema logs |
| `.api.log` | FastAPI Server | API endpoint access logs, query execution times, error traces |
| `.frontend.log` | Vite Dev Server | Frontend bundler logs, hot module reload (HMR) events |

---

## Stopping the Project

- If running via `bash start.sh`, simply press **`Ctrl+C`** in the terminal. The script traps the interrupt and stops all servers and containers cleanly.
- Alternatively, run `bash reset_demo.sh` at any time to ensure all background processes and containers are stopped.

---

## Testing & Quality Assurance

Verify that the entire repository meets evaluation standards:

### 1. Python Test Suite (134 Tests)
```bash
source .venv/bin/activate
pytest -v
```
*Tests coverage: Schema validation, normalization, 1-minute tumbling aggregations, watermark boundaries, Kafka producer serialization, S3 writers, CloudWatch metrics, FastAPI endpoints, and pipeline manager orchestration.*

### 2. Frontend Production Build & Linting
```bash
cd frontend
npm run build    # Validates bundle compilation with zero errors
npm run lint     # Validates ESLint / Oxlint code quality
cd ..
```

### 3. Python Bytecode Compilation
```bash
python -m compileall -q src tests api
```

### 4. Terraform Infrastructure Validation
```bash
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
```

---

## Repository Structure

```
bmw_capstone/
├── .github/workflows/          # GitHub Actions CI workflow (Python tests, Terraform checks)
├── api/                        # FastAPI backend
│   ├── main.py                 # REST API endpoints (/health, /summary, /telemetry, /faults)
│   ├── athena_client.py        # AWS Athena client
│   ├── local_reader.py         # Real-time PySpark streaming log fallback parser
│   ├── pipeline_manager.py     # Terminal-equivalent pipeline command runner
│   └── tests/                  # API unit & integration tests
├── checkpoints/                # Local PySpark streaming state store (git-ignored)
├── docker-compose.yml          # Kafka broker container specification
├── docs/                       # Sphinx technical documentation source
├── frontend/                   # React + Vite web dashboard
│   ├── src/
│   │   ├── components/         # Pipeline controls, status flow, KPI cards, telemetry table
│   │   ├── hooks/              # useTelemetry polling hook
│   │   └── App.jsx             # Dashboard root layout
│   └── package.json            # Frontend dependencies & build scripts
├── pyproject.toml              # Project metadata & build tool configuration
├── requirements.txt            # Root Python dependencies
├── reset_demo.sh               # Local demo state reset script
├── src/                        # Core streaming pipeline package
│   ├── aggregation/            # PySpark window aggregation logic
│   ├── generator/              # Synthetic BMW telemetry event generator & CLI
│   ├── kafka/                  # Kafka producer & message serializer
│   ├── sinks/                  # S3 Parquet/JSON writers & CloudWatch metrics
│   ├── streaming/              # PySpark Structured Streaming application
│   ├── transformations/        # Field normalizers & converters
│   └── validation/             # Pydantic & PySpark schema validators
├── start.sh                    # Master one-click startup script
├── terraform/                  # Infrastructure as Code (S3, Athena, Glue, IAM)
└── tests/                      # Pytest unit & integration test suite (134 tests)
```
