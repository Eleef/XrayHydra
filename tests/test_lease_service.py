"""
Unit tests for Lease Service.
Tests workspace isolation, TTL expiration, cooldown behavior, and workspace summaries.
"""
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.services.lease_service import GLOBAL_WORKSPACE_ID, CooldownRecord, LeaseManager, LeaseRecord, UsageRecord


class TestLeaseManager(unittest.TestCase):
    """Test cases for LeaseManager."""

    def setUp(self):
        self.manager = LeaseManager()
        self.mock_healthy_ports = [10001, 10002, 10003]

    def _mock_healthy_ports(self):
        return patch.object(
            self.manager,
            "_get_healthy_ports",
            return_value=self.mock_healthy_ports,
        )

    def test_acquire_success(self):
        with self._mock_healthy_ports():
            result = self.manager.acquire("workspace_a", ttl=60)

        self.assertTrue(result.success)
        self.assertIsNotNone(result.lease_id)
        self.assertIn(result.proxy_port, self.mock_healthy_ports)
        self.assertIsNotNone(result.expires_at)
        self.assertEqual(result.metrics["usage_count"], 1)
        self.assertEqual(result.metrics["success_count"], 0)
        self.assertEqual(result.metrics["failure_count"], 0)

    def test_acquire_by_exit_ip_success(self):
        proxy_service = MagicMock()
        proxy_service.get_proxies_by_exit_ip.return_value = [
            {"port": 10001, "exit_ip": "203.0.113.10"},
            {"port": 10002, "exit_ip": "203.0.113.10"},
        ]

        with patch("api.services.lease_service.ProxyService", return_value=proxy_service), \
             patch.object(self.manager, "_get_healthy_ports", return_value=[10001, 10002]):
            result = self.manager.acquire_by_exit_ip("workspace_a", "203.0.113.10", ttl=60)

        self.assertTrue(result.success)
        self.assertIn(result.proxy_port, [10001, 10002])
        self.assertEqual(result.metrics["usage_count"], 1)

    def test_classify_ports_for_workspace(self):
        self.manager._active_leases["workspace_b:10002"] = LeaseRecord(
            lease_id="lease-2",
            workspace_id="workspace_b",
            proxy_port=10002,
            acquired_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=5),
        )
        self.manager._cooldowns["workspace_a:10003"] = CooldownRecord(
            workspace_id="workspace_a",
            proxy_port=10003,
            until=datetime.now() + timedelta(minutes=5),
            set_at=datetime.now(),
            source="timed",
        )

        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001, 10002, 10003]):
            classified = self.manager.classify_ports_for_workspace("workspace_a", [10001, 10002, 10003])

        self.assertEqual(classified["available"], {10001})
        self.assertEqual(classified["occupied"], {10002})
        self.assertEqual(classified["unavailable"], {10003})

    def test_acquire_by_exit_ip_not_found(self):
        proxy_service = MagicMock()
        proxy_service.get_proxies_by_exit_ip.return_value = []

        with patch("api.services.lease_service.ProxyService", return_value=proxy_service):
            result = self.manager.acquire_by_exit_ip("workspace_a", "203.0.113.10", ttl=60)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "exit_ip_not_found")

    def test_acquire_by_exit_ip_returns_occupied_when_all_matches_actively_leased(self):
        proxy_service = MagicMock()
        proxy_service.get_proxies_by_exit_ip.return_value = [
            {"port": 10001, "exit_ip": "203.0.113.10"},
        ]
        self.manager._active_leases["workspace_a:10001"] = LeaseRecord(
            lease_id="lease-1",
            workspace_id="workspace_a",
            proxy_port=10001,
            acquired_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=5),
        )

        with patch("api.services.lease_service.ProxyService", return_value=proxy_service), \
             patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            result = self.manager.acquire_by_exit_ip("workspace_b", "203.0.113.10", ttl=60)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "exit_ip_occupied")

    def test_acquire_by_exit_ip_returns_unavailable_when_matches_exist_but_not_allocatable(self):
        proxy_service = MagicMock()
        proxy_service.get_proxies_by_exit_ip.return_value = [
            {"port": 10001, "exit_ip": "203.0.113.10"},
        ]

        with patch("api.services.lease_service.ProxyService", return_value=proxy_service), \
             patch.object(self.manager, "_get_healthy_ports", return_value=[]):
            result = self.manager.acquire_by_exit_ip("workspace_a", "203.0.113.10", ttl=60)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "exit_ip_unavailable")

    def test_acquire_by_exit_ip_uses_existing_selection_rule_for_duplicate_matches(self):
        proxy_service = MagicMock()
        proxy_service.get_proxies_by_exit_ip.return_value = [
            {"port": 10002, "exit_ip": "203.0.113.10"},
            {"port": 10001, "exit_ip": "203.0.113.10"},
        ]

        with patch("api.services.lease_service.ProxyService", return_value=proxy_service), \
             patch.object(self.manager, "_get_healthy_ports", return_value=[10001, 10002]), \
             patch("api.services.lease_service.random.choice", return_value=10002):
            result = self.manager.acquire_by_exit_ip(
                "workspace_a",
                "203.0.113.10",
                ttl=60,
                initial_port_ordering="random",
            )

        self.assertTrue(result.success)
        self.assertEqual(result.proxy_port, 10002)

    def test_acquire_no_available_proxy(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[]):
            result = self.manager.acquire("workspace_a", ttl=60)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "no_available_proxy")

    def test_acquire_no_available_proxy_reports_all_disabled_message(self):
        mock_health_service = MagicMock()
        mock_health_service.get_all_health_states.return_value = [
            {"proxy_port": 10001, "status": "disabled"},
            {"proxy_port": 10002, "status": "disabled"},
        ]

        with patch.object(self.manager, "_get_healthy_ports", return_value=[]), \
             patch("api.services.lease_service.get_health_service", return_value=mock_health_service):
            result = self.manager.acquire("workspace_a", ttl=60)

        self.assertFalse(result.success)
        self.assertEqual(result.message, "当前没有可分配代理：所有代理均处于健康禁用状态")

    def test_workspace_isolation(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            result_a = self.manager.acquire("workspace_a", ttl=60)
            result_b = self.manager.acquire("workspace_b", ttl=60)

        self.assertTrue(result_a.success)
        self.assertTrue(result_b.success)
        self.assertEqual(result_a.proxy_port, result_b.proxy_port)

    def test_same_workspace_different_ports(self):
        with self._mock_healthy_ports():
            result1 = self.manager.acquire("workspace_a", ttl=60)
            result2 = self.manager.acquire("workspace_a", ttl=60)
            result3 = self.manager.acquire("workspace_a", ttl=60)

        ports = {result1.proxy_port, result2.proxy_port, result3.proxy_port}
        self.assertEqual(len(ports), 3)

    def test_exhaust_all_proxies(self):
        with self._mock_healthy_ports():
            self.manager.acquire("workspace_a", ttl=60)
            self.manager.acquire("workspace_a", ttl=60)
            self.manager.acquire("workspace_a", ttl=60)
            result = self.manager.acquire("workspace_a", ttl=60)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "no_available_proxy")

    def test_release_success(self):
        with self._mock_healthy_ports():
            result = self.manager.acquire("workspace_a", ttl=60)
            port = result.proxy_port
            success, cooldown_until = self.manager.release(
                "workspace_a",
                f"127.0.0.1:{port}",
                cooldown_seconds=0,
            )

        self.assertTrue(success)
        self.assertIsNone(cooldown_until)

    def test_release_with_cooldown(self):
        with self._mock_healthy_ports():
            result = self.manager.acquire("workspace_a", ttl=60)
            port = result.proxy_port
            success, cooldown_until = self.manager.release(
                "workspace_a",
                f"127.0.0.1:{port}",
                cooldown_seconds=300,
            )

        self.assertTrue(success)
        self.assertIsNotNone(cooldown_until)
        expected_cooldown = datetime.now() + timedelta(seconds=300)
        delta = abs((cooldown_until - expected_cooldown).total_seconds())
        self.assertLess(delta, 2)

        key = f"workspace_a:{port}"
        self.assertEqual(self.manager._cooldowns[key].source, "timed")

    def test_release_invalid_proxy_address(self):
        success, cooldown_until = self.manager.release(
            "workspace_a",
            "invalid-address",
            cooldown_seconds=300,
        )
        self.assertFalse(success)
        self.assertIsNone(cooldown_until)

    def test_idempotent_release(self):
        with self._mock_healthy_ports():
            success1, _ = self.manager.release("workspace_a", "127.0.0.1:10001", cooldown_seconds=0)
            success2, _ = self.manager.release("workspace_a", "127.0.0.1:10001", cooldown_seconds=0)

        self.assertTrue(success1)
        self.assertTrue(success2)

    def test_release_with_success_result_increments_success_count_once(self):
        with self._mock_healthy_ports():
            lease = self.manager.acquire("workspace_a", ttl=60)
            port = lease.proxy_port
            success1, _ = self.manager.release(
                "workspace_a",
                f"127.0.0.1:{port}",
                cooldown_seconds=0,
                result="success",
            )
            success2, _ = self.manager.release(
                "workspace_a",
                f"127.0.0.1:{port}",
                cooldown_seconds=0,
                result="success",
            )

        self.assertTrue(success1)
        self.assertTrue(success2)
        metrics = self.manager._usage_stats["workspace_a"][port]
        self.assertEqual(metrics.usage_count, 1)
        self.assertEqual(metrics.success_count, 1)
        self.assertEqual(metrics.failure_count, 0)

    def test_release_without_result_does_not_increment_outcome_counts(self):
        with self._mock_healthy_ports():
            lease = self.manager.acquire("workspace_a", ttl=60)
            port = lease.proxy_port
            success, _ = self.manager.release(
                "workspace_a",
                f"127.0.0.1:{port}",
                cooldown_seconds=0,
            )

        self.assertTrue(success)
        metrics = self.manager._usage_stats["workspace_a"][port]
        self.assertEqual(metrics.usage_count, 1)
        self.assertEqual(metrics.success_count, 0)
        self.assertEqual(metrics.failure_count, 0)

    def test_cooldown_blocks_same_workspace_only(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            result_a = self.manager.acquire("workspace_a", ttl=60)
            port = result_a.proxy_port
            self.manager.release("workspace_a", f"127.0.0.1:{port}", cooldown_seconds=300)

            result_a2 = self.manager.acquire("workspace_a", ttl=60)
            self.assertFalse(result_a2.success)

            result_b = self.manager.acquire("workspace_b", ttl=60)

        self.assertTrue(result_b.success)
        self.assertEqual(result_b.proxy_port, port)

    def test_manual_cooldown_blocks_same_workspace_only(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            success, error = self.manager.set_manual_cooldown("workspace_a", 10001)
            self.assertTrue(success)
            self.assertIsNone(error)

            result_a = self.manager.acquire("workspace_a", ttl=60)
            self.assertFalse(result_a.success)

            result_b = self.manager.acquire("workspace_b", ttl=60)

        self.assertTrue(result_b.success)
        self.assertEqual(result_b.proxy_port, 10001)

    def test_manual_cooldown_can_be_recalled(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            self.manager.set_manual_cooldown("workspace_a", 10001)
            success, source = self.manager.recall_cooldown("workspace_a", 10001)
            self.assertTrue(success)
            self.assertEqual(source, "manual")

            result = self.manager.acquire("workspace_a", ttl=60)

        self.assertTrue(result.success)
        self.assertEqual(result.proxy_port, 10001)

    def test_manual_cooldown_with_failure_result_increments_failure_count(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            success, error = self.manager.set_manual_cooldown("workspace_a", 10001, result="failure")

        self.assertTrue(success)
        self.assertIsNone(error)
        metrics = self.manager._usage_stats["workspace_a"][10001]
        self.assertEqual(metrics.usage_count, 0)
        self.assertEqual(metrics.success_count, 0)
        self.assertEqual(metrics.failure_count, 1)

    def test_manual_cooldown_does_not_expire_automatically(self):
        key = "workspace_a:10001"
        self.manager._cooldowns[key] = CooldownRecord(
            workspace_id="workspace_a",
            proxy_port=10001,
            until=None,
            set_at=datetime.now() - timedelta(days=2),
            source="manual",
        )

        removed = self.manager._cleanup_expired_cooldowns()
        self.assertEqual(removed, 0)
        self.assertIn(key, self.manager._cooldowns)

    def test_manual_cooldown_rejects_active_lease(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            self.manager.acquire("workspace_a", ttl=60)
            success, error = self.manager.set_manual_cooldown("workspace_a", 10001)

        self.assertFalse(success)
        self.assertIn("active lease", error)

    def test_timed_cooldown_batch_skips_active_lease(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001, 10002]):
            self.manager.acquire("workspace_a", ttl=60, initial_port_ordering="port_asc")
            result = self.manager.set_timed_cooldowns("workspace_a", [10001, 10002], 300)

        self.assertEqual(result["applied_ports"], [10002])
        self.assertEqual(result["skipped_ports"], [10001])
        self.assertEqual(self.manager._cooldowns["workspace_a:10002"].source, "timed")

    def test_timed_cooldown_batch_with_failure_result_counts_only_applied_ports(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001, 10002]):
            self.manager.acquire("workspace_a", ttl=60, initial_port_ordering="port_asc")
            result = self.manager.set_timed_cooldowns("workspace_a", [10001, 10002], 300, result="failure")

        self.assertEqual(result["applied_ports"], [10002])
        self.assertEqual(result["skipped_ports"], [10001])
        self.assertEqual(self.manager._usage_stats["workspace_a"][10001].failure_count, 0)
        self.assertEqual(self.manager._usage_stats["workspace_a"][10002].failure_count, 1)

    def test_global_timed_cooldown_blocks_acquire_for_all_workspaces(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            success, error = self.manager.set_timed_cooldown(GLOBAL_WORKSPACE_ID, 10001, 300)
            result_a = self.manager.acquire("workspace_a", ttl=60)
            result_b = self.manager.acquire("workspace_b", ttl=60)

        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertFalse(result_a.success)
        self.assertFalse(result_b.success)

    def test_global_manual_cooldown_rejects_port_with_any_active_lease(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            self.manager.acquire("workspace_a", ttl=60)
            success, error = self.manager.set_manual_cooldown(GLOBAL_WORKSPACE_ID, 10001)

        self.assertFalse(success)
        self.assertIn("active lease", error)

    def test_recall_global_cooldown_restores_port_for_all_workspaces(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001]):
            self.manager.set_manual_cooldown(GLOBAL_WORKSPACE_ID, 10001)
            success, source = self.manager.recall_cooldown(GLOBAL_WORKSPACE_ID, 10001)
            result_a = self.manager.acquire("workspace_a", ttl=60)
            result_b = self.manager.acquire("workspace_b", ttl=60)

        self.assertTrue(success)
        self.assertEqual(source, "manual")
        self.assertTrue(result_a.success)
        self.assertTrue(result_b.success)
        self.assertEqual(result_a.proxy_port, 10001)
        self.assertEqual(result_b.proxy_port, 10001)

    def test_lru_selection(self):
        manager = LeaseManager()
        now = datetime.now()
        manager._usage_stats["workspace_x"] = {
            10001: UsageRecord(last_used_at=now - timedelta(hours=2), usage_count=2),
            10002: UsageRecord(last_used_at=now - timedelta(hours=1), usage_count=1),
            10003: UsageRecord(last_used_at=now, usage_count=1),
        }

        with patch.object(manager, "_get_healthy_ports", return_value=[10001, 10002, 10003]):
            result = manager.acquire("workspace_x", ttl=60)

        self.assertEqual(result.proxy_port, 10001)

    def test_first_acquire_defaults_to_random_tie_break_for_never_used_ports(self):
        manager = LeaseManager()
        with patch.object(manager, "_get_healthy_ports", return_value=[10001, 10002, 10003]), \
             patch("api.services.lease_service.random.choice", return_value=10003) as mock_choice:
            result = manager.acquire("workspace_x", ttl=60)

        self.assertEqual(result.proxy_port, 10003)
        mock_choice.assert_called_once_with([10001, 10002, 10003])

    def test_first_acquire_can_use_port_ascending_tie_break(self):
        manager = LeaseManager()
        with patch.object(manager, "_get_healthy_ports", return_value=[10003, 10001, 10002]), \
             patch("api.services.lease_service.random.choice") as mock_choice:
            result = manager.acquire("workspace_x", ttl=60, initial_port_ordering="port_asc")

        self.assertEqual(result.proxy_port, 10001)
        mock_choice.assert_not_called()

    def test_ttl_expiration(self):
        key = "workspace_a:10001"
        self.manager._active_leases[key] = LeaseRecord(
            lease_id="test-id",
            workspace_id="workspace_a",
            proxy_port=10001,
            acquired_at=datetime.now() - timedelta(seconds=120),
            expires_at=datetime.now() - timedelta(seconds=60),
        )

        with self._mock_healthy_ports():
            result = self.manager.acquire("workspace_a", ttl=60)

        self.assertTrue(result.success)
        self.assertIn(result.proxy_port, self.mock_healthy_ports)

    def test_get_status_includes_workspace_summaries_and_cooldown_source(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001, 10002]):
            lease = self.manager.acquire("workspace_a", ttl=60)
            self.manager.release("workspace_a", f"127.0.0.1:{lease.proxy_port}", cooldown_seconds=300)
            self.manager.set_manual_cooldown("workspace_b", 10002)

        status = self.manager.get_status()

        self.assertEqual(status["total_active"], 0)
        self.assertEqual(status["total_cooldowns"], 2)
        self.assertEqual({cd["source"] for cd in status["cooldowns"]}, {"timed", "manual"})

        summaries = {item["workspace_id"]: item for item in status["workspaces"]}
        self.assertEqual(summaries["workspace_a"]["cooldown_count"], 1)
        self.assertEqual(summaries["workspace_b"]["cooldown_count"], 1)
        self.assertIn("metrics", status["cooldowns"][0])
        self.assertIn("usage_count", status["cooldowns"][0]["metrics"])

    def test_get_status_filtered_workspace_keeps_workspace_summary_list(self):
        with self._mock_healthy_ports():
            self.manager.acquire("workspace_a", ttl=60)
            self.manager.acquire("workspace_b", ttl=60)

        status = self.manager.get_status(workspace_id="workspace_a")
        self.assertEqual(status["total_active"], 1)
        self.assertEqual({item["workspace_id"] for item in status["workspaces"]}, {"workspace_a", "workspace_b"})

    def test_get_status_filtered_workspace_includes_global_cooldowns_but_not_global_summary(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001, 10002]):
            self.manager.set_manual_cooldown(GLOBAL_WORKSPACE_ID, 10001)
            self.manager.set_manual_cooldown("workspace_a", 10002)

        status = self.manager.get_status(workspace_id="workspace_a")

        self.assertEqual(status["total_cooldowns"], 2)
        self.assertEqual(
            {(item["workspace_id"], item["proxy_port"]) for item in status["cooldowns"]},
            {(GLOBAL_WORKSPACE_ID, 10001), ("workspace_a", 10002)},
        )
        self.assertEqual({item["workspace_id"] for item in status["workspaces"]}, {"workspace_a"})

    def test_reset_workspace_clears_only_target_workspace_state(self):
        with patch.object(self.manager, "_get_healthy_ports", return_value=[10001, 10002]):
            lease = self.manager.acquire("workspace_a", ttl=60)
            self.manager.release("workspace_a", f"127.0.0.1:{lease.proxy_port}", cooldown_seconds=300)
            other_lease = self.manager.acquire("workspace_b", ttl=60)
            self.manager.release("workspace_b", f"127.0.0.1:{other_lease.proxy_port}", cooldown_seconds=120)

        result = self.manager.reset_workspace("workspace_a")
        status = self.manager.get_status()

        self.assertEqual(result["workspace_id"], "workspace_a")
        self.assertEqual(result["released_count"], 0)
        self.assertEqual(result["recalled_count"], 1)
        self.assertEqual({item["workspace_id"] for item in status["workspaces"]}, {"workspace_b"})
        self.assertEqual(status["total_active"], 0)
        self.assertEqual(status["total_cooldowns"], 1)

    def test_reset_workspace_optionally_clears_only_target_metrics(self):
        with self._mock_healthy_ports():
            lease_a = self.manager.acquire("workspace_a", ttl=60)
            self.manager.release("workspace_a", f"127.0.0.1:{lease_a.proxy_port}", result="success")
            lease_b = self.manager.acquire("workspace_b", ttl=60)
            self.manager.release("workspace_b", f"127.0.0.1:{lease_b.proxy_port}", result="failure")

        result = self.manager.reset_workspace("workspace_a", clear_metrics=True)

        self.assertEqual(result["cleared_metric_entries"], 1)
        self.assertNotIn("workspace_a", self.manager._usage_stats)
        self.assertIn("workspace_b", self.manager._usage_stats)

    def test_get_stats(self):
        with self._mock_healthy_ports():
            lease_a = self.manager.acquire("workspace_a", ttl=60)
            self.manager.release("workspace_a", f"127.0.0.1:{lease_a.proxy_port}", result="success")
            self.manager.acquire("workspace_b", ttl=60)

        stats = self.manager.get_stats()
        self.assertEqual(stats["total_active_leases"], 1)
        self.assertIn("workspace_a", stats["workspaces"])
        self.assertIn("workspace_b", stats["workspaces"])
        self.assertTrue(all("success_count" in item for item in stats["proxies_by_usage"]))
        self.assertTrue(any(item["workspace_id"] == "workspace_a" for item in stats["proxies_by_usage"]))
        self.assertGreaterEqual(len(stats["proxies_by_usage"]), 2)

    def test_metrics_persist_round_trip_with_lazy_flush_store(self):
        with TemporaryDirectory() as tmp_dir:
            metrics_path = Path(tmp_dir) / "lease_metrics.json"
            manager = LeaseManager(metrics_path=metrics_path, flush_delay_seconds=5, max_flush_interval_seconds=5)
            with patch.object(manager, "_get_healthy_ports", return_value=[10001]):
                lease = manager.acquire("workspace_a", ttl=60)
                manager.release("workspace_a", f"127.0.0.1:{lease.proxy_port}", result="success")
                manager.set_manual_cooldown("workspace_b", 10001, result="failure")

            manager.flush_metrics()
            restored = LeaseManager(metrics_path=metrics_path, flush_delay_seconds=5, max_flush_interval_seconds=5)

        self.assertEqual(restored._usage_stats["workspace_a"][10001].usage_count, 1)
        self.assertEqual(restored._usage_stats["workspace_a"][10001].success_count, 1)
        self.assertEqual(restored._usage_stats["workspace_b"][10001].failure_count, 1)


class TestLeaseRecord(unittest.TestCase):
    def test_is_expired_false(self):
        record = LeaseRecord(
            lease_id="test",
            workspace_id="ws",
            proxy_port=10001,
            acquired_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
        )
        self.assertFalse(record.is_expired())

    def test_is_expired_true(self):
        record = LeaseRecord(
            lease_id="test",
            workspace_id="ws",
            proxy_port=10001,
            acquired_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1),
        )
        self.assertTrue(record.is_expired())


class TestCooldownRecord(unittest.TestCase):
    def test_is_expired_false(self):
        record = CooldownRecord(
            workspace_id="ws",
            proxy_port=10001,
            until=datetime.now() + timedelta(hours=1),
            set_at=datetime.now(),
            source="timed",
        )
        self.assertFalse(record.is_expired())

    def test_is_expired_true(self):
        record = CooldownRecord(
            workspace_id="ws",
            proxy_port=10001,
            until=datetime.now() - timedelta(hours=1),
            set_at=datetime.now() - timedelta(hours=2),
            source="timed",
        )
        self.assertTrue(record.is_expired())

    def test_manual_cooldown_without_until_never_expires(self):
        record = CooldownRecord(
            workspace_id="ws",
            proxy_port=10001,
            until=None,
            set_at=datetime.now() - timedelta(days=1),
            source="manual",
        )
        self.assertFalse(record.is_expired())


if __name__ == "__main__":
    unittest.main()
