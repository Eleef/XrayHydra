"""
Smoke checks for one-click startup scripts.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class TestStartScripts(unittest.TestCase):
    """Ensure startup scripts exist and keep their bootstrap contract."""

    def test_windows_start_script_bootstraps_and_runs_server(self):
        script = (ROOT / "start_windows.bat").read_text(encoding="utf-8")
        self.assertIn(".venv\\Scripts\\python.exe", script)
        self.assertIn("-m venv .venv", script)
        self.assertIn("pip install -r requirements.txt", script)
        self.assertIn("server.py %*", script)

    def test_linux_start_script_bootstraps_and_runs_server(self):
        script = (ROOT / "start_linux.sh").read_text(encoding="utf-8")
        self.assertIn(".venv/bin/python", script)
        self.assertIn("-m venv .venv", script)
        self.assertIn("pip install -r requirements.txt", script)
        self.assertIn('exec "$PYTHON" server.py "$@"', script)


if __name__ == "__main__":
    unittest.main()
