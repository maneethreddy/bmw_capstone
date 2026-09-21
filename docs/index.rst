BMW Capstone P11 Documentation
================================

.. image:: https://img.shields.io/badge/python-3.10%2B-blue
   :alt: Python 3.10+

.. image:: https://img.shields.io/badge/PySpark-3.5.3-orange
   :alt: PySpark 3.5.3

.. image:: https://img.shields.io/badge/AWS-Athena%20%7C%20S3%20%7C%20CloudWatch-232F3E
   :alt: AWS Services

**BMW Capstone P11** is a real-time connected-vehicle telemetry platform built
with Apache Kafka, PySpark Structured Streaming, AWS S3/Athena, and a FastAPI
dashboard backend.

.. toctree::
   :maxdepth: 2
   :caption: User Guides

   guides/quickstart
   guides/architecture
   guides/configuration
   guides/terraform

.. toctree::
   :maxdepth: 3
   :caption: API Reference

   api/src
   api/src.streaming
   api/src.generator
   api/src.kafka
   api/src.sinks
   api/src.aggregation
   api/src.transformations
   api/src.validation
   api/api

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
