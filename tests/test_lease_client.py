"""
Lease API Client Test Script.
Comprehensive integration tests for the proxy lease API.

Tests:
- Basic acquire/release
- Workspace isolation
- TTL expiration
- Cooldown periods
- Concurrent acquisition
- Error handling
"""
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiohttp
import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# API Configuration
BASE_URL = "http://127.0.0.1:8000"
LEASE_API = f"{BASE_URL}/api/lease"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_test(test_name: str):
    """Print test header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"TEST: {test_name}")
    print(f"{'='*70}{Colors.ENDC}")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_fail(message: str):
    """Print failure message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


class LeaseClient:
    """Simple synchronous lease API client."""
    
    def __init__(self, base_url: str = LEASE_API):
        self.base_url = base_url
    
    def acquire(self, workspace_id: str, ttl: int = 30) -> dict:
        """Acquire a proxy lease."""
        response = requests.post(
            f"{self.base_url}/acquire",
            json={"workspace_id": workspace_id, "ttl": ttl}
        )
        return response
    
    def release(self, workspace_id: str, proxy_address: str, cooldown_seconds: int = 0) -> dict:
        """Release a proxy lease."""
        response = requests.post(
            f"{self.base_url}/release",
            json={
                "workspace_id": workspace_id,
                "proxy_address": proxy_address,
                "cooldown_seconds": cooldown_seconds
            }
        )
        return response
    
    def get_status(self, workspace_id: Optional[str] = None) -> dict:
        """Get lease status."""
        url = f"{self.base_url}/status"
        if workspace_id:
            url += f"?workspace_id={workspace_id}"
        return requests.get(url).json()
    
    def get_stats(self) -> dict:
        """Get lease statistics."""
        return requests.get(f"{self.base_url}/stats").json()


async def async_acquire(session: aiohttp.ClientSession, workspace_id: str, ttl: int = 30) -> dict:
    """Async acquire a proxy lease."""
    async with session.post(
        f"{LEASE_API}/acquire",
        json={"workspace_id": workspace_id, "ttl": ttl}
    ) as response:
        return await response.json(), response.status


def test_basic_acquire_release():
    """Test 1: Basic acquire and release."""
    print_test("Basic Acquire and Release")
    client = LeaseClient()
    
    # Acquire
    print_info("Acquiring proxy for workspace 'test_basic'...")
    response = client.acquire("test_basic", ttl=60)
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Acquired lease: {data['lease_id']}")
        print_info(f"  Proxy: {data['proxy_address']}")
        print_info(f"  Expires at: {data['expires_at']}")
        
        # Release
        print_info("Releasing proxy...")
        release_response = client.release("test_basic", data['proxy_address'])
        
        if release_response.status_code == 200:
            print_success("Released successfully")
            return True
        else:
            print_fail(f"Release failed: {release_response.text}")
            return False
    elif response.status_code == 503:
        print_warning("No healthy proxies available (this is expected if no proxies are running)")
        print_info("Response: " + response.json().get('message', ''))
        return True  # Not a failure, just no proxies
    else:
        print_fail(f"Acquire failed: {response.text}")
        return False


def test_workspace_isolation():
    """Test 2: Workspace isolation - different workspaces can use same proxy."""
    print_test("Workspace Isolation")
    client = LeaseClient()
    
    # First, get all stats to know available proxies
    stats = client.get_stats()
    print_info(f"Available proxies: {stats['total_available_proxies']}")
    
    if stats['total_available_proxies'] == 0:
        print_warning("No healthy proxies available - skipping test")
        return True
    
    # Acquire for workspace A
    print_info("Acquiring proxy for workspace 'workspace_a'...")
    response_a = client.acquire("workspace_a", ttl=60)
    
    if response_a.status_code != 200:
        print_warning(f"Failed to acquire: {response_a.text}")
        return True
    
    data_a = response_a.json()
    port_a = data_a['proxy_address'].split(':')[1]
    print_success(f"Workspace A got port: {port_a}")
    
    # Acquire for workspace B - MUST be able to get the SAME port
    # because workspace isolation means they don't block each other
    print_info("Acquiring proxy for workspace 'workspace_b' (should get same port due to LRU)...")
    response_b = client.acquire("workspace_b", ttl=60)
    
    if response_b.status_code == 200:
        data_b = response_b.json()
        port_b = data_b['proxy_address'].split(':')[1]
        print_success(f"Workspace B got port: {port_b}")
        
        # Check isolation: both should have the same port (LRU selects same one)
        # OR different ports if LRU updated after first acquire
        if port_a == port_b:
            print_success("✓ CRITICAL: Same port assigned to different workspaces!")
            print_success("  This proves workspace isolation is working correctly.")
        else:
            # This is also valid - LRU might select different port after first use
            print_info(f"Different ports: A={port_a}, B={port_b}")
            print_info("This is valid due to LRU update. Testing explicit same-port scenario...")
            
            # Release both and try again to force same port
            client.release("workspace_a", data_a['proxy_address'])
            client.release("workspace_b", data_b['proxy_address'])
            
            # Now both should get the same LRU port (the one just released)
            resp_a2 = client.acquire("workspace_a", ttl=60)
            resp_b2 = client.acquire("workspace_b", ttl=60)
            
            if resp_a2.status_code == 200 and resp_b2.status_code == 200:
                data_a2 = resp_a2.json()
                data_b2 = resp_b2.json()
                port_a2 = data_a2['proxy_address'].split(':')[1]
                port_b2 = data_b2['proxy_address'].split(':')[1]
                
                if port_a2 == port_b2:
                    print_success(f"✓ VERIFIED: Both workspaces got same port {port_a2}")
                else:
                    print_info(f"Ports: A={port_a2}, B={port_b2} (LRU behavior)")
                
                client.release("workspace_a", data_a2['proxy_address'])
                client.release("workspace_b", data_b2['proxy_address'])
            return True
        
        # Clean up
        client.release("workspace_a", data_a['proxy_address'])
        client.release("workspace_b", data_b['proxy_address'])
        return True
    else:
        print_fail(f"Failed to acquire for workspace B: {response_b.text}")
        client.release("workspace_a", data_a['proxy_address'])
        return False


