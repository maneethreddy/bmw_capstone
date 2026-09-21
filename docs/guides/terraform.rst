Infrastructure as Code (Terraform)
===================================

The ``terraform/`` directory contains Terraform (HCL) configurations that provision
and manage all AWS cloud infrastructure required by the BMW Capstone P11 telemetry platform.

Infrastructure Architecture
---------------------------

The provisioned AWS infrastructure supports the complete streaming lifecycle:

.. code-block:: text

   ┌────────────────────────────────────────────────────────────────────────┐
   │                         AWS Cloud Infrastructure                       │
   │                                                                        │
   │  ┌────────────────────────┐         ┌───────────────────────────────┐  │
   │  │ Amazon S3 Bucket       │         │ AWS Glue Data Catalog         │  │
   │  │ (Raw JSON & Curated    │         │ Database: bmw_capstone_p11    │  │
   │  │  Parquet Aggregates)   │◄────────┤ Table: telemetry_aggregates   │  │
   │  └───────────┬────────────┘         └───────────────┬───────────────┘  │
   │              ▲                                      ▲                  │
   │       Writes │                                      │ Reads metadata   │
   │  ┌───────────┴────────────┐                 ┌───────┴───────────────┐  │
   │  │ PySpark Streaming /    │                 │ Amazon Athena         │  │
   │  │ FastAPI App            │                 │ Serverless SQL Engine │  │
   │  │ (IAM Role Assigned)    │                 └───────────────┬───────┘  │
   │  └───────────┬────────────┘                                 │          │
   │              │ Logs & Metrics                               │ Queries  │
   │              ▼                                              ▼          │
   │  ┌────────────────────────┐                 ┌───────────────────────┐  │
   │  │ Amazon CloudWatch      │                 │ FastAPI Backend       │  │
   │  │ Logs & Metrics         │                 │ /api/telemetry        │  │
   │  └────────────────────────┘                 └───────────────────────┘  │
   └────────────────────────────────────────────────────────────────────────┘

Provisioned AWS Resources
-------------------------

