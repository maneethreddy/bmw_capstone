Quickstart
==========

This guide gets you from zero to a running BMW Connected Vehicle streaming
pipeline in under 10 minutes.

Prerequisites
-------------

* Python 3.10 or higher
* Java 11 or higher (required by PySpark)
* Docker (for the local Kafka broker)
* AWS credentials configured (``~/.aws/credentials`` or env vars) — *only needed for S3/Athena sinks*

Installation
------------

1. **Clone the repository** and create a virtual environment::

      git clone https://github.com/your-org/bmw_capstone_p11.git
      cd bmw_capstone_p11
      python -m venv .venv
      source .venv/bin/activate      # Windows: .venv\Scripts\activate

2. **Install Python dependencies**::

      pip install -e .
      pip install -r api/requirements.txt

3. **Copy and edit the sample environment file**::

      cp configs/sample.env .env
      # Edit .env with your AWS region, S3 bucket name, etc.

Running Locally
---------------

The pipeline requires three concurrently running processes.

Terminal 1 — Kafka broker
^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   docker compose up -d kafka

Terminal 2 — PySpark Structured Streaming
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   bmw-streaming
   # or: python -m src.streaming.run_streaming

Terminal 3 — Telemetry Generator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Send 100 events at 0.5-second intervals::

   python -m src.generator.cli --count 100 --interval 0.5

Terminal 4 — API + Dashboard
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   uvicorn api.main:app --reload --port 8000

Open the React dashboard at ``http://localhost:5173`` (start it with
``cd frontend && npm run dev``).

Running the Test Suite
----------------------

::

   pytest tests/ -v

Building the Documentation
--------------------------

::

   pip install -r docs/requirements.txt
   cd docs && make html

Open ``docs/_build/html/index.html`` in your browser.
