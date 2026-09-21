src.streaming — PySpark Structured Streaming
=============================================

The :mod:`src.streaming` package implements the PySpark Structured Streaming
pipeline that reads vehicle telemetry from Kafka, validates and aggregates
events, then writes results to S3 and CloudWatch.

Modules
-------

.. autosummary::
   :nosignatures:

   src.streaming.pipeline
   src.streaming.run_streaming
   src.streaming.spark_session

pipeline
--------

.. automodule:: src.streaming.pipeline
   :members:
   :undoc-members:
   :show-inheritance:

run\_streaming
--------------

.. automodule:: src.streaming.run_streaming
   :members:
   :undoc-members:
   :show-inheritance:

spark\_session
--------------

.. automodule:: src.streaming.spark_session
   :members:
   :undoc-members:
   :show-inheritance:
