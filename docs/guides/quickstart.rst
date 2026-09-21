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

      git clone https://github.com/maneethreddy/bmw_capstone.git
      cd bmw_capstone
      python3 -m venv .venv
      source .venv/bin/activate      # Windows: .venv\Scripts\activate

2. **Install Python and Frontend dependencies**::

      pip install -r requirements.txt
      cd frontend && npm install && cd ..

Starting the Pipeline
---------------------

Option A: One-Command Startup (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Run the master startup script to launch Kafka, FastAPI, and Vite automatically::

   bash start.sh

Option B: Manual Multi-Terminal Startup
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Terminal 1 — Kafka broker::

   docker compose up -d kafka

Terminal 2 — PySpark Structured Streaming::

   python -m src.streaming.run_streaming \
     --window-duration "1 minute" \
     --watermark-delay "30 seconds" \
     --checkpoint ./checkpoints/demo

Terminal 3 — Telemetry Generator::

   python -m src.generator.cli --count 20 --interval 0.2

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
