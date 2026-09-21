"""Unit tests for simplified api.pipeline_manager.PipelineManager."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from api.pipeline_manager import PipelineManager


@pytest.fixture
def manager(tmp_path):
    return PipelineManager(project_dir=tmp_path)


class TestPipelineManagerUnit:
    # -----------------------------------------------------------------------
    # 1. start_kafka
    # -----------------------------------------------------------------------

    def test_start_kafka_success(self, manager):
        with patch("shutil.which", return_value="/usr/local/bin/docker"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Container kafka Started", stderr="")
            res = manager.start_kafka()
            assert res["status"] == "success"
            assert res["command"] == "docker compose up -d kafka"
            assert "Started" in res["output"]

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert cmd == ["/usr/local/bin/docker", "compose", "up", "-d", "kafka"]

    def test_start_kafka_no_docker_raises(self, manager):
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="Docker is not installed"):
                manager.start_kafka()

    def test_start_kafka_failure_raises_actual_error(self, manager):
        with patch("shutil.which", return_value="/usr/local/bin/docker"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Cannot connect to the Docker daemon",
            )
            with pytest.raises(RuntimeError, match="Cannot connect to the Docker daemon"):
                manager.start_kafka()

    # -----------------------------------------------------------------------
    # 2. start_spark
    # -----------------------------------------------------------------------

    def test_is_spark_running_with_active_proc(self, manager):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        manager._spark_proc = mock_proc
        assert manager.is_spark_running() is True

    def test_is_spark_running_false_when_no_proc(self, manager):
        manager._spark_proc = None
        with patch("pathlib.Path.exists", return_value=False):
            assert manager.is_spark_running() is False

    def test_start_spark_already_running_no_duplicate(self, manager):
        with patch.object(manager, "is_spark_running", return_value=True), \
             patch("subprocess.Popen") as mock_popen:
            res = manager.start_spark()
            assert res["status"] == "success"
            assert "already running" in res["output"]
            mock_popen.assert_not_called()

    def test_start_spark_launches_command(self, manager):
        with patch.object(manager, "is_spark_running", return_value=False), \
             patch("subprocess.Popen") as mock_popen, \
             patch("time.sleep"):
            mock_proc = MagicMock()
            mock_proc.pid = 12345
            mock_proc.poll.return_value = None
            mock_popen.return_value = mock_proc

            res = manager.start_spark()
            assert res["status"] == "success"
            assert "started" in res["output"]

            mock_popen.assert_called_once()
            cmd = mock_popen.call_args[0][0]
            assert "-m" in cmd
            assert "src.streaming.run_streaming" in cmd
            assert "--window-duration" in cmd
            assert "1 minute" in cmd
            assert "--watermark-delay" in cmd
            assert "30 seconds" in cmd
            assert "--checkpoint" in cmd

    def test_start_spark_immediate_exit_raises_actual_error(self, manager):
        with patch.object(manager, "is_spark_running", return_value=False), \
             patch("subprocess.Popen") as mock_popen, \
             patch("time.sleep"):
            mock_proc = MagicMock()
            mock_proc.pid = 12345
            mock_proc.poll.return_value = 1
            mock_popen.return_value = mock_proc

            with pytest.raises(RuntimeError, match="PySpark streaming exited immediately"):
                manager.start_spark()

    # -----------------------------------------------------------------------
    # 3. generate_data
    # -----------------------------------------------------------------------

    def test_generate_data_executes_cli(self, manager):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Published 20 events", stderr="")
            res = manager.generate_data()
            assert res["status"] == "success"
            assert res["command"] == "python -m src.generator.cli --count 20 --interval 0.2"

            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "-m" in cmd
            assert "src.generator.cli" in cmd
            assert "--count" in cmd
            assert "20" in cmd
            assert "--interval" in cmd
            assert "0.2" in cmd

    def test_generate_data_failure_raises_actual_error(self, manager):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="KafkaTimeoutError: Failed to update metadata after 30.0 secs.",
            )
            with pytest.raises(RuntimeError, match="KafkaTimeoutError"):
                manager.generate_data()
