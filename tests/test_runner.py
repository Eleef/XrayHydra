"""
Unit tests for cross-platform XrayRunner process tracking.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.xray_prism.runner import XrayRunner


class TestXrayRunner(unittest.TestCase):
    """Test project-scoped process tracking without global process killing."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name)
        self.runner = XrayRunner(
            xray_path=str(self.project_dir / "bin" / "xray.exe"),
            project_dir=str(self.project_dir)
        )

        self.config_path = self.project_dir / "config.json"
        self.config_path.write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_start_writes_process_metadata(self):
        """Start should persist project-owned process metadata."""
        process = MagicMock()
        process.pid = 4321
        process.poll.return_value = None

        with patch.object(self.runner, "validate_config", return_value=(True, "")), \
             patch("src.xray_prism.runner.subprocess.Popen", return_value=process):
            self.runner.start(str(self.config_path))

        metadata = json.loads(self.runner.process_info_file.read_text(encoding="utf-8"))
        self.assertEqual(metadata["pid"], 4321)
        self.assertEqual(
            Path(metadata["xray_path"]).resolve(strict=False),
            Path(self.runner.xray_path).resolve(strict=False)
        )
        self.assertEqual(
            Path(metadata["config_path"]).resolve(strict=False),
            self.config_path.resolve(strict=False)
        )

    def test_get_tracked_process_pid_requires_matching_executable_and_config(self):
        """Only a matching recorded process may be reclaimed after restart."""
        self.runner._write_process_metadata(
            pid=5678,
            xray_path=self.runner.xray_path,
            config_path=str(self.config_path)
        )

        with patch.object(self.runner, "_pid_exists", return_value=True), \
             patch.object(self.runner, "_get_process_executable", return_value=self.runner.xray_path), \
             patch.object(
                 self.runner,
                 "_get_process_cmdline",
                 return_value=[self.runner.xray_path, "run", "-config", str(self.config_path)]
             ):
            tracked_pid = self.runner._get_tracked_process_pid()

        self.assertEqual(tracked_pid, 5678)

    def test_get_tracked_process_pid_rejects_mismatched_executable(self):
        """A reused PID with another executable must not be terminated."""
        self.runner._write_process_metadata(
            pid=9999,
            xray_path=self.runner.xray_path,
            config_path=str(self.config_path)
        )

        with patch.object(self.runner, "_pid_exists", return_value=True), \
             patch.object(self.runner, "_get_process_executable", return_value=str(self.project_dir / "bin" / "other.exe")):
            tracked_pid = self.runner._get_tracked_process_pid()

        self.assertIsNone(tracked_pid)
        self.assertFalse(self.runner.process_info_file.exists())

    def test_stop_uses_tracked_process_when_in_memory_process_missing(self):
        """Stop should reclaim the recorded project-owned process after service restart."""
        self.runner._write_process_metadata(
            pid=2468,
            xray_path=self.runner.xray_path,
            config_path=str(self.config_path)
        )

        with patch.object(self.runner, "_get_tracked_process_pid", return_value=2468), \
             patch.object(self.runner, "_terminate_pid") as terminate_pid:
            self.runner.stop()

        terminate_pid.assert_called_once_with(2468)
        self.assertFalse(self.runner.process_info_file.exists())


if __name__ == "__main__":
    unittest.main()
