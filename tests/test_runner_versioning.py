"""
Unit tests for XrayRunner version compatibility and config validation flow.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.xray_prism.runner import XrayRunner


class TestXrayRunnerVersioning(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_dir = Path(self.temp_dir.name)
        self.runner = XrayRunner(project_dir=str(self.project_dir))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_version_tuple(self):
        self.assertEqual(self.runner._parse_version_tuple("v26.1.13"), (26, 1, 13))
        self.assertEqual(self.runner._parse_version_tuple("26.2.6"), (26, 2, 6))
        self.assertIsNone(self.runner._parse_version_tuple("invalid"))

    def test_is_binary_compatible_compares_semver(self):
        with patch.object(self.runner, "get_binary_version", return_value="v26.1.13"):
            self.assertTrue(self.runner.is_binary_compatible("dummy.exe", minimum_version="v26.1.13"))

        with patch.object(self.runner, "get_binary_version", return_value="v24.12.18"):
            self.assertFalse(self.runner.is_binary_compatible("dummy.exe", minimum_version="v26.1.13"))


if __name__ == "__main__":
    unittest.main()
