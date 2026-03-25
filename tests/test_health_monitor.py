"""
Unit tests for HealthMonitor recovery probing.
"""
import unittest
from unittest.mock import patch

from src.xray_prism.health_monitor import HealthMonitor
from src.xray_prism.models import HealthStatus


class TestHealthMonitor(unittest.TestCase):
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
