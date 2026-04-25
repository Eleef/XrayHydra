"""
Unit tests for HealthMonitor recovery probing.
"""
import unittest
from unittest.mock import patch

from src.xray_prism.health_monitor import HealthMonitor
from src.xray_prism.models import HealthStatus
from src.xray_prism.proxy_runtime import get_proxy_probe_scheme
from src.xray_prism.tester import MIN_CONNECTIVITY_SUCCESSES


class TestHealthMonitor(unittest.TestCase):
    def test_handle_probe_failure_disables_only_after_three_failures(self):
        monitor = HealthMonitor(timeout=1, max_workers=1)
        port = 10000

        monitor.handle_probe_failure(port, "timeout", "connectivity_failed")
        state = monitor.get_state(port)
        self.assertIsNotNone(state)
        self.assertEqual(state.failure_count, 1)
        self.assertNotEqual(state.status, HealthStatus.DISABLED)

        monitor.handle_probe_failure(port, "timeout", "connectivity_failed")
        state = monitor.get_state(port)
        self.assertIsNotNone(state)
        self.assertEqual(state.failure_count, 2)
        self.assertNotEqual(state.status, HealthStatus.DISABLED)

        monitor.handle_probe_failure(port, "timeout", "connectivity_failed")
        state = monitor.get_state(port)
        self.assertIsNotNone(state)
        self.assertEqual(state.failure_count, 3)
        self.assertEqual(state.status, HealthStatus.DISABLED)
        self.assertIsNotNone(state.penalty_until)
        self.assertEqual(state.last_error_category, "connectivity_failed")

    def test_handle_probe_success_resets_failure_count_and_error_context(self):
        monitor = HealthMonitor(timeout=1, max_workers=1)
        port = 10001

        monitor.handle_probe_failure(port, "connection refused", "runtime_unavailable")
        monitor.handle_probe_failure(port, "connection refused", "runtime_unavailable")
        state = monitor.get_state(port)
        self.assertIsNotNone(state)
        self.assertEqual(state.failure_count, 2)
        self.assertEqual(state.last_error_category, "runtime_unavailable")

        monitor.handle_probe_success(port, 120.5)
        state = monitor.get_state(port)
        self.assertIsNotNone(state)
        self.assertEqual(state.failure_count, 0)
        self.assertNotEqual(state.status, HealthStatus.DISABLED)
        self.assertIsNone(state.last_error_category)
        self.assertIsNone(state.last_error_message)

    def test_successful_probe_preserves_summary_and_network_advisory(self):
        monitor = HealthMonitor(timeout=1, max_workers=1)
        monitor.get_or_create_state(10003)

        with patch.object(monitor, "check_network_connectivity", return_value=False), \
             patch.object(
                 monitor,
                 "probe_proxy",
                 return_value=(
                     True,
                     88.0,
                     None,
                     None,
                     "connectivity 2/3; exit-info 0/0",
                     "https://www.gstatic.com/generate_204",
                 ),
             ):
            states = monitor.run_health_check([10003])

        state = states[10003]
        self.assertEqual(state.last_probe_summary, "connectivity 2/3; exit-info 0/0")
        self.assertEqual(state.last_successful_target, "https://www.gstatic.com/generate_204")
        self.assertEqual(state.last_error_category, "network_advisory")
        self.assertIn("直连网络检测异常", state.last_error_message)

    def test_exported_state_includes_error_diagnostics(self):
        monitor = HealthMonitor(timeout=1, max_workers=1)
        port = 10002
        monitor.handle_probe_failure(port, "proxy handshake failed", "runtime_unavailable")

        state_dict = monitor.export_states()[0]
        self.assertIn("last_error_category", state_dict)
        self.assertIn("last_error_message", state_dict)
        self.assertEqual(state_dict["last_error_category"], "runtime_unavailable")
        self.assertIn("proxy handshake failed", state_dict["last_error_message"])

    def test_run_health_check_reprobes_when_all_states_disabled(self):
        monitor = HealthMonitor(timeout=1, max_workers=1)
        for port in (10000, 10001):
            state = monitor.get_or_create_state(port)
            state.status = HealthStatus.DISABLED

        with patch.object(monitor, "check_network_connectivity", return_value=True), \
             patch.object(monitor, "probe_proxy", return_value=(True, 123.4, None, None, "connectivity 2/3; exit-info 0/0", "https://www.gstatic.com/generate_204")) as probe_proxy:
            states = monitor.run_health_check([10000, 10001])

        self.assertEqual(probe_proxy.call_count, 2)
        self.assertEqual(states[10000].status, HealthStatus.DEGRADED)
        self.assertEqual(states[10001].status, HealthStatus.DEGRADED)

    def test_probe_proxy_uses_runtime_probe_scheme_by_default(self):
        monitor = HealthMonitor(timeout=1, max_workers=1)
        captured = {}

        def fake_test_port(port, node_name, proxy_type=None):
            captured["proxy_type"] = proxy_type
            from types import SimpleNamespace
            return SimpleNamespace(
                success=True,
                latency_ms=120.0,
                error=None,
                connectivity_status="success",
                successful_target_count=MIN_CONNECTIVITY_SUCCESSES,
                tested_targets=[
                    "https://www.gstatic.com/generate_204",
                    "https://www.google.com/generate_204",
                    "http://cp.cloudflare.com/",
                ],
                successful_target="https://www.gstatic.com/generate_204",
                last_probe_summary="connectivity 2/3; exit-info 0/0",
            )

        with patch.object(monitor, "_is_local_proxy_available", return_value=True), \
             patch("src.xray_prism.health_monitor.ProxyTester") as tester_cls:
            tester_cls.return_value.test_port.side_effect = fake_test_port
            success, latency, error, category, summary, target = monitor.probe_proxy(10000)

        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNone(category)
        self.assertEqual(summary, "connectivity 2/3; exit-info 0/0")
        self.assertEqual(target, "https://www.gstatic.com/generate_204")
        self.assertEqual(captured["proxy_type"], get_proxy_probe_scheme())


if __name__ == "__main__":
    unittest.main()
