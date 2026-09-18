-- =============================================================================
-- athena_setup.sql
-- BMW Capstone P11 — Athena / Glue Data Catalog setup
--
-- Purpose: Define the Athena external table over curated Parquet data in S3.
-- Athena queries S3 directly; no Glue ETL job is used.
--
-- Run order:
--   1. Create database (if running manually outside Terraform)
--   2. Create external table
--   3. Add partitions (or enable partition projection)
--
-- The Terraform configuration (terraform/main.tf) provisions the same
-- resources automatically via aws_glue_catalog_database and
-- aws_glue_catalog_table. Use these statements if you need to set up
-- manually in the Athena query editor.
-- =============================================================================

-- Step 1: Create the Glue database (Athena uses Glue Data Catalog)
CREATE DATABASE IF NOT EXISTS bmw_capstone_p11
COMMENT 'BMW Capstone P11 — real-time connected vehicle telemetry aggregates';


-- Step 2: Create the external table pointing at curated Parquet in S3
-- Replace <YOUR_BUCKET> with the actual bucket name (set via S3_BUCKET env var)
CREATE EXTERNAL TABLE IF NOT EXISTS bmw_capstone_p11.telemetry_aggregates (
    vehicle_id            STRING    COMMENT 'Normalized BMW vehicle identifier e.g. BMW-101',
    window_start          TIMESTAMP COMMENT 'Start of the event-time aggregation window',
    window_end            TIMESTAMP COMMENT 'End of the event-time aggregation window',
    average_speed         DOUBLE    COMMENT 'Average vehicle speed (km/h) within the window',
    average_battery_level DOUBLE    COMMENT 'Average battery charge level (%) within the window',
    maximum_temperature   DOUBLE    COMMENT 'Maximum engine/battery temperature (°C) within the window',
    fault_count           BIGINT    COMMENT 'Number of non-NONE fault events within the window',
    event_count           BIGINT    COMMENT 'Total telemetry events within the window'
)
PARTITIONED BY (
    date STRING COMMENT 'Processing date in YYYY-MM-DD format for efficient partition pruning'
)
STORED AS PARQUET
LOCATION 's3://<YOUR_BUCKET>/curated/telemetry/'
TBLPROPERTIES (
    'parquet.compress' = 'SNAPPY',
    'classification'   = 'parquet'
);


-- Step 3: Load newly written partitions so Athena can see them
-- Run this after the streaming pipeline writes new date partitions
MSCK REPAIR TABLE bmw_capstone_p11.telemetry_aggregates;


-- Step 4: Verify the table and its partitions
SHOW PARTITIONS bmw_capstone_p11.telemetry_aggregates;
