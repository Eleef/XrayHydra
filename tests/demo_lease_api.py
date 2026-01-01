"""
Lease API Demo Script.
Interactive demonstration of the proxy lease API with real proxies.

This script:
1. Checks if proxies are available
2. If not, provides instructions to set up proxies
3. Runs comprehensive tests with actual proxy leases
"""
import sys
import time
from pathlib import Path

import requests

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

BASE_URL = "http://127.0.0.1:8000"


def check_proxies():
    """Check if any proxies are available."""
    try:
        response = requests.get(f"{BASE_URL}/api/proxies")
        if response.status_code == 200:
            data = response.json()
            return data.get('total', 0), data.get('proxies', [])
    except Exception as e:
        print(f"Error checking proxies: {e}")
        return 0, []


def check_health_status():
    """Check health status of proxies."""
    try:
        response = requests.get(f"{BASE_URL}/api/health/status")
        if response.status_code == 200:
            data = response.json()
            states = data.get('states', [])
            healthy = [s for s in states if s.get('status') == 'healthy']
            return len(healthy), states
    except Exception as e:
        print(f"Error checking health: {e}")
        return 0, []


def demo_with_proxies():
    """Run demo with actual proxies."""
    print("\n" + "="*70)
    print("  LEASE API INTERACTIVE DEMO")
    print("="*70)
    
    # Check available proxies
    total_proxies, proxies = check_proxies()
    healthy_count, health_states = check_health_status()
    
    print(f"\nProxy Status:")
    print(f"  Total proxies: {total_proxies}")
    print(f"  Healthy proxies: {healthy_count}")
    
    if healthy_count == 0:
        print("\n❌ No healthy proxies available!")
        print("\nTo run this demo, you need to:")
        print("  1. Add a subscription via the web UI (http://localhost:8000)")
        print("  2. Refresh the subscription to get nodes")
        print("  3. Add some nodes to the proxy list")
        print("  4. Start Xray")
        print("  5. Wait for health monitoring to mark them as healthy")
        print("\nAlternatively, run the unit tests which don't require proxies:")
        print("  python -m pytest tests/test_lease_service.py -v")
        return
    
    print(f"\n✓ Found {healthy_count} healthy proxies - ready for demo!\n")
    
    # Demo 1: Single workspace acquisition
    print("="*70)
    print("DEMO 1: Single Workspace - Acquire and Release")
    print("="*70)
    
    print("\n1. Acquiring proxy for 'demo_workspace_1' with 60s TTL...")
    response = requests.post(
        f"{BASE_URL}/api/lease/acquire",
        json={"workspace_id": "demo_workspace_1", "ttl": 60}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Lease acquired!")
        print(f"     Lease ID: {data['lease_id']}")
        print(f"     Proxy: {data['proxy_address']}")
        print(f"     Expires: {data['expires_at']}")
        
        lease_id_1 = data['lease_id']
        proxy_addr_1 = data['proxy_address']
        
        # Check status
        print("\n2. Checking lease status...")
        status = requests.get(f"{BASE_URL}/api/lease/status?workspace_id=demo_workspace_1").json()
        print(f"   Active leases: {status['total_active']}")
        
        # Release
        print("\n3. Releasing proxy with 10-second cooldown...")
        release_resp = requests.post(
            f"{BASE_URL}/api/lease/release",
            json={
                "workspace_id": "demo_workspace_1",
                "proxy_address": proxy_addr_1,
                "cooldown_seconds": 10
            }
        )
        if release_resp.status_code == 200:
            print(f"   ✓ Released! Cooldown until: {release_resp.json()['cooldown_until']}")
    else:
        print(f"   ✗ Failed: {response.json()}")
    
    # Demo 2: Workspace Isolation
    print("\n" + "="*70)
    print("DEMO 2: Workspace Isolation - Multiple Workspaces")
    print("="*70)
    
    workspaces = ["crawler_A", "crawler_B", "crawler_C"]
    leases = []
    
    print("\nAcquiring proxies for 3 different workspaces...")
    for ws in workspaces:
        response = requests.post(
            f"{BASE_URL}/api/lease/acquire",
            json={"workspace_id": ws, "ttl": 60}
        )
        if response.status_code == 200:
            data = response.json()
            leases.append((ws, data))
            port = data['proxy_address'].split(':')[1]
            print(f"  ✓ {ws}: port {port}")
        else:
            print(f"  ✗ {ws}: {response.json().get('message', 'failed')}")
    
    # Check if multiple workspaces got the same port
    if len(leases) >= 2:
        ports = [lease[1]['proxy_address'].split(':')[1] for lease in leases]
        unique_ports = set(ports)
        print(f"\n  Ports assigned: {ports}")
        if len(unique_ports) < len(ports):
            print(f"  ✓ Workspace isolation confirmed: {len(ports) - len(unique_ports)} port(s) shared!")
        else:
            print(f"  ℹ All workspaces got different ports (LRU distribution)")
    
    # Show stats
    print("\n" + "="*70)
    print("DEMO 3: System Statistics")
    print("="*70)
    
    stats = requests.get(f"{BASE_URL}/api/lease/stats").json()
    print(f"\nSystem Stats:")
    print(f"  Available proxies: {stats['total_available_proxies']}")
    print(f"  Active leases: {stats['total_active_leases']}")
    print(f"  Cooldowns: {stats['total_cooldowns']}")
    print(f"  Workspaces: {', '.join(stats['workspaces'])}")
    
    if stats['proxies_by_usage']:
        print(f"\n  Top Used Proxies:")
        for proxy in stats['proxies_by_usage'][:5]:
            print(f"    Port {proxy['port']}: used {proxy['usage_count']} times")
    
    # Clean up
    print("\n" + "="*70)
    print("Cleaning up...")
    print("="*70)
    for ws, data in leases:
        requests.post(
            f"{BASE_URL}/api/lease/release",
            json={
                "workspace_id": ws,
                "proxy_address": data['proxy_address'],
                "cooldown_seconds": 0
            }
        )
        print(f"  ✓ Released {ws}")
    
    print("\n✓ Demo complete!")
    print("\nNext steps:")
    print("  - Check the API docs: http://localhost:8000/docs#/Lease")
    print("  - Run concurrent tests: python tests/test_lease_client.py")
    print("  - Run unit tests: python -m pytest tests/test_lease_service.py -v")


if __name__ == "__main__":
    try:
        demo_with_proxies()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
