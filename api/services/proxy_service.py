"""
Proxy management service.
Handles active proxies and Xray process management.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import sys
import time

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.xray_prism.models import ProxyNode, Protocol, NetworkType
from src.xray_prism.generator import ConfigGenerator
from src.xray_prism.runner import XrayRunner
from src.xray_prism.tester import ProxyTester

from api.services.subscription_service import get_subscription_service

# Import health service (delayed to avoid circular import)
def get_health_service():
    from api.services.health_service import get_health_service as _get_health
    return _get_health()


class ProxyService:
    """Service for managing active proxies and Xray process."""
    
    DATA_DIR = PROJECT_ROOT / "data"
    PROXIES_FILE = DATA_DIR / "active_proxies.json"
    CONFIG_FILE = PROJECT_ROOT / "config.json"
    
    def __init__(self):
        """Initialize the proxy service."""
        self._ensure_data_dir()
        self._load_data()
        self._runner: Optional[XrayRunner] = None
        self._start_time: Optional[float] = None
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.PROXIES_FILE.exists():
            self._save_data({"proxies": [], "start_port": 10000})
    
    def _load_data(self) -> Dict:
        """Load proxy data from JSON file."""
        if self.PROXIES_FILE.exists():
            with open(self.PROXIES_FILE, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        else:
            self._data = {"proxies": [], "start_port": 10000}
        return self._data
    
    def _save_data(self, data: Optional[Dict] = None):
        """Save proxy data to JSON file."""
        if data:
            self._data = data
        with open(self.PROXIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
    
    def get_all_proxies(self) -> List[Dict]:
        """Get all active proxies."""
        self._load_data()
        return self._data.get("proxies", [])
    
    def get_xray_status(self) -> str:
        """Get current Xray status."""
        if self._runner and self._runner.is_running():
            return "running"
        return "stopped"
    
    def get_uptime(self) -> Optional[int]:
        """Get Xray uptime in seconds."""
        if self._start_time and self._runner and self._runner.is_running():
            return int(time.time() - self._start_time)
        return None
    
    def add_proxies(self, node_ids: List[str], start_port: int = 10000) -> List[Dict]:
        """Add nodes to the active proxy list."""
        self._load_data()
        
        subscription_service = get_subscription_service()
        nodes_data = subscription_service.get_nodes_by_ids(node_ids)
        
        if not nodes_data:
            raise ValueError("No valid nodes found")
        
        # Calculate next available port
        existing_ports = {p["port"] for p in self._data.get("proxies", [])}
        current_port = start_port
        
        new_proxies = []
        for node in nodes_data:
            # Skip if node already in proxies
            if any(p["node_id"] == node["id"] for p in self._data.get("proxies", [])):
                continue
            
            # Find next available port
            while current_port in existing_ports:
                current_port += 1
            
            proxy = {
                "port": current_port,
                "node_id": node["id"],
                "node_name": node["name"],
                "protocol": node["protocol"],
                "address": node["address"],
                "server_port": node["port"],
                "test_status": "pending",
                "latency_ms": None,
                "exit_ip": None
            }
            new_proxies.append(proxy)
            self._data["proxies"].append(proxy)
            existing_ports.add(current_port)
            current_port += 1
        
        self._data["start_port"] = start_port
        self._save_data()
        
        # Regenerate config if Xray is running
        if self._runner and self._runner.is_running():
            self._regenerate_and_restart()
        
        return new_proxies
    
    def remove_proxy(self, port: int) -> bool:
        """Remove a proxy by port."""
        self._load_data()
        
        initial_count = len(self._data.get("proxies", []))
        self._data["proxies"] = [
            p for p in self._data.get("proxies", []) 
            if p["port"] != port
        ]
        
        if len(self._data["proxies"]) < initial_count:
            self._save_data()
            
            # Regenerate config if Xray is running
            if self._runner and self._runner.is_running():
                self._regenerate_and_restart()
            
            return True
        return False
    
    def clear_all_proxies(self) -> int:
        """Remove all proxies."""
        self._load_data()
        count = len(self._data.get("proxies", []))
        self._data["proxies"] = []
        self._save_data()
        
        # Stop Xray if running
        if self._runner and self._runner.is_running():
            self._runner.stop()
        
        return count
    
    def _build_proxy_nodes(self) -> List[ProxyNode]:
        """Build ProxyNode objects from active proxies."""
        self._load_data()
        subscription_service = get_subscription_service()
        
        proxy_nodes = []
        for proxy in self._data.get("proxies", []):
            node_data = subscription_service.get_node(proxy["node_id"])
            if not node_data:
                continue
            
            # Map stored field names to ProxyNode field names
            proxy_node = ProxyNode(
                name=node_data["name"],
                protocol=Protocol(node_data["protocol"]),
                address=node_data["address"],
                port=node_data["port"],
                uuid=node_data.get("uuid"),
                password=node_data.get("password"),
                security=node_data.get("security", "auto"),
                network=NetworkType(node_data.get("network", "tcp")),
                tls=node_data.get("tls", False),
                sni=node_data.get("sni"),
                allow_insecure=node_data.get("allow_insecure", False),
                path=node_data.get("ws_path"),  # ws_path -> path
                host=node_data.get("ws_host"),  # ws_host -> host
                service_name=node_data.get("grpc_service_name"),  # grpc_service_name -> service_name
                fingerprint=node_data.get("fingerprint"),
            )
            # Store local port for mapping
            proxy_node._local_port = proxy["port"]
            proxy_nodes.append(proxy_node)
        
        return proxy_nodes
    
    def _regenerate_config(self) -> str:
        """Regenerate Xray configuration file."""
        proxy_nodes = self._build_proxy_nodes()
        
        if not proxy_nodes:
            return str(self.CONFIG_FILE)
        
        # Create port mappings
        from src.xray_prism.models import PortMapping
        port_mappings = []
        for node in proxy_nodes:
            local_port = getattr(node, '_local_port', None)
            if local_port:
                port_mappings.append(PortMapping(local_port=local_port, node=node))
        
        generator = ConfigGenerator(inbound_protocol="http")
        # Use port_mappings for generation
        generator.generate_and_save_with_mappings(port_mappings, str(self.CONFIG_FILE))
        
        return str(self.CONFIG_FILE)
    
    def _regenerate_and_restart(self):
        """Regenerate config and restart Xray."""
        config_path = self._regenerate_config()
        if self._runner:
            self._runner.stop()
            time.sleep(0.5)
            self._runner.start(config_path)
    
    def start_xray(self) -> Dict:
        """Start the Xray process."""
        if self._runner and self._runner.is_running():
            return {"success": True, "message": "Xray is already running", "status": "running"}
        
        # Check if there are any proxies
        self._load_data()
        if not self._data.get("proxies"):
            return {"success": False, "message": "No proxies configured", "status": "stopped"}
        
        # Generate config
        config_path = self._regenerate_config()
        
        # Initialize runner if needed
        if not self._runner:
            self._runner = XrayRunner()
        
        # Try to find or download Xray
        xray_path = self._runner.find_xray()
        if not xray_path:
            try:
                self._runner.download_xray()
            except Exception as e:
                return {"success": False, "message": f"Failed to download Xray: {e}", "status": "stopped"}
        
        # Start Xray
        try:
            self._runner.start(config_path)
            self._start_time = time.time()
            
            # Start health monitoring
            try:
                health_service = get_health_service()
                active_ports = [p["port"] for p in self._data.get("proxies", [])]
                health_service.sync_with_proxies(active_ports)
                health_service.start_monitoring(
                    lambda: [p["port"] for p in self.get_all_proxies()]
                )
            except Exception as e:
                # Log but don't fail if health monitoring fails
                print(f"Warning: Failed to start health monitoring: {e}")
            
            return {"success": True, "message": "Xray started successfully", "status": "running"}
        except Exception as e:
            return {"success": False, "message": f"Failed to start Xray: {e}", "status": "error"}
    
    def stop_xray(self) -> Dict:
        """Stop the Xray process."""
        if not self._runner or not self._runner.is_running():
            return {"success": True, "message": "Xray is not running", "status": "stopped"}
        
        try:
            self._runner.stop()
            self._start_time = None
            
            # Stop health monitoring
            try:
                health_service = get_health_service()
                health_service.stop_monitoring()
            except Exception as e:
                print(f"Warning: Failed to stop health monitoring: {e}")
            
            return {"success": True, "message": "Xray stopped successfully", "status": "stopped"}
        except Exception as e:
            return {"success": False, "message": f"Failed to stop Xray: {e}", "status": "error"}
    
    def restart_xray(self) -> Dict:
        """Restart the Xray process."""
        self.stop_xray()
        time.sleep(0.5)
        return self.start_xray()
    
    def test_all_proxies(self, timeout: int = 5, workers: int = 20) -> List[Dict]:
        """Test all active proxies."""
        self._load_data()
        
        if not self._data.get("proxies"):
            return []
        
        # Ensure Xray is running
        if not self._runner or not self._runner.is_running():
            raise RuntimeError("Xray is not running. Please start Xray first.")
        
        # Build proxy nodes and port mappings for tester
        proxy_nodes = self._build_proxy_nodes()
        
        from src.xray_prism.models import PortMapping
        mappings = []
        for node in proxy_nodes:
            local_port = getattr(node, '_local_port', None)
            if local_port:
                mappings.append(PortMapping(local_port=local_port, node=node))
        
        # Run tests
        tester = ProxyTester(timeout=timeout, max_workers=workers)
        results = tester.test_all(mappings)
        
        # Update proxy test results
        test_results = []
        for result in results:
            for proxy in self._data["proxies"]:
                if proxy["port"] == result.local_port:
                    if result.success:
                        proxy["test_status"] = "success"
                        proxy["latency_ms"] = int(result.latency_ms) if result.latency_ms else None
                        proxy["exit_ip"] = result.exit_ip
                    else:
                        proxy["test_status"] = "failed"
                        proxy["latency_ms"] = None
                        proxy["exit_ip"] = None
                    
                    test_results.append({
                        "node_id": proxy["node_id"],
                        "name": proxy["node_name"],
                        "port": proxy["port"],
                        "status": proxy["test_status"],
                        "latency_ms": proxy["latency_ms"],
                        "exit_ip": proxy["exit_ip"],
                        "error": result.error
                    })
                    break
        
        self._save_data()
        return test_results
    
    def test_single_proxy(self, port: int, timeout: int = 5) -> Optional[Dict]:
        """Test a single proxy by port."""
        self._load_data()
        
        proxy = next((p for p in self._data.get("proxies", []) if p["port"] == port), None)
        if not proxy:
            return None
        
        # Ensure Xray is running
        if not self._runner or not self._runner.is_running():
            raise RuntimeError("Xray is not running. Please start Xray first.")
        
        tester = ProxyTester(timeout=timeout, max_workers=1)
        result = tester.test_port(port, proxy["node_name"])
        
        if result.success:
            proxy["test_status"] = "success"
            proxy["latency_ms"] = int(result.latency_ms) if result.latency_ms else None
            proxy["exit_ip"] = result.exit_ip
        else:
            proxy["test_status"] = "failed"
            proxy["latency_ms"] = None
            proxy["exit_ip"] = None
        
        self._save_data()
        
        return {
            "node_id": proxy["node_id"],
            "name": proxy["node_name"],
            "port": proxy["port"],
            "status": proxy["test_status"],
            "latency_ms": proxy["latency_ms"],
            "exit_ip": proxy["exit_ip"],
            "error": result.error
        }


# Singleton instance
_proxy_service: Optional[ProxyService] = None

def get_proxy_service() -> ProxyService:
    """Get the singleton proxy service instance."""
    global _proxy_service
    if _proxy_service is None:
        _proxy_service = ProxyService()
    return _proxy_service
