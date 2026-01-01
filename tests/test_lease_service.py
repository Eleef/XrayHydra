"""
Unit tests for Lease Service.
Tests workspace isolation, TTL expiration, cooldown, and LRU selection.
"""
import sys
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.services.lease_service import LeaseManager, LeaseRecord, CooldownRecord


class TestLeaseManager(unittest.TestCase):
    """Test cases for LeaseManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = LeaseManager()
        # Mock healthy ports
        self.mock_healthy_ports = [10001, 10002, 10003]
    
    def _mock_healthy_ports(self):
        """Mock the _get_healthy_ports method."""
        return patch.object(
            self.manager, 
            '_get_healthy_ports', 
            return_value=self.mock_healthy_ports
        )
    
    def test_acquire_success(self):
        """Test successful lease acquisition."""
        with self._mock_healthy_ports():
            result = self.manager.acquire("workspace_a", ttl=60)
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.lease_id)
        self.assertIn(result.proxy_port, self.mock_healthy_ports)
        self.assertIsNotNone(result.expires_at)
    
    def test_acquire_no_available_proxy(self):
        """Test acquisition when no proxies available."""
        with patch.object(self.manager, '_get_healthy_ports', return_value=[]):
            result = self.manager.acquire("workspace_a", ttl=60)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "no_available_proxy")
    
    def test_workspace_isolation(self):
        """Test that different workspaces can hold leases for same proxy simultaneously."""
        # Use only one port to force testing isolation
        with patch.object(self.manager, '_get_healthy_ports', return_value=[10001]):
            # Workspace A acquires the only proxy
            result_a = self.manager.acquire("workspace_a", ttl=60)
            
            # Workspace B should ALSO be able to get the same proxy
            # (same port can be leased to multiple workspaces)
            result_b = self.manager.acquire("workspace_b", ttl=60)
        
        self.assertTrue(result_a.success)
        self.assertTrue(result_b.success)
        # Both workspaces can use the same port (isolation means they don't block each other)
        self.assertEqual(result_a.proxy_port, result_b.proxy_port)
    
    def test_same_workspace_different_ports(self):
        """Test that same workspace gets different ports for multiple leases."""
        with self._mock_healthy_ports():
            result1 = self.manager.acquire("workspace_a", ttl=60)
            result2 = self.manager.acquire("workspace_a", ttl=60)
            result3 = self.manager.acquire("workspace_a", ttl=60)
        
        ports = {result1.proxy_port, result2.proxy_port, result3.proxy_port}
        self.assertEqual(len(ports), 3)  # All unique
    
    def test_exhaust_all_proxies(self):
        """Test error when workspace exhausts all proxies."""
        with self._mock_healthy_ports():
            # Acquire all 3 ports
            self.manager.acquire("workspace_a", ttl=60)
            self.manager.acquire("workspace_a", ttl=60)
            self.manager.acquire("workspace_a", ttl=60)
            
            # 4th should fail
            result = self.manager.acquire("workspace_a", ttl=60)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error, "no_available_proxy")
    
    def test_release_success(self):
        """Test successful lease release."""
        with self._mock_healthy_ports():
            result = self.manager.acquire("workspace_a", ttl=60)
            port = result.proxy_port
            
            success, cooldown_until = self.manager.release(
                "workspace_a", 
                f"127.0.0.1:{port}",
                cooldown_seconds=0
            )
        
        self.assertTrue(success)
        self.assertIsNone(cooldown_until)
    
    def test_release_with_cooldown(self):
        """Test release with cooldown period."""
        with self._mock_healthy_ports():
            result = self.manager.acquire("workspace_a", ttl=60)
            port = result.proxy_port
            
            success, cooldown_until = self.manager.release(
                "workspace_a",
                f"127.0.0.1:{port}",
                cooldown_seconds=300
            )
        
        self.assertTrue(success)
        self.assertIsNotNone(cooldown_until)
        # Cooldown should be approximately 5 minutes from now
        expected_cooldown = datetime.now() + timedelta(seconds=300)
        delta = abs((cooldown_until - expected_cooldown).total_seconds())
        self.assertLess(delta, 2)  # Within 2 seconds
    
    def test_release_idempotent(self):
        """Test that release is idempotent."""
        with self._mock_healthy_ports():
            result = self.manager.acquire("workspace_a", ttl=60)
            port = result.proxy_port
            
            # Release twice
            success1, _ = self.manager.release("workspace_a", f"127.0.0.1:{port}")
            success2, _ = self.manager.release("workspace_a", f"127.0.0.1:{port}")
        
        self.assertTrue(success1)
        self.assertTrue(success2)  # Second release also succeeds
    
    def test_cooldown_blocks_acquisition(self):
        """Test that cooldown blocks acquisition for same workspace."""
        with self._mock_healthy_ports():
            # Acquire and release with cooldown
            result1 = self.manager.acquire("workspace_a", ttl=60)
            port = result1.proxy_port
            self.manager.release("workspace_a", f"127.0.0.1:{port}", cooldown_seconds=300)
            
            # Try to acquire again - should get different port
            result2 = self.manager.acquire("workspace_a", ttl=60)
        
        self.assertTrue(result2.success)
        self.assertNotEqual(result1.proxy_port, result2.proxy_port)
    
    def test_cooldown_does_not_affect_other_workspace(self):
        """Test that cooldown only affects own workspace."""
        # Use only one port to force testing isolation
        with patch.object(self.manager, '_get_healthy_ports', return_value=[10001]):
            # Workspace A acquires and releases with cooldown
            result_a = self.manager.acquire("workspace_a", ttl=60)
            port = result_a.proxy_port
            self.manager.release("workspace_a", f"127.0.0.1:{port}", cooldown_seconds=300)
            
            # Workspace A cannot get this port anymore (in cooldown)
            result_a2 = self.manager.acquire("workspace_a", ttl=60)
            self.assertFalse(result_a2.success)  # Blocked by cooldown
            
            # Workspace B should still be able to get this port
            result_b = self.manager.acquire("workspace_b", ttl=60)
        
        self.assertTrue(result_b.success)
        self.assertEqual(result_b.proxy_port, port)  # Gets the cooldown port
    
    def test_lru_selection(self):
        """Test LRU port selection."""
        manager = LeaseManager()
        
        # Manually set usage stats to test LRU
        now = datetime.now()
        manager._usage_stats[10001] = MagicMock(last_used_at=now - timedelta(hours=2))
        manager._usage_stats[10002] = MagicMock(last_used_at=now - timedelta(hours=1))
        manager._usage_stats[10003] = MagicMock(last_used_at=now)
        
        with patch.object(manager, '_get_healthy_ports', return_value=[10001, 10002, 10003]):
            result = manager.acquire("workspace_x", ttl=60)
        
        # Should select 10001 (least recently used)
        self.assertEqual(result.proxy_port, 10001)
    
    def test_ttl_expiration(self):
        """Test that expired leases are cleaned up."""
        # Create a lease that's already expired
        key = "workspace_a:10001"
        self.manager._active_leases[key] = LeaseRecord(
            lease_id="test-id",
            workspace_id="workspace_a",
            proxy_port=10001,
            acquired_at=datetime.now() - timedelta(seconds=120),
            expires_at=datetime.now() - timedelta(seconds=60)  # Expired 60s ago
        )
        
        with self._mock_healthy_ports():
            # Acquire should clean up expired and allow reuse
            result = self.manager.acquire("workspace_a", ttl=60)
        
        self.assertTrue(result.success)
        # Should be able to get port 10001 since expired lease was cleaned
        self.assertIn(result.proxy_port, self.mock_healthy_ports)
    
    def test_get_status(self):
        """Test status query."""
        with self._mock_healthy_ports():
            self.manager.acquire("workspace_a", ttl=60)
            self.manager.acquire("workspace_b", ttl=60)
        
        # Get all status
        status = self.manager.get_status()
        self.assertEqual(status["total_active"], 2)
        
        # Get filtered status
        status_a = self.manager.get_status(workspace_id="workspace_a")
        self.assertEqual(status_a["total_active"], 1)
    
    def test_get_stats(self):
        """Test statistics query."""
        with self._mock_healthy_ports():
            self.manager.acquire("workspace_a", ttl=60)
            self.manager.acquire("workspace_b", ttl=60)
        
        stats = self.manager.get_stats()
        self.assertEqual(stats["total_active_leases"], 2)
        self.assertIn("workspace_a", stats["workspaces"])
        self.assertIn("workspace_b", stats["workspaces"])


class TestLeaseRecord(unittest.TestCase):
    """Test cases for LeaseRecord."""
    
    def test_is_expired_false(self):
        """Test that active lease is not expired."""
        record = LeaseRecord(
            lease_id="test",
            workspace_id="ws",
            proxy_port=10001,
            acquired_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        self.assertFalse(record.is_expired())
    
    def test_is_expired_true(self):
        """Test that old lease is expired."""
        record = LeaseRecord(
            lease_id="test",
            workspace_id="ws",
            proxy_port=10001,
            acquired_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1)
        )
        self.assertTrue(record.is_expired())


class TestCooldownRecord(unittest.TestCase):
    """Test cases for CooldownRecord."""
    
    def test_is_expired_false(self):
        """Test that active cooldown is not expired."""
        record = CooldownRecord(
            workspace_id="ws",
            proxy_port=10001,
            until=datetime.now() + timedelta(hours=1),
            set_at=datetime.now()
        )
        self.assertFalse(record.is_expired())
    
    def test_is_expired_true(self):
        """Test that old cooldown is expired."""
        record = CooldownRecord(
            workspace_id="ws",
            proxy_port=10001,
            until=datetime.now() - timedelta(hours=1),
            set_at=datetime.now() - timedelta(hours=2)
        )
        self.assertTrue(record.is_expired())


if __name__ == "__main__":
    unittest.main()
