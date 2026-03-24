"""
Unit tests for SubscriptionService persistence behavior.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from api.services.subscription_service import SubscriptionService
from src.xray_prism.models import ProxyNode, Protocol


class TestSubscriptionService(unittest.TestCase):
    """Ensure subscription persistence stays consistent on fetch failures."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

        self.data_patcher = patch.object(SubscriptionService, "DATA_DIR", self.data_dir)
        self.file_patcher = patch.object(
            SubscriptionService,
            "SUBSCRIPTIONS_FILE",
            self.data_dir / "subscriptions.json"
        )
        self.data_patcher.start()
        self.file_patcher.start()

        self.service = SubscriptionService()

    def tearDown(self):
        self.data_patcher.stop()
        self.file_patcher.stop()
        self.temp_dir.cleanup()

    def test_create_subscription_does_not_persist_on_fetch_failure(self):
        """Invalid subscriptions must not be stored as empty successful records."""
        with patch("api.services.subscription_service.fetch_subscription", side_effect=ValueError("boom")):
            with self.assertRaises(ValueError):
                self.service.create_subscription("broken", "https://example.com/broken")

        with open(self.service.SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data, {"subscriptions": {}, "nodes": {}})

    def test_create_subscription_persists_subscription_and_nodes_together(self):
        """Successful create should atomically write both subscription and parsed nodes."""
        node = ProxyNode(
            name="demo-node",
            protocol=Protocol.TROJAN,
            address="demo.example.com",
            port=443,
            password="secret",
            tls=True,
        )

        with patch("api.services.subscription_service.fetch_subscription", return_value="trojan://demo"), \
             patch("api.services.subscription_service.parse_subscription", return_value=[node]):
            result = self.service.create_subscription("demo", "https://example.com/demo")

        self.assertEqual(result["node_count"], 1)
        self.assertIsNotNone(result["last_updated"])

        with open(self.service.SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data["subscriptions"]), 1)
        self.assertEqual(len(data["nodes"]), 1)

    def test_create_subscription_keeps_ssr_nodes_for_ui_display(self):
        """SSR-only subscriptions are persisted so frontend can render them as unsupported."""
        ssr_node = ProxyNode(
            name="SSR-demo",
            protocol=Protocol.SSR,
            address="ssr.example.com",
            port=443,
            password="secret",
            security="aes-256-cfb",
        )

        with patch("api.services.subscription_service.fetch_subscription", return_value="ssr://demo"), \
             patch("api.services.subscription_service.parse_subscription", side_effect=[[ssr_node], [ssr_node]]):
            result = self.service.create_subscription("ssr-only", "https://example.com/ssr")

        self.assertEqual(result["node_count"], 1)
        with open(self.service.SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["nodes"]), 1)
        stored = list(data["nodes"].values())[0]
        self.assertEqual(stored["protocol"], "ssr")

    def test_create_subscription_keeps_supported_and_unsupported_nodes(self):
        """Mixed subscriptions should keep runnable and unsupported recognized nodes."""
        trojan_node = ProxyNode(
            name="demo-node",
            protocol=Protocol.TROJAN,
            address="demo.example.com",
            port=443,
            password="secret",
            tls=True,
        )
        ssr_node = ProxyNode(
            name="SSR-demo",
            protocol=Protocol.SSR,
            address="ssr.example.com",
            port=443,
            password="secret",
            security="aes-256-cfb",
        )

        with patch("api.services.subscription_service.fetch_subscription", return_value="mixed"), \
             patch("api.services.subscription_service.parse_subscription", return_value=[trojan_node, ssr_node]):
            result = self.service.create_subscription("mixed", "https://example.com/mixed")

        self.assertEqual(result["node_count"], 2)

        with open(self.service.SUBSCRIPTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        stored_nodes = list(data["nodes"].values())
        self.assertEqual(len(stored_nodes), 2)
        self.assertEqual(sorted(item["protocol"] for item in stored_nodes), ["ssr", "trojan"])


if __name__ == "__main__":
    unittest.main()
