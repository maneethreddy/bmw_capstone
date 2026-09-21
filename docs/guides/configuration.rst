Configuration Reference
========================

All runtime configuration is controlled via environment variables.
Copy ``configs/sample.env`` to ``.env`` in the project root and edit it
before starting any process.

Kafka Settings
--------------

.. envvar:: KAFKA_BOOTSTRAP_SERVERS

   Comma-separated list of Kafka broker addresses.

   **Default:** ``localhost:9092``

.. envvar:: KAFKA_TOPIC

   Name of the Kafka topic that carries telemetry events.

   **Default:** ``bmw-telemetry``

.. envvar:: KAFKA_RETRIES

   Number of producer retry attempts on transient errors.

   **Default:** ``3``

.. envvar:: KAFKA_REQUEST_TIMEOUT_MS

   Producer request timeout in milliseconds.

   **Default:** ``10000``

.. envvar:: KAFKA_LINGER_MS

   Producer linger time in milliseconds (batching window).

   **Default:** ``10``

PySpark Settings
----------------

.. envvar:: SPARK_MASTER

   Spark master URL.

   **Default:** ``local[*]`` (all available cores)

.. envvar:: SPARK_WINDOW_DURATION

   Tumbling window duration for aggregation.

   **Default:** ``5 minutes``

.. envvar:: SPARK_WATERMARK_DELAY

   Maximum allowed event-time delay before an event is dropped.

   **Default:** ``2 minutes``

.. envvar:: SPARK_CHECKPOINT_LOCATION

   Local or S3 path for Spark Structured Streaming checkpoints.

   **Default:** ``./checkpoints/bmw-telemetry``

.. envvar:: SPARK_KAFKA_PACKAGE

   Maven coordinate of the Spark–Kafka integration JAR.

   **Default:** ``org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3``

AWS Settings
------------

.. envvar:: AWS_REGION

   AWS region for S3, Athena, and CloudWatch.

   **Default:** ``us-east-1``

.. envvar:: S3_BUCKET

   Target S3 bucket name. Leave empty to disable the S3 sink.

   **Default:** *(empty — S3 sink disabled)*

.. envvar:: ATHENA_DATABASE

   Athena database / Glue catalog database name.

   **Default:** ``bmw_capstone_p11``

.. envvar:: ATHENA_TABLE

   Athena table name for aggregated telemetry windows.

   **Default:** ``telemetry_aggregates``

.. envvar:: ATHENA_OUTPUT_LOCATION

   S3 URI for Athena query result storage (``s3://bucket/path/``).

   **Required** when using the Athena backend.

CloudWatch Settings
-------------------

.. envvar:: CLOUDWATCH_ENABLED

   Set to ``true`` to emit operational metrics and log events to CloudWatch.

   **Default:** ``false``

