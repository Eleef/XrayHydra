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
            "password": "secret",
        }]
        mock_health_service = MagicMock()

        with patch("api.services.proxy_service.get_subscription_service", return_value=mock_subscription_service), \
             patch("api.services.proxy_service.get_health_service", return_value=mock_health_service):
            added = self.service.add_proxies(["node_1"])

        self.assertEqual(len(added), 1)
        mock_health_service.sync_with_proxies.assert_called_once_with([])
        mock_health_service.stop_monitoring.assert_called_once()

    def test_add_proxies_rejects_runtime_unsupported_nodes(self):
        """Unsupported protocol nodes should be blocked before entering proxy pool."""
        mock_subscription_service = MagicMock()
        mock_subscription_service.get_nodes_by_ids.return_value = [{
            "id": "node_ssr_1",
            "name": "SSR Node",
            "protocol": "ssr",
            "address": "ssr.example.com",
            "port": 443,
        }]
        mock_custom_service = MagicMock()
        mock_custom_service.get_nodes_by_ids.return_value = []

        with patch("api.services.proxy_service.get_subscription_service", return_value=mock_subscription_service), \
             patch("api.services.proxy_service.get_custom_group_service", return_value=mock_custom_service):
            with self.assertRaises(ValueError) as exc:
                self.service.add_proxies(["node_ssr_1"])

        self.assertIn("不支持运行", str(exc.exception))
        self.assertIn("ssr", str(exc.exception))

    def test_remove_proxy_while_running_syncs_remaining_ports(self):
        """Removing a live proxy must immediately remove its health state."""
        self._write_proxies([
            {"port": 10000, "node_id": "node_1", "node_name": "Node 1", "protocol": "trojan", "address": "a", "server_port": 443},
            {"port": 10001, "node_id": "node_2", "node_name": "Node 2", "protocol": "trojan", "address": "b", "server_port": 443},
        ])
        self.service._load_data()
        self.service._runner = MagicMock()
        self.service._runner.is_running.return_value = True
        self.config_file.write_text(
            json.dumps(
                {
                    "inbounds": [
                        {"port": 10001, "protocol": "socks"},
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        mock_node = MagicMock()
        mock_node._local_port = 10001

        mock_health_service = MagicMock()
        with patch.object(self.service, "_build_proxy_nodes", return_value=[mock_node]), \
             patch.object(self.service, "_regenerate_config", return_value=str(self.config_file)), \
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

    def test_get_xray_status_reclaims_tracked_process_after_service_restart(self):
        """Status should report running when a project-owned Xray process is still alive after API restart."""
        self.service._runner = None

        mock_runner = MagicMock()
        mock_runner.is_running.return_value = True

        with patch("api.services.proxy_service.XrayRunner", return_value=mock_runner):
            status = self.service.get_xray_status()

        self.assertEqual(status, "running")
        mock_runner.is_running.assert_called_once()

    def test_stop_xray_stops_tracked_process_after_service_restart(self):
        """Stop should terminate the tracked project-owned process even when no in-memory runner exists."""
        self._write_proxies([
            {"port": 10000, "node_id": "node_1", "node_name": "Node 1", "protocol": "trojan", "address": "a", "server_port": 443},
        ])
        self.service._load_data()
        self.service._runner = None

        mock_runner = MagicMock()
        mock_runner.is_running.side_effect = [True, False]
        mock_health_service = MagicMock()

        with patch("api.services.proxy_service.XrayRunner", return_value=mock_runner), \
             patch("api.services.proxy_service.get_health_service", return_value=mock_health_service):
            result = self.service.stop_xray()

        self.assertTrue(result["success"])
        mock_runner.stop.assert_called_once()
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
            "password": "secret",
            "network": "tcp",
            "tls": True,
        }

        with patch("api.services.proxy_service.get_subscription_service", return_value=mock_subscription_service):
            config_path = self.service._regenerate_config()

        self.assertEqual(config_path, str(self.config_file))
        config = json.loads(self.config_file.read_text(encoding="utf-8"))
        self.assertEqual(config["inbounds"][0]["protocol"], "socks")
        self.assertEqual(config["inbounds"][0]["port"], 10022)
        self.assertEqual(config["inbounds"][0]["listen"], "127.0.0.1")
        self.assertTrue(config["inbounds"][0]["settings"]["udp"])

    def test_regenerate_config_uses_configured_proxy_bind_host(self):
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
            "password": "secret",
            "network": "tcp",
            "tls": True,
        }

        with patch.dict("os.environ", {"PROXY_BIND_HOST": "0.0.0.0"}, clear=False), \
             patch("api.services.proxy_service.get_subscription_service", return_value=mock_subscription_service):
            config_path = self.service._regenerate_config()

        self.assertEqual(config_path, str(self.config_file))
        config = json.loads(self.config_file.read_text(encoding="utf-8"))
        self.assertEqual(config["inbounds"][0]["listen"], "0.0.0.0")

    def test_build_proxy_access_fields_uses_configured_access_host(self):
        with patch.dict(
            "os.environ",
            {
                "PROXY_BIND_HOST": "0.0.0.0",
                "PROXY_ACCESS_HOST": "192.168.50.10",
            },
            clear=False,
        ):
            fields = self.service.build_proxy_access_fields(10022)

        self.assertEqual(fields["proxy_address"], "192.168.50.10:10022")
        self.assertEqual(fields["http_proxy_url"], "http://192.168.50.10:10022")
        self.assertEqual(fields["socks5_proxy_url"], "socks5://192.168.50.10:10022")

    def test_get_proxies_by_country_code_filters_exact_match(self):
        self._write_proxies([
            {
                "port": 10000,
                "node_id": "node_1",
                "node_name": "Node 1",
                "protocol": "trojan",
                "address": "a",
                "server_port": 443,
                "exit_ip": "203.0.113.10",
                "exit_country": "United States",
                "exit_country_code": "US",
            },
            {
                "port": 10001,
                "node_id": "node_2",
                "node_name": "Node 2",
                "protocol": "trojan",
                "address": "b",
                "server_port": 443,
                "exit_ip": "203.0.113.20",
                "exit_country": "Japan",
                "exit_country_code": "JP",
            },
        ])
        self.service._load_data()

        us_proxies = self.service.get_proxies_by_country_code("us")
        self.assertEqual([item["port"] for item in us_proxies], [10000])

    def test_sync_health_runtime_state_runs_immediate_probe_after_start(self):
        self._write_proxies([
            {"port": 10022, "node_id": "node_1", "node_name": "Node 1", "protocol": "trojan", "address": "a", "server_port": 443},
            {"port": 10023, "node_id": "node_2", "node_name": "Node 2", "protocol": "trojan", "address": "b", "server_port": 443},
        ])
        self.service._load_data()
        self.service._runner = MagicMock()
        self.service._runner.is_running.return_value = True
        self.config_file.write_text(
            json.dumps(
                {
                    "inbounds": [
                        {"port": 10022, "protocol": "socks"},
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        mock_health_service = MagicMock()
        with patch("api.services.proxy_service.get_health_service", return_value=mock_health_service):
            self.service._sync_health_runtime_state(ensure_monitoring=True)

        mock_health_service.sync_with_proxies.assert_called_once_with([10022])
        mock_health_service.start_monitoring.assert_called_once()
        mock_health_service.run_health_check.assert_called_once_with([10022])

    def test_sync_health_runtime_state_stops_monitoring_when_config_has_no_runtime_ports(self):
        self._write_proxies([
            {"port": 10022, "node_id": "node_1", "node_name": "Node 1", "protocol": "trojan", "address": "a", "server_port": 443},
            {"port": 10023, "node_id": "node_2", "node_name": "Node 2", "protocol": "trojan", "address": "b", "server_port": 443},
        ])
        self.service._load_data()
        self.service._runner = MagicMock()
        self.service._runner.is_running.return_value = True
        self.config_file.write_text(json.dumps({"inbounds": []}, ensure_ascii=False), encoding="utf-8")

        mock_health_service = MagicMock()
        with patch("api.services.proxy_service.get_health_service", return_value=mock_health_service):
            self.service._sync_health_runtime_state(ensure_monitoring=True)

        mock_health_service.sync_with_proxies.assert_called_once_with([])
        mock_health_service.stop_monitoring.assert_called_once()
        mock_health_service.start_monitoring.assert_not_called()
        mock_health_service.run_health_check.assert_not_called()

    def test_get_exit_ip_duplicate_groups_prefers_lowest_latency_success_proxy(self):
        self._write_proxies([
            {"port": 10000, "node_id": "node_1", "node_name": "Node 1", "protocol": "trojan", "address": "a", "server_port": 443, "test_status": "success", "latency_ms": 620, "exit_ip": "203.0.113.10"},
            {"port": 10001, "node_id": "node_2", "node_name": "Node 2", "protocol": "trojan", "address": "b", "server_port": 443, "test_status": "success", "latency_ms": 410, "exit_ip": "203.0.113.10"},
            {"port": 10002, "node_id": "node_3", "node_name": "Node 3", "protocol": "trojan", "address": "c", "server_port": 443, "test_status": "failed", "latency_ms": None, "exit_ip": None},
        ])

        groups = self.service.get_exit_ip_duplicate_groups()

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["exit_ip"], "203.0.113.10")
        self.assertEqual(groups[0]["keep_proxy"]["port"], 10001)
        self.assertEqual([item["port"] for item in groups[0]["remove_proxies"]], [10000])

    def test_dedupe_proxies_by_exit_ip_disables_only_confirmed_ports(self):
        self._write_proxies([
            {"port": 10000, "node_id": "node_1", "node_name": "Node 1", "protocol": "trojan", "address": "a", "server_port": 443, "test_status": "success", "latency_ms": 620, "exit_ip": "203.0.113.10"},
            {"port": 10001, "node_id": "node_2", "node_name": "Node 2", "protocol": "trojan", "address": "b", "server_port": 443, "test_status": "success", "latency_ms": 410, "exit_ip": "203.0.113.10"},
            {"port": 10002, "node_id": "node_3", "node_name": "Node 3", "protocol": "trojan", "address": "c", "server_port": 443, "test_status": "success", "latency_ms": 390, "exit_ip": "198.51.100.8"},
        ])

        mock_health_service = MagicMock()
        with patch("api.services.proxy_service.get_health_service", return_value=mock_health_service):
            result = self.service.dedupe_proxies_by_exit_ip([10000])

        self.assertEqual(result["disabled_count"], 1)
        self.assertEqual(result["disabled_ports"], [10000])
        self.assertEqual(result["kept_ports"], [10001])
        self.assertEqual([item["port"] for item in self.service.get_all_proxies()], [10000, 10001, 10002])
        self.assertEqual([item["port"] for item in self.service.get_all_proxies(include_disabled=False)], [10001, 10002])
        disabled_proxy = next(item for item in self.service.get_all_proxies() if item["port"] == 10000)
        self.assertEqual(disabled_proxy["pool_status"], "dedupe_disabled")
        self.assertEqual(disabled_proxy["disabled_reason"], "exit_ip_duplicate")


if __name__ == "__main__":
    unittest.main()
