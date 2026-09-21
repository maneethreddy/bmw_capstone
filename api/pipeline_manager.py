"""BMW Capstone P11 — Local Pipeline Command Runner.

Executes the exact 3 local terminal commands:
  1. Start Kafka:
     docker compose up -d kafka
  2. Start PySpark Streaming:
     python -m src.streaming.run_streaming \
       --window-duration "1 minute" \
       --watermark-delay "30 seconds" \
       --checkpoint ./checkpoints/demo
  3. Generate Telemetry:
     python -m src.generator.cli --count 20 --interval 0.2
"""

from __future__ import annotations

import logging
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).resolve().parent.parent
SPARK_PID_FILE = PROJECT_DIR / ".spark.pid"
SPARK_LOG_FILE = PROJECT_DIR / ".spark.log"


def find_java_home() -> Optional[str]:
    """Find a valid JAVA_HOME path for PySpark."""
    if "JAVA_HOME" in os.environ:
        candidate = Path(os.environ["JAVA_HOME"])
        if (candidate / "bin" / "java").exists():
            return str(candidate)

    known_candidates = [
        Path("/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"),
        Path("/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home"),
        Path("/usr/local/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"),
        Path("/usr/local/opt/openjdk/libexec/openjdk.jdk/Contents/Home"),
    ]
    for c in known_candidates:
        if (c / "bin" / "java").exists():
            return str(c)

    try:
        res = subprocess.run(["/usr/libexec/java_home"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            candidate = Path(res.stdout.strip())
            if (candidate / "bin" / "java").exists():
                return str(candidate)
    except Exception:
        pass

    jvm_dir = Path("/Library/Java/JavaVirtualMachines")
    if jvm_dir.exists():
        for p in jvm_dir.glob("*/Contents/Home"):
            if (p / "bin" / "java").exists():
                return str(p)

    # Common Linux locations (Ubuntu/Debian/CentOS/Fedora)
    linux_candidates = [
        Path("/usr/lib/jvm/default-java"),
        Path("/usr/lib/jvm/java-17-openjdk-amd64"),
        Path("/usr/lib/jvm/java-11-openjdk-amd64"),
        Path("/usr/lib/jvm/java-17-openjdk-arm64"),
        Path("/usr/lib/jvm/java-11-openjdk-arm64"),
        Path("/usr/lib/jvm/java-17-openjdk"),
        Path("/usr/lib/jvm/java-11-openjdk"),
    ]
    for c in linux_candidates:
        if (c / "bin" / "java").exists():
            return str(c)

    # Check which java in PATH and resolve symlink to JAVA_HOME
    java_bin = shutil.which("java")
    if java_bin:
        try:
            resolved = Path(java_bin).resolve()
            # If java is in <JAVA_HOME>/bin/java
            if resolved.parent.name == "bin" and (resolved.parent.parent / "bin" / "java").exists():
                return str(resolved.parent.parent)
        except Exception:
            pass

    return None


class PipelineManager:
    """Executes the 3 existing terminal pipeline commands."""

    def __init__(self, project_dir: Path = PROJECT_DIR) -> None:
        self.project_dir = project_dir
        self._spark_proc: Optional[subprocess.Popen] = None

    # -----------------------------------------------------------------------
    # 1. Start Kafka
    # -----------------------------------------------------------------------

    def start_kafka(self) -> Dict[str, Any]:
        """Run Terminal 1 command: docker compose up -d kafka."""
        docker_bin = shutil.which("docker")
        if not docker_bin:
            raise RuntimeError("Docker is not installed or not found in PATH.")

        cmd = [docker_bin, "compose", "up", "-d", "kafka"]
        cmd_str = "docker compose up -d kafka"
        logger.info("Executing Kafka command: %s", cmd_str)

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_dir),
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Kafka startup timed out after 30 seconds.") from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to execute '{cmd_str}': {exc}") from exc

        if res.returncode != 0:
            err_msg = res.stderr.strip() or res.stdout.strip() or f"Command exited with code {res.returncode}"
            logger.error("Kafka startup failed: %s", err_msg)
            raise RuntimeError(err_msg)

        output = res.stdout.strip() or res.stderr.strip() or "Kafka started successfully."
        return {
            "status": "success",
            "command": cmd_str,
            "output": output,
        }

    # -----------------------------------------------------------------------
    # 2. Start PySpark Streaming
    # -----------------------------------------------------------------------

    def is_spark_running(self) -> bool:
        """Check if PySpark streaming process is currently running."""
        if self._spark_proc is not None:
            if self._spark_proc.poll() is None:
                return True
            self._spark_proc = None

        if SPARK_PID_FILE.exists():
            try:
                pid = int(SPARK_PID_FILE.read_text().strip())
                os.kill(pid, 0)
                ps_res = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "command="],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if "src.streaming.run_streaming" in ps_res.stdout:
                    return True
                SPARK_PID_FILE.unlink(missing_ok=True)
            except (OSError, ValueError, subprocess.SubprocessError):
                SPARK_PID_FILE.unlink(missing_ok=True)

        return False

    def start_spark(self) -> Dict[str, Any]:
        """Run Terminal 2 command: python -m src.streaming.run_streaming ..."""
        cmd_str = (
            'python -m src.streaming.run_streaming '
            '--window-duration "1 minute" '
            '--watermark-delay "30 seconds" '
            '--checkpoint ./checkpoints/demo'
        )

        if self.is_spark_running():
            logger.info("PySpark streaming is already running.")
            return {
                "status": "success",
                "command": cmd_str,
                "output": "PySpark streaming is already running.",
            }

        python_bin = sys.executable
        cmd = [
            python_bin,
            "-m",
            "src.streaming.run_streaming",
            "--window-duration",
            "1 minute",
            "--watermark-delay",
            "30 seconds",
            "--checkpoint",
            "./checkpoints/demo",
        ]

        env = os.environ.copy()
        java_home = find_java_home()
        if java_home:
            env["JAVA_HOME"] = java_home
            java_bin = str(Path(java_home) / "bin")
            env["PATH"] = f"{java_bin}:{env.get('PATH', '')}"

        logger.info("Executing PySpark streaming command: %s", cmd_str)
        try:
            log_file = open(SPARK_LOG_FILE, "a", encoding="utf-8")
            self._spark_proc = subprocess.Popen(
                cmd,
                cwd=str(self.project_dir),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env,
            )
            SPARK_PID_FILE.write_text(str(self._spark_proc.pid))
        except Exception as exc:
            logger.exception("Failed to launch PySpark streaming: %s", exc)
            raise RuntimeError(f"Failed to launch PySpark: {exc}") from exc

        # Check if process immediately exited
        time.sleep(0.5)
        if self._spark_proc.poll() is not None:
            exit_code = self._spark_proc.poll()
            err_output = ""
            if SPARK_LOG_FILE.exists():
                try:
                    lines = SPARK_LOG_FILE.read_text(encoding="utf-8").splitlines()
                    err_output = "\n".join(lines[-10:])
                except Exception:
                    pass
            self._spark_proc = None
            SPARK_PID_FILE.unlink(missing_ok=True)
            raise RuntimeError(
                f"PySpark streaming exited immediately (code {exit_code}):\n{err_output or 'Unknown error'}"
            )

        return {
            "status": "success",
            "command": cmd_str,
            "output": "PySpark streaming started.",
        }

    # -----------------------------------------------------------------------
    # 3. Generate Telemetry Data
    # -----------------------------------------------------------------------

    def generate_data(self) -> Dict[str, Any]:
        """Run Terminal 3 command: python -m src.generator.cli --count 20 --interval 0.2."""
        python_bin = sys.executable
        cmd = [
            python_bin,
            "-m",
            "src.generator.cli",
            "--count",
            "20",
            "--interval",
            "0.2",
        ]
        cmd_str = "python -m src.generator.cli --count 20 --interval 0.2"
        logger.info("Executing Telemetry generator command: %s", cmd_str)

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_dir),
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Telemetry generator timed out after 30 seconds.") from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to execute '{cmd_str}': {exc}") from exc

        if res.returncode != 0:
            err_msg = res.stderr.strip() or res.stdout.strip() or f"Command exited with code {res.returncode}"
            logger.error("Telemetry generator failed: %s", err_msg)
            raise RuntimeError(err_msg)

        output = res.stdout.strip() or res.stderr.strip() or "Generated 20 events."
        return {
            "status": "success",
            "command": cmd_str,
            "output": output,
        }


# Global manager singleton
pipeline_manager = PipelineManager()