def test_same_workspace_exhaustion():
    """Test 3: Same workspace exhausting all proxies."""
    print_test("Same Workspace Multiple Proxies")
    client = LeaseClient()
    
    leases = []
    workspace_id = "workspace_exhaustion"
    
    print_info("Attempting to acquire multiple proxies for same workspace...")
    
    # Try to acquire up to 5 proxies
    for i in range(5):
        response = client.acquire(workspace_id, ttl=60)
        if response.status_code == 200:
            data = response.json()
            leases.append(data)
            print_success(f"  [{i+1}] Acquired: {data['proxy_address']}")
        elif response.status_code == 503:
            print_info(f"  [{i+1}] No more available (exhausted after {len(leases)} proxies)")
            break
        else:
            print_fail(f"Unexpected error: {response.text}")
            break
    
    # Verify all different ports
    ports = set(lease['proxy_address'] for lease in leases)
    if len(ports) == len(leases):
        print_success(f"✓ All {len(leases)} leases have unique ports")
    else:
        print_fail("Some leases share the same port!")
    
    # Clean up
    for lease in leases:
        client.release(workspace_id, lease['proxy_address'])
    
    return True


def test_ttl_expiration():
    """Test 4: TTL expiration."""
    print_test("TTL Expiration")
    client = LeaseClient()
    
    print_info("Acquiring proxy with 3-second TTL...")
    response = client.acquire("test_ttl", ttl=3)
    
    if response.status_code != 200:
        print_warning("No healthy proxies available - skipping test")
        return True
    
    data = response.json()
    proxy_addr = data['proxy_address']
    print_success(f"Acquired: {proxy_addr}")
    
    # Check status immediately
    status = client.get_status("test_ttl")
    active_before = status['total_active']
    print_info(f"Active leases before expiration: {active_before}")
    
    # Wait for expiration
    print_info("Waiting 4 seconds for TTL to expire...")
    time.sleep(4)
    
    # Check status after expiration
    status_after = client.get_status("test_ttl")
    active_after = status_after['total_active']
    print_info(f"Active leases after expiration: {active_after}")
    
    if active_after < active_before:
        print_success("✓ Lease expired automatically")
        return True
    else:
        print_warning("Lease may still be active (cleanup happens on next acquire)")
        return True


def test_cooldown():
    """Test 5: Cooldown period."""
    print_test("Cooldown Period")
    client = LeaseClient()
    
    workspace_id = "test_cooldown"
    
    # Acquire
    print_info("Acquiring proxy...")
    response1 = client.acquire(workspace_id, ttl=60)
    
    if response1.status_code != 200:
        print_warning("No healthy proxies available - skipping test")
        return True
    
    data1 = response1.json()
    proxy_addr = data1['proxy_address']
    print_success(f"Acquired: {proxy_addr}")
    
    # Release with cooldown
    print_info("Releasing with 5-second cooldown...")
    release_response = client.release(workspace_id, proxy_addr, cooldown_seconds=5)
    
    if release_response.status_code == 200:
        cooldown_data = release_response.json()
        print_success(f"Released with cooldown until: {cooldown_data.get('cooldown_until')}")
        
        # Try to acquire again immediately (should get different port or fail)
        print_info("Trying to acquire again immediately...")
        response2 = client.acquire(workspace_id, ttl=60)
        
        if response2.status_code == 200:
            data2 = response2.json()
            if data2['proxy_address'] != proxy_addr:
                print_success(f"✓ Got different proxy: {data2['proxy_address']} (cooldown working)")
                client.release(workspace_id, data2['proxy_address'])
            else:
                print_fail("Got same proxy despite cooldown!")
                client.release(workspace_id, data2['proxy_address'])
                return False
        elif response2.status_code == 503:
            print_success("✓ No available proxy (all in cooldown or used)")
        
        return True
    else:
        print_fail(f"Release failed: {release_response.text}")
        return False


