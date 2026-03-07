"""
Tests for the generated Python SDK.
"""
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app


SDK_SRC = Path(__file__).resolve().parent.parent / "sdk" / "python" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from xray_prism_sdk import XrayPrismClient  # noqa: E402


class TestPythonSdk(unittest.TestCase):
    """Smoke-test the generated SDK against the in-process FastAPI app."""

    def setUp(self):
        self.transport = TestClient(app)
        self.client = XrayPrismClient(base_url="", client=self.transport)

    def tearDown(self):
        self.client.close()

    def test_can_call_system_status(self):
        data = self.client.get_system_status()
        self.assertIn("xray_status", data)
        self.assertIn("subscription_count", data)

    def test_can_call_list_subscriptions(self):
        data = self.client.list_subscriptions()
        self.assertIn("subscriptions", data)
        self.assertIn("total", data)

    def test_can_call_lease_stats(self):
        data = self.client.get_lease_stats()
        self.assertIn("total_available_proxies", data)
        self.assertIn("workspaces", data)

    def test_can_call_lease_status_and_exposes_new_methods(self):
        data = self.client.get_lease_status()
        self.assertIn("workspaces", data)
        self.assertTrue(hasattr(self.client, "set_manual_lease_cooldown"))
        self.assertTrue(hasattr(self.client, "recall_lease_cooldown"))


if __name__ == "__main__":
    unittest.main()