1. Amazon S3 Bucket (``aws_s3_bucket.telemetry``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The primary storage location for both raw DLQ events and curated Parquet window aggregates:

* **Location format:**
  - Raw / DLQ: ``s3://<bucket_name>/raw/telemetry/``
  - Curated Aggregates: ``s3://<bucket_name>/curated/telemetry/date=YYYY-MM-DD/``
* **Security & Governance:**
  - **Public Access Block:** All public ACLs and bucket policies are blocked.
  - **Server-Side Encryption:** Default AES-256 server-side encryption (SSE-S3).
  - **Versioning:** Enabled to protect against accidental overwrites or deletions.

2. AWS Glue Data Catalog (``aws_glue_catalog_database`` & ``table``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Defines the external schema over curated Parquet files stored in S3 so that **Amazon Athena**
can query streaming aggregates with serverless SQL without requiring persistent ETL clusters:

* **Database:** ``bmw_capstone_p11`` (configurable via ``glue_database_name``)
* **Table:** ``telemetry_aggregates`` (EXTERNAL_TABLE)
* **Storage Format:** Snappy-compressed Parquet (``org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat``)
* **Partition Key:** ``date`` (string, formatted ``YYYY-MM-DD``)
* **Schema Columns:**

  .. list-table::
     :header-rows: 1
     :widths: 25 20 55

     * - Column Name
       - Hive / Athena Type
       - Description
     * - ``vehicle_id``
       - ``string``
       - BMW vehicle identifier (e.g. ``BMW-EV-001``)
     * - ``window_start``
       - ``timestamp``
       - Start timestamp of the 5-minute tumbling window
     * - ``window_end``
       - ``timestamp``
       - End timestamp of the 5-minute tumbling window
     * - ``average_speed``
       - ``double``
       - Mean vehicle speed (km/h) across the window
     * - ``average_battery_level``
       - ``double``
       - Mean battery state-of-charge (%)
     * - ``maximum_temperature``
       - ``double``
       - Peak motor/battery temperature (°C)
     * - ``fault_count``
       - ``bigint``
       - Count of non-NONE fault events in the window
     * - ``event_count``
       - ``bigint``
       - Total telemetry events recorded in the window

3. Amazon CloudWatch Log Group (``aws_cloudwatch_log_group.streaming``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Dedicated log group (default ``/bmw-capstone-p11/streaming``) for structured logs emitted
by PySpark streaming pipelines, API workers, and generator tasks:

* **Retention Period:** Configurable via ``log_retention_days`` (default: 14 days).

4. IAM Role & Least-Privilege Policies (``aws_iam_role.streaming``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

IAM role and inline policy granting least-privilege permissions to the runtime environment:

* **S3Write & S3List:** ``s3:PutObject``, ``s3:AbortMultipartUpload``, ``s3:ListBucket``, and ``s3:GetBucketLocation`` on the telemetry bucket.
* **CloudWatchLogs:** ``logs:CreateLogGroup``, ``logs:CreateLogStream``, ``logs:PutLogEvents``, and ``logs:DescribeLogStreams``.
* **CloudWatchMetrics:** ``cloudwatch:PutMetricData`` for operational latency and throughput metrics.
* **GlueRead:** ``glue:GetDatabase``, ``glue:GetTable``, and ``glue:GetPartitions`` for Athena query compilation.
* **AthenaQuery:** ``athena:StartQueryExecution``, ``athena:GetQueryExecution``, and ``athena:GetQueryResults``.

Variables Reference
-------------------

The configuration in ``terraform/variables.tf`` exposes the following variables:

.. list-table::
   :header-rows: 1
   :widths: 25 15 25 35

   * - Variable
     - Type
     - Default
     - Description
   * - ``aws_region``
     - ``string``
     - ``us-east-1``
     - AWS region for all telemetry infrastructure
   * - ``bucket_name``
     - ``string``
     - ``m-bmw-capstone-p11-raw``
     - Globally unique S3 bucket name
   * - ``iam_role_name``
     - ``string``
     - ``bmw-capstone-p11-streaming-role``
     - IAM role name for streaming runtime
   * - ``log_retention_days``
     - ``number``
     - ``14``
     - Retention period for CloudWatch logs (days)
   * - ``cloudwatch_log_group_name``
     - ``string``
     - ``/bmw-capstone-p11/streaming``
     - Log group name for streaming applications
   * - ``glue_database_name``
     - ``string``
     - ``bmw_capstone_p11``
     - Glue catalog database name for Athena
   * - ``glue_table_name``
     - ``string``
     - ``telemetry_aggregates``
     - Glue table name for curated aggregates
   * - ``tags``
     - ``map(string)``
     - See variables.tf
     - Resource tags applied to all AWS resources

Outputs Reference
-----------------

The outputs defined in ``terraform/outputs.tf`` provide values to populate your ``.env``:

* ``s3_bucket_name`` — S3 bucket name (maps to ``S3_BUCKET``).
* ``s3_bucket_arn`` — S3 bucket ARN.
* ``cloudwatch_log_group_name`` — CloudWatch log group.
* ``streaming_role_arn`` — ARN of the IAM role.
* ``glue_database_name`` — Glue database name (maps to ``ATHENA_DATABASE``).
* ``glue_table_name`` — Glue table name (maps to ``ATHENA_TABLE``).
* ``athena_query_hint`` — Ready-to-run verification query for Athena console or API:

.. code-block:: sql

   SELECT * FROM bmw_capstone_p11.telemetry_aggregates
   ORDER BY window_start DESC
   LIMIT 20;

Deployment Walkthrough
----------------------

Prerequisites
~~~~~~~~~~~~~

* `Terraform CLI <https://www.terraform.io/>`_ (v1.5.0 or later)
* AWS CLI installed and authenticated (``aws configure`` or SSO)
* IAM credentials with permissions to create S3 buckets, IAM roles, Glue catalogs, and CloudWatch groups.

1. Initialize Terraform
~~~~~~~~~~~~~~~~~~~~~~~~

Download required AWS provider plugins:

.. code-block:: bash

   cd terraform
   terraform init

2. Plan Infrastructure Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inspect the execution plan before creating resources:

.. code-block:: bash

   terraform plan -out=tfplan

3. Apply Configuration
~~~~~~~~~~~~~~~~~~~~~~

Apply the plan to provision the AWS cloud resources:

.. code-block:: bash

   terraform apply tfplan

4. Verify Outputs and Configure ``.env``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Print outputs and verify the provisioned resource names:

.. code-block:: bash

   terraform output

Copy the generated bucket and database values into your root ``.env`` file:

.. code-block:: bash

   AWS_REGION=us-east-1
   S3_BUCKET=m-bmw-capstone-p11-raw
   ATHENA_DATABASE=bmw_capstone_p11
   ATHENA_TABLE=telemetry_aggregates
   ATHENA_OUTPUT_LOCATION=s3://m-bmw-capstone-p11-raw/athena-results/

5. Tear Down (Clean up)
~~~~~~~~~~~~~~~~~~~~~~~

When finished with the capstone evaluation, destroy provisioned resources:

.. code-block:: bash

   terraform destroy