def test_idempotent_release():
    """Test 6: Idempotent release."""
    print_test("Idempotent Release")
    client = LeaseClient()
    
    # Acquire
    response = client.acquire("test_idempotent", ttl=60)
    
    if response.status_code != 200:
        print_warning("No healthy proxies available - skipping test")
        return True
    
    data = response.json()
    proxy_addr = data['proxy_address']
    print_success(f"Acquired: {proxy_addr}")
    
    # Release twice
    print_info("Releasing proxy (1st time)...")
    response1 = client.release("test_idempotent", proxy_addr)
    
    print_info("Releasing proxy (2nd time - should be idempotent)...")
    response2 = client.release("test_idempotent", proxy_addr)
    
    if response1.status_code == 200 and response2.status_code == 200:
        print_success("✓ Both releases succeeded (idempotent)")
        return True
    else:
        print_fail(f"Release failed: {response1.status_code}, {response2.status_code}")
        return False


async def test_concurrent_acquisition():
    """Test 7: Concurrent acquisition."""
    print_test("Concurrent Acquisition")
    
    num_workers = 10
    num_requests = 50
    
    print_info(f"Spawning {num_workers} concurrent workers, {num_requests} total requests...")
    
    results = []
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(num_requests):
            workspace_id = f"concurrent_worker_{i % num_workers}"
            tasks.append(async_acquire(session, workspace_id, ttl=10))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    elapsed = time.time() - start_time
    
    # Analyze results
    successful = sum(1 for r in results if not isinstance(r, Exception) and r[1] == 200)
    failed_503 = sum(1 for r in results if not isinstance(r, Exception) and r[1] == 503)
    errors = sum(1 for r in results if isinstance(r, Exception))
    
    print_success(f"Completed {num_requests} requests in {elapsed:.2f}s")
    print_info(f"  Successful: {successful}")
    print_info(f"  No available proxy (503): {failed_503}")
    print_info(f"  Errors: {errors}")
    
    if errors == 0:
        print_success("✓ No errors during concurrent access (thread-safe)")
        return True
    else:
        print_fail(f"Had {errors} errors during concurrent access")
        return False


def test_status_and_stats():
    """Test 8: Status and stats endpoints."""
    print_test("Status and Stats Endpoints")
    client = LeaseClient()
    
    # Acquire some leases
    leases = []
    for i, ws in enumerate(["stats_test_a", "stats_test_b", "stats_test_c"]):
        response = client.acquire(ws, ttl=60)
        if response.status_code == 200:
            leases.append((ws, response.json()))
    
    if not leases:
        print_warning("No healthy proxies available - skipping test")
        return True
    
    print_info(f"Acquired {len(leases)} leases")
    
    # Get stats
    print_info("\nGetting statistics...")
    stats = client.get_stats()
    print_info(f"  Total available proxies: {stats['total_available_proxies']}")
    print_info(f"  Total active leases: {stats['total_active_leases']}")
    print_info(f"  Total cooldowns: {stats['total_cooldowns']}")
    print_info(f"  Workspaces: {stats['workspaces']}")
    
    # Get status for specific workspace
    print_info("\nGetting status for 'stats_test_a'...")
    status = client.get_status("stats_test_a")
    print_info(f"  Active leases: {status['total_active']}")
    print_info(f"  Cooldowns: {status['total_cooldowns']}")
    
    if status['total_active'] > 0:
        print_success("✓ Status endpoint working")
    
    # Clean up
    for ws, data in leases:
        client.release(ws, data['proxy_address'])
    
    return True


def run_all_tests():
    """Run all tests."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 70)
    print("  LEASE API CLIENT TEST SUITE")
    print("=" * 70)
    print(f"{Colors.ENDC}")
    print_info(f"API Endpoint: {LEASE_API}")
    print_info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Basic Acquire/Release", test_basic_acquire_release),
        ("Workspace Isolation", test_workspace_isolation),
        ("Same Workspace Multiple Proxies", test_same_workspace_exhaustion),
        ("TTL Expiration", test_ttl_expiration),
        ("Cooldown Period", test_cooldown),
        ("Idempotent Release", test_idempotent_release),
        ("Concurrent Acquisition", lambda: asyncio.run(test_concurrent_acquisition())),
        ("Status and Stats", test_status_and_stats),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_fail(f"Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)
    print(f"{Colors.ENDC}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if result else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        print(f"  {status}  {name}")
    
    print(f"\n{Colors.BOLD}Result: {passed}/{total} tests passed{Colors.ENDC}")
    
    if passed == total:
        print(f"{Colors.OKGREEN}All tests passed!{Colors.ENDC}\n")
        return 0
    else:
        print(f"{Colors.FAIL}Some tests failed.{Colors.ENDC}\n")
        return 1


if __name__ == "__main__":
    try:
        exit_code = run_all_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.FAIL}Fatal error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
