"""
Unit tests for ProxyService health-state synchronization.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from api.services.proxy_service import ProxyService


class TestProxyService(unittest.TestCase):
    """Verify proxy runtime changes keep health state in sync."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.proxies_file = self.data_dir / "active_proxies.json"
        self.config_file = self.data_dir / "config.json"
        self.config_file.write_text("{}", encoding="utf-8")

        self.data_patcher = patch.object(ProxyService, "DATA_DIR", self.data_dir)
        self.file_patcher = patch.object(ProxyService, "PROXIES_FILE", self.proxies_file)
        self.config_patcher = patch.object(ProxyService, "CONFIG_FILE", self.config_file)
        self.data_patcher.start()
        self.file_patcher.start()
        self.config_patcher.start()

        self.service = ProxyService()

    def tearDown(self):
        self.data_patcher.stop()
        self.file_patcher.stop()
        self.config_patcher.stop()
        self.temp_dir.cleanup()

    def _write_proxies(self, proxies):
        with open(self.proxies_file, "w", encoding="utf-8") as f:
            json.dump({"proxies": proxies, "start_port": 10000}, f, ensure_ascii=False, indent=2)

    def test_add_proxies_while_stopped_clears_health_state(self):
        """Configured proxies should not remain leaseable while Xray is stopped."""
        mock_subscription_service = MagicMock()
        mock_subscription_service.get_nodes_by_ids.return_value = [{
            "id": "node_1",
            "name": "Node 1",
            "protocol": "trojan",
            "address": "demo.example.com",
            "port": 443,
        }]
        mock_health_service = MagicMock()

        with patch("api.services.proxy_service.get_subscription_service", return_value=mock_subscription_service), \
             patch("api.services.proxy_service.get_health_service", return_value=mock_health_service):
            added = self.service.add_proxies(["node_1"])

        self.assertEqual(len(added), 1)
        mock_health_service.sync_with_proxies.assert_called_once_with([])
        mock_health_service.stop_monitoring.assert_called_once()

    def test_remove_proxy_while_running_syncs_remaining_ports(self):
        """Removing a live proxy must immediately remove its health state."""
        self._write_proxies([
            {"port": 10000, "node_id": "node_1", "node_name": "Node 1", "protocol": "trojan", "address": "a", "server_port": 443},
            {"port": 10001, "node_id": "node_2", "node_name": "Node 2", "protocol": "trojan", "address": "b", "server_port": 443},
        ])
        self.service._load_data()
        self.service._runner = MagicMock()
        self.service._runner.is_running.return_value = True

        mock_health_service = MagicMock()
        with patch.object(self.service, "_regenerate_config", return_value=str(self.config_file)), \
             patch("api.services.proxy_service.get_health_service", return_value=mock_health_service):
            removed = self.service.remove_proxy(10000)

        self.assertTrue(removed)
        self.service._runner.stop.assert_called_once()
        self.service._runner.start.assert_called_once_with(str(self.config_file))
        mock_health_service.sync_with_proxies.assert_called_once_with([10001])

    def test_stop_xray_clears_health_state_even_when_process_already_stopped(self):
        """Stop should clear stale health states even without an in-memory process."""
        self._write_proxies([
            {"port": 10000, "node_id": "node_1", "node_name": "Node 1", "protocol": "trojan", "address": "a", "server_port": 443},
        ])
        self.service._load_data()
        self.service._runner = None

        mock_health_service = MagicMock()
        with patch("api.services.proxy_service.get_health_service", return_value=mock_health_service):
            result = self.service.stop_xray()

        self.assertTrue(result["success"])
        mock_health_service.sync_with_proxies.assert_called_once_with([])
        mock_health_service.stop_monitoring.assert_called_once()

    def test_regenerate_config_uses_socks_inbound_for_mixed_port_clients(self):
        """Generated config should expose socks inbound so one port supports socks5 and HTTP clients."""
        self._write_proxies([
            {"port": 10022, "node_id": "node_1", "node_name": "Node 1", "protocol": "trojan", "address": "a", "server_port": 443},
        ])
        self.service._load_data()

        mock_subscription_service = MagicMock()
        mock_subscription_service.get_node.return_value = {
            "id": "node_1",
            "name": "Node 1",
            "protocol": "trojan",
            "address": "demo.example.com",
            "port": 443,
            "network": "tcp",
            "tls": True,
        }

        with patch("api.services.proxy_service.get_subscription_service", return_value=mock_subscription_service):
            config_path = self.service._regenerate_config()

        self.assertEqual(config_path, str(self.config_file))
        config = json.loads(self.config_file.read_text(encoding="utf-8"))
        self.assertEqual(config["inbounds"][0]["protocol"], "socks")
        self.assertEqual(config["inbounds"][0]["port"], 10022)
        self.assertTrue(config["inbounds"][0]["settings"]["udp"])


if __name__ == "__main__":
    unittest.main()
