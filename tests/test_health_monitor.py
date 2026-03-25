"""
Unit tests for HealthMonitor recovery probing.
"""
import unittest
from unittest.mock import patch

from src.xray_prism.health_monitor import HealthMonitor
from src.xray_prism.models import HealthStatus


class TestHealthMonitor(unittest.TestCase):
    def test_handle_probe_failure_disables_only_after_three_failures(self):
        monitor = HealthMonitor(timeout=1, max_workers=1)
        port = 10000

        monitor.handle_probe_failure(port, "timeout", "probe_failed")
        state = monitor.get_state(port)
        self.assertIsNotNone(state)
        self.assertEqual(state.failure_count, 1)
        self.assertNotEqual(state.status, HealthStatus.DISABLED)

        monitor.handle_probe_failure(port, "timeout", "probe_failed")
        state = monitor.get_state(port)
        self.assertIsNotNone(state)
        self.assertEqual(state.failure_count, 2)
        self.assertNotEqual(state.status, HealthStatus.DISABLED)

        monitor.handle_probe_failure(port, "timeout", "probe_failed")
        state = monitor.get_state(port)
        self.assertIsNotNone(state)
        self.assertEqual(state.failure_count, 3)
        self.assertEqual(state.status, HealthStatus.DISABLED)
        self.assertIsNotNone(state.penalty_until)
        self.assertEqual(state.last_error_category, "probe_failed")

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
             patch.object(monitor, "probe_proxy", return_value=(True, 123.4, None)) as probe_proxy:
            states = monitor.run_health_check([10000, 10001])

        self.assertEqual(probe_proxy.call_count, 2)
        self.assertEqual(states[10000].status, HealthStatus.DEGRADED)
        self.assertEqual(states[10001].status, HealthStatus.DEGRADED)


if __name__ == "__main__":
    unittest.main()
