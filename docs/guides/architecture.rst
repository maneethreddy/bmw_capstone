Architecture
============

This page describes the end-to-end data flow of the BMW Capstone P11 platform.

High-Level Flow
---------------

.. code-block:: text

   ┌──────────────────────────────────────────────────────────────────┐
   │  Telemetry Generator                                             │
   │  src.generator.telemetry_generator                               │
   │  • Produces synthetic vehicle events (speed, battery, temp …)    │
   └──────────────────────┬───────────────────────────────────────────┘
                          │  JSON messages (vehicle_id keyed)
                          ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  Apache Kafka  (bmw-telemetry topic)                             │
   │  • At-least-once delivery, compacted topic                       │
   └──────────────────────┬───────────────────────────────────────────┘
                          │  Kafka readStream
                          ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │  PySpark Structured Streaming  (src.streaming)                   │
   │  ┌───────────────────────────────────────────────────────────┐   │
   │  │  pipeline.py                                               │   │
   │  │  1. read_kafka_events        — readStream from Kafka       │   │
   │  │  2. parse_and_validate_events — JSON schema + validation   │   │
   │  │     • Valid events  → watermark → dedup → aggregation      │   │
   │  │     • Invalid events → DLQ (console / S3 raw/)             │   │
   │  │  3. aggregate_events          — 5-min tumbling windows     │   │
   │  └───────────────────────────────────────────────────────────┘   │
   └────────────┬─────────────────────────────┬────────────────────────┘
                │ Valid aggregates             │ Invalid events (DLQ)
                ▼                             ▼
   ┌────────────────────────┐   ┌─────────────────────────────────────┐
   │  S3  (src.sinks)       │   │  Console sink (always-on)           │
   │  curated/ Parquet      │   │  raw/telemetry/ JSON  (S3)          │
   └────────────┬───────────┘   └─────────────────────────────────────┘
                │ Athena-crawled
                ▼
   ┌────────────────────────┐   ┌─────────────────────────────────────┐
   │  Amazon Athena         │   │  Amazon CloudWatch (src.sinks)      │
   │  bmw_capstone_p11 DB   │   │  BatchesProcessed, InvalidRecords…  │
   └────────────┬───────────┘   └─────────────────────────────────────┘
                │ SQL queries
                ▼
   ┌────────────────────────────────────────────────────────────────┐
   │  FastAPI backend  (api/)                                       │
   │  GET /api/telemetry  GET /api/summary  GET /api/faults         │
   └────────────────────────────┬───────────────────────────────────┘
                                │ JSON REST
                                ▼
   ┌────────────────────────────────────────────────────────────────┐
   │  React Dashboard  (frontend/)                                  │
   │  Summary cards, telemetry table, fault explorer                │
   └────────────────────────────────────────────────────────────────┘

Module Responsibilities
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Responsibility
   * - :mod:`src.generator`
     - Synthetic telemetry generation and Kafka publishing CLI
   * - :mod:`src.kafka`
     - Kafka producer abstraction with retry and serialization
   * - :mod:`src.streaming`
     - PySpark readStream, parse/validate, watermark, window aggregation
   * - :mod:`src.validation`
     - Schema definitions and field-level validation rules
   * - :mod:`src.transformations`
     - Fault-code normalization, timestamp canonicalization
   * - :mod:`src.aggregation`
     - Pure-Python window aggregation (used in tests and local mode)
   * - :mod:`src.sinks`
     - S3 writer (raw JSON + curated Parquet) and CloudWatch metrics
   * - :mod:`api`
     - FastAPI app, Athena client, local fallback reader, pipeline manager

Data Model
----------

Every vehicle event carries these fields:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Field
     - Type
     - Description
   * - ``vehicle_id``
     - ``str``
     - BMW vehicle identifier matching ``^BMW-[A-Z0-9-]+$``
   * - ``timestamp``
     - ``str``
     - ISO-8601 datetime with timezone (e.g. ``2024-01-15T10:30:00.000+00:00``)
   * - ``speed``
     - ``float``
     - Vehicle speed in km/h — valid range ``[0, 250]``
   * - ``battery_level``
     - ``float``
     - Battery state-of-charge in % — valid range ``[0, 100]``
   * - ``temperature``
     - ``float``
     - Motor/battery temperature in °C — valid range ``[-20, 120]``
   * - ``fault_code``
     - ``str``
     - One of ``NONE``, ``TEMP_HIGH``, ``BATTERY_LOW``, ``ENGINE_FAULT``
