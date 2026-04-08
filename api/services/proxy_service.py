"""
Proxy management service.
Handles active proxies and Xray process management.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys
import time
from datetime import datetime

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.xray_prism.capabilities import evaluate_node_runtime
from src.xray_prism.models import (
    ProxyNode,
    Protocol,
    NetworkType,
)
from src.xray_prism.proxy_runtime import build_proxy_address
from src.xray_prism.generator import ConfigGenerator
from src.xray_prism.runner import XrayRunner
from src.xray_prism.tester import ProxyTester

from api.services.subscription_service import get_subscription_service
from api.services.custom_group_service import get_custom_group_service

logger = logging.getLogger(__name__)

DEFAULT_PROXY_SCHEME = "http"
SUPPORTED_PROXY_PROTOCOLS = ("http", "socks5")
POOL_STATUS_ACTIVE = "active"
POOL_STATUS_DEDUPE_DISABLED = "dedupe_disabled"
DISABLED_REASON_EXIT_IP_DUPLICATE = "exit_ip_duplicate"


def build_proxy_access_fields(port: int) -> Dict[str, object]:
    """Build explicit client-facing access metadata for a local proxy port."""
    proxy_address = build_proxy_address(port)
    return {
        "proxy_address": proxy_address,
        "proxy_scheme": DEFAULT_PROXY_SCHEME,
        "supported_proxy_protocols": list(SUPPORTED_PROXY_PROTOCOLS),
        "http_proxy_url": f"http://{proxy_address}",
        "socks5_proxy_url": f"socks5://{proxy_address}",
        "socks5h_proxy_url": f"socks5h://{proxy_address}",
    }

# Import health service (delayed to avoid circular import)
def get_health_service():
    from api.services.health_service import get_health_service as _get_health
    return _get_health()


class ProxyService:
    """Service for managing active proxies and Xray process."""
    
    DATA_DIR = PROJECT_ROOT / "data"
    PROXIES_FILE = DATA_DIR / "active_proxies.json"
    CONFIG_FILE = PROJECT_ROOT / "config.json"

    @staticmethod
    def build_proxy_access_fields(port: int) -> Dict[str, object]:
        """Expose client-facing proxy metadata for a local port."""
        return build_proxy_access_fields(port)
    
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
        proxies = self._data.get("proxies", [])
        normalized = [self._normalize_proxy_record(proxy) for proxy in proxies]
        if normalized != proxies:
            self._data["proxies"] = normalized
            self._save_data()
        return self._data
    
    def _save_data(self, data: Optional[Dict] = None):
        """Save proxy data to JSON file."""
        if data:
            self._data = data
        with open(self.PROXIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _get_runner(self) -> XrayRunner:
        """Lazily create an Xray runner so service restarts can reclaim tracked processes."""
        if self._runner is None:
            self._runner = XrayRunner(project_dir=str(self.CONFIG_FILE.parent))
        return self._runner

    def _is_xray_running(self) -> bool:
        """Check runtime status using either the in-memory process or tracked process metadata."""
        return self._get_runner().is_running()

    def _load_runtime_config_ports(self) -> List[int]:
        """Read actual runtime inbound ports from the generated config file."""
        if not self.CONFIG_FILE.exists():
            return []
        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as exc:
            logger.warning("读取当前 Xray 配置失败: %s", exc)
            return []

        ports: List[int] = []
        for inbound in config.get("inbounds", []):
            try:
                port = inbound.get("port")
                if port is None:
                    continue
                ports.append(int(port))
            except (TypeError, ValueError):
                continue
        return ports

    @staticmethod
    def _normalize_proxy_record(proxy: Dict) -> Dict:
        """Normalize persisted proxy fields added by newer versions."""
        normalized = dict(proxy)
        pool_status = str(normalized.get("pool_status") or POOL_STATUS_ACTIVE)
        if pool_status not in {POOL_STATUS_ACTIVE, POOL_STATUS_DEDUPE_DISABLED}:
            pool_status = POOL_STATUS_ACTIVE
        normalized["pool_status"] = pool_status
        normalized["disabled_reason"] = normalized.get("disabled_reason") if pool_status != POOL_STATUS_ACTIVE else None
        normalized["disabled_at"] = normalized.get("disabled_at") if pool_status != POOL_STATUS_ACTIVE else None
        normalized.setdefault("exit_country", None)
        normalized.setdefault("exit_country_code", None)
        return normalized

    @staticmethod
    def is_proxy_enabled(proxy: Dict) -> bool:
        """Return whether a proxy should participate in runtime routing."""
        return str(proxy.get("pool_status") or POOL_STATUS_ACTIVE) == POOL_STATUS_ACTIVE

    def _get_runtime_proxy_ports(self) -> List[int]:
        """Return ports that are actually routable by the current Xray process."""
        self._load_data()
        if self._is_xray_running():
            runtime_ports = set(self._load_runtime_config_ports())
            return [
                int(p["port"])
                for p in self._data.get("proxies", [])
                if self.is_proxy_enabled(p) and int(p["port"]) in runtime_ports
            ]
        return []

    def get_runtime_proxy_ports(self) -> List[int]:
        """Public wrapper for routes/services that need actual runtime ports."""
        self._load_data()
        return self._get_runtime_proxy_ports()

    def _get_source_node_data(self, node_id: str) -> Optional[Dict[str, Any]]:
        node_data = get_subscription_service().get_node(node_id)
        if node_data:
            return node_data
        return get_custom_group_service().get_node(node_id)

    @staticmethod
    def _node_data_to_proxy_node(node_data: Dict[str, Any]) -> ProxyNode:
        network_value = node_data.get("network", "tcp")
        try:
            network = NetworkType(str(network_value))
        except ValueError:
            network = NetworkType.TCP
        return ProxyNode(
            name=node_data["name"],
            protocol=Protocol(node_data["protocol"]),
            address=node_data["address"],
            port=node_data["port"],
            uuid=node_data.get("uuid"),
            password=node_data.get("password"),
            security=node_data.get("security", "auto"),
            network=network,
            tls=node_data.get("tls", False),
            sni=node_data.get("sni"),
            allow_insecure=node_data.get("allow_insecure", False),
            path=node_data.get("ws_path"),
            host=node_data.get("ws_host"),
            service_name=node_data.get("grpc_service_name"),
            fingerprint=node_data.get("fingerprint"),
            alter_id=int(node_data.get("alter_id", 0)),
            flow=node_data.get("flow"),
            public_key=node_data.get("public_key"),
            short_id=node_data.get("short_id"),
            hy_obfs=node_data.get("hy_obfs"),
            hy_obfs_password=node_data.get("hy_obfs_password"),
            hy_alpn=node_data.get("hy_alpn"),
            ss_plugin=node_data.get("ss_plugin"),
            ss_plugin_opts=node_data.get("ss_plugin_opts"),
            ss_uot=node_data.get("ss_uot"),
            ss_uot_version=node_data.get("ss_uot_version"),
            raw_network=node_data.get("raw_network"),
            parse_degraded=bool(node_data.get("parse_degraded", False)),
            parse_degraded_reason=node_data.get("parse_degraded_reason"),
        )

    def get_proxy_runtime_metadata(
        self,
        proxy: Dict[str, Any],
        *,
        runtime_ports: Optional[set[int]] = None,
        xray_running: Optional[bool] = None,
    ) -> Dict[str, Optional[str] | bool]:
        """Describe whether a pool proxy is currently loaded into Xray runtime."""
        node_data = self._get_source_node_data(proxy["node_id"])
        if not node_data:
            return {
                "runtime_loaded": False,
                "runtime_load_reason": "源节点记录不存在，当前无法加载到 Xray",
            }

        capability = evaluate_node_runtime(node_data)
        if not capability.runtime_supported:
            return {
                "runtime_loaded": False,
                "runtime_load_reason": capability.reason or "当前节点不可运行",
            }

        if xray_running is None:
            xray_running = self._is_xray_running()
        if not xray_running:
            return {
                "runtime_loaded": False,
                "runtime_load_reason": "Xray 未运行",
            }

        if runtime_ports is None:
            runtime_ports = set(self._get_runtime_proxy_ports())
        if int(proxy["port"]) not in runtime_ports:
            return {
                "runtime_loaded": False,
                "runtime_load_reason": "当前节点未加载到 Xray 运行配置",
            }

        return {
            "runtime_loaded": True,
            "runtime_load_reason": None,
        }

    def _sync_health_runtime_state(self, ensure_monitoring: bool = False) -> None:
        """
        Keep health state aligned with currently routable proxy ports.

        When Xray is stopped, health states are cleared so LeaseManager cannot
        hand out stale ports from the persisted health cache.
        """
        health_service = get_health_service()
        active_ports = self._get_runtime_proxy_ports()
        health_service.sync_with_proxies(active_ports)

        if active_ports:
            if ensure_monitoring:
                health_service.start_monitoring(
                    lambda: self._get_runtime_proxy_ports()
                )
                # Xray 刚启动时立即跑一轮检测，避免沿用旧的 disabled 状态导致租约归零。
                health_service.run_health_check(active_ports)
        else:
            health_service.stop_monitoring()
    
    def get_all_proxies(self, include_disabled: bool = True) -> List[Dict]:
        """Get proxies in the pool, optionally excluding dedupe-disabled entries."""
        self._load_data()
        proxies = self._data.get("proxies", [])
        if include_disabled:
            return [dict(proxy) for proxy in proxies]
        return [dict(proxy) for proxy in proxies if self.is_proxy_enabled(proxy)]

    def get_proxy_by_port(self, port: int, include_disabled: bool = True) -> Optional[Dict]:
        """Return one proxy record by local port."""
        self._load_data()
        for proxy in self._data.get("proxies", []):
            if int(proxy.get("port", 0)) != int(port):
                continue
            if include_disabled or self.is_proxy_enabled(proxy):
                return dict(proxy)
            return None
        return None

    def get_proxies_by_exit_ip(self, exit_ip: str, include_disabled: bool = True) -> List[Dict]:
        """Return proxy records whose tested exit IP matches the provided value."""
        normalized_exit_ip = str(exit_ip or "").strip()
        if not normalized_exit_ip:
            return []
        return [
            proxy
            for proxy in self.get_all_proxies(include_disabled=include_disabled)
            if str(proxy.get("exit_ip") or "").strip() == normalized_exit_ip
        ]

    def get_proxies_by_country_code(self, country_code: str, include_disabled: bool = True) -> List[Dict]:
        """Return proxy records whose tested exit country code matches the provided value."""
        normalized_code = str(country_code or "").strip().upper()
        if not normalized_code:
            return []
        return [
            proxy
            for proxy in self.get_all_proxies(include_disabled=include_disabled)
            if str(proxy.get("exit_country_code") or "").strip().upper() == normalized_code
        ]
    
    def get_xray_status(self) -> str:
        """Get current Xray status."""
        if self._is_xray_running():
            return "running"
        return "stopped"
    
    def get_uptime(self) -> Optional[int]:
        """Get Xray uptime in seconds."""
        if self._start_time and self._is_xray_running():
            return int(time.time() - self._start_time)
        return None

    @staticmethod
    def _proxy_dedupe_rank(proxy: Dict) -> tuple:
        """Lower rank wins when keeping one proxy from the same exit IP group."""
        status_rank = 0 if proxy.get("test_status") == "success" else 1
        latency = proxy.get("latency_ms")
        latency_rank = latency if isinstance(latency, (int, float)) else float("inf")
        return (status_rank, latency_rank, int(proxy["port"]))

    def get_exit_ip_duplicate_groups(self) -> List[Dict]:
        """Preview duplicate proxies that share the same tested exit IP."""
        groups: Dict[str, List[Dict]] = {}
        for proxy in self.get_all_proxies(include_disabled=False):
            exit_ip = str(proxy.get("exit_ip") or "").strip()
            if not exit_ip:
                continue
            groups.setdefault(exit_ip, []).append(proxy)

        duplicate_groups: List[Dict] = []
        for exit_ip, proxies in groups.items():
            if len(proxies) < 2:
                continue
            ordered = sorted(proxies, key=self._proxy_dedupe_rank)
            keep_proxy = dict(ordered[0])
            remove_proxies = [dict(item) for item in ordered[1:]]
            duplicate_groups.append({
                "exit_ip": exit_ip,
                "keep_proxy": keep_proxy,
                "remove_proxies": remove_proxies,
            })

        duplicate_groups.sort(key=lambda item: item["exit_ip"])
        return duplicate_groups

    def dedupe_proxies_by_exit_ip(self, disable_ports: List[int]) -> Dict:
        """Disable duplicate proxies chosen by the user after previewing duplicate exit IP groups."""
        self._load_data()
        if not disable_ports:
            raise ValueError("disable_ports cannot be empty")

        duplicate_groups = self.get_exit_ip_duplicate_groups()
        allowed_ports = {
            int(proxy["port"])
            for group in duplicate_groups
            for proxy in group["remove_proxies"]
        }
        requested_ports = list(dict.fromkeys(int(port) for port in disable_ports))
        invalid_ports = [port for port in requested_ports if port not in allowed_ports]
        if invalid_ports:
            raise ValueError(f"Invalid duplicate proxy ports: {invalid_ports}")

        disabled = []
        kept = []
        kept_ports = set()
        disabled_at = datetime.now().isoformat(timespec="seconds")

        for proxy in self._data.get("proxies", []):
            port = int(proxy["port"])
            if port in requested_ports:
                proxy["pool_status"] = POOL_STATUS_DEDUPE_DISABLED
                proxy["disabled_reason"] = DISABLED_REASON_EXIT_IP_DUPLICATE
                proxy["disabled_at"] = disabled_at
                disabled.append(dict(proxy))

        self._save_data()

        if self._is_xray_running():
            self._regenerate_and_restart()
        else:
            self._sync_health_runtime_state()

        for group in duplicate_groups:
            keep_proxy = group["keep_proxy"]
            if any(int(item["port"]) in requested_ports for item in group["remove_proxies"]):
                keep_port = int(keep_proxy["port"])
                if keep_port not in kept_ports:
                    kept.append(dict(keep_proxy))
                    kept_ports.add(keep_port)

        return {
            "disabled_count": len(disabled),
            "disabled_ports": [int(item["port"]) for item in disabled],
            "kept_ports": sorted(kept_ports),
            "disabled": disabled,
            "kept": kept,
        }
    
    def add_proxies(self, node_ids: List[str], start_port: int = 10000) -> List[Dict]:
        """Add nodes to the active proxy list."""
        self._load_data()

        requested_ids = list(dict.fromkeys(node_ids))
        subscription_nodes = get_subscription_service().get_nodes_by_ids(requested_ids)
        custom_nodes = get_custom_group_service().get_nodes_by_ids(requested_ids)
        node_map = {node["id"]: node for node in subscription_nodes}
        node_map.update({node["id"]: node for node in custom_nodes})
        nodes_data = [node_map[node_id] for node_id in requested_ids if node_id in node_map]

        if not nodes_data:
            raise ValueError("No valid nodes found")

        unsupported_nodes = [
            node for node in nodes_data
            if not evaluate_node_runtime(node).runtime_supported
        ]
        if unsupported_nodes:
            details = ", ".join(
                f'{node.get("name", node.get("id", "unknown"))}({node.get("protocol", "unknown")})'
                for node in unsupported_nodes
            )
            raise ValueError(f"存在当前 Xray 不支持运行的节点，无法加入代理池: {details}")

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
                "exit_ip": None,
                "exit_country": None,
                "exit_country_code": None,
                "pool_status": POOL_STATUS_ACTIVE,
                "disabled_reason": None,
                "disabled_at": None,
            }
            new_proxies.append(proxy)
            self._data["proxies"].append(proxy)
            existing_ports.add(current_port)
            current_port += 1
        
        self._data["start_port"] = start_port
        self._save_data()
        
        # Regenerate config if Xray is running
        if self._is_xray_running():
            self._regenerate_and_restart()
        else:
            self._sync_health_runtime_state()

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
            if self._is_xray_running():
                self._regenerate_and_restart()
            else:
                self._sync_health_runtime_state()
            
            return True
        return False
    
    def clear_all_proxies(self) -> int:
        """Remove all proxies."""
        self._load_data()
        count = len(self._data.get("proxies", []))
        self._data["proxies"] = []
        self._save_data()
        
        # Stop Xray if running
        if self._is_xray_running():
            self.stop_xray()
        else:
            self._sync_health_runtime_state()
        
        return count
    
    def _build_proxy_nodes(self) -> List[ProxyNode]:
        """Build ProxyNode objects from active proxies."""
        self._load_data()
        
        proxy_nodes = []
        for proxy in self._data.get("proxies", []):
            if not self.is_proxy_enabled(proxy):
                continue
            node_data = self._get_source_node_data(proxy["node_id"])
            if not node_data:
                continue
            proxy_node = self._node_data_to_proxy_node(node_data)
            capability = evaluate_node_runtime(proxy_node)
            if not capability.runtime_supported:
                reason = capability.reason or f"不支持的协议: {proxy_node.protocol.value}"
                logger.warning("跳过不可运行节点 %s: %s", proxy.get("node_id"), reason)
                continue
            # Store local port for mapping
            proxy_node._local_port = proxy["port"]
            proxy_nodes.append(proxy_node)
        
        return proxy_nodes
    
    def _regenerate_config(self) -> str:
        """Regenerate Xray configuration file."""
        proxy_nodes = self._build_proxy_nodes()

        # Create port mappings
        from src.xray_prism.models import PortMapping
        port_mappings = []
        for node in proxy_nodes:
            local_port = getattr(node, '_local_port', None)
            if local_port:
                port_mappings.append(PortMapping(local_port=local_port, node=node))
        
        generator = ConfigGenerator(inbound_protocol="socks")
        # Use port_mappings for generation
        generator.generate_and_save_with_mappings(port_mappings, str(self.CONFIG_FILE))
        
        return str(self.CONFIG_FILE)
    
    def _regenerate_and_restart(self):
        """Regenerate config and restart Xray."""
        runner = self._get_runner()
        enabled_proxies = self.get_all_proxies(include_disabled=False)

        if not runner.is_running():
            self._sync_health_runtime_state()
            return

        if not enabled_proxies:
            runner.stop()
            self._start_time = None
            self._sync_health_runtime_state()
            return

        runnable_nodes = self._build_proxy_nodes()
        if not runnable_nodes:
            runner.stop()
            self._start_time = None
            self._sync_health_runtime_state()
            return

        config_path = self._regenerate_config()
        runner.stop()
        time.sleep(0.5)
        runner.start(config_path)
        self._start_time = time.time()
        self._sync_health_runtime_state(ensure_monitoring=True)
    
    def start_xray(self) -> Dict:
        """Start the Xray process."""
        if self._is_xray_running():
            return {"success": True, "message": "Xray is already running", "status": "running"}
        
        # Check if there are any proxies
        self._load_data()
        if not self.get_all_proxies(include_disabled=False):
            self._sync_health_runtime_state()
            return {"success": False, "message": "No enabled proxies configured", "status": "stopped"}

        if not self._build_proxy_nodes():
            self._sync_health_runtime_state()
            return {"success": False, "message": "No runnable proxies configured", "status": "stopped"}
        
        # Generate config
        config_path = self._regenerate_config()
        
        # Initialize runner if needed
        runner = self._get_runner()
        
        # Try to find or download Xray
        xray_path = runner.find_xray()
        if not xray_path:
            try:
                runner.download_xray()
            except Exception as e:
                return {"success": False, "message": f"Failed to download Xray: {e}", "status": "stopped"}
        
        # Start Xray
        try:
            runner.start(config_path)
            self._start_time = time.time()
            
            # Start health monitoring
            try:
                self._sync_health_runtime_state(ensure_monitoring=True)
            except Exception as e:
                # Log but don't fail if health monitoring fails
                logger.warning("Failed to start health monitoring: %s", e)
            
            return {"success": True, "message": "Xray started successfully", "status": "running"}
        except Exception as e:
            self._sync_health_runtime_state()
            return {"success": False, "message": f"Failed to start Xray: {e}", "status": "error"}
    
    def stop_xray(self) -> Dict:
        """Stop the Xray process."""
        runner = self._get_runner()
        if not runner.is_running():
            self._start_time = None
            try:
                self._sync_health_runtime_state()
            except Exception as e:
                logger.warning("Failed to clear health state while Xray already stopped: %s", e)
            return {"success": True, "message": "Xray is not running", "status": "stopped"}
        
        try:
            runner.stop()
            self._start_time = None
            
            # Stop health monitoring
            try:
                self._sync_health_runtime_state()
            except Exception as e:
                logger.warning("Failed to stop health monitoring: %s", e)
            
            return {"success": True, "message": "Xray stopped successfully", "status": "stopped"}
        except Exception as e:
            return {"success": False, "message": f"Failed to stop Xray: {e}", "status": "error"}
    
    def restart_xray(self) -> Dict:
        """Restart the Xray process."""
        self.stop_xray()
        time.sleep(0.5)
        return self.start_xray()
    
    def test_all_proxies(self, timeout: int = 5, workers: int = 20, attempts: int = 1) -> Dict[str, object]:
        """Test all active proxies, optionally retrying each proxy multiple times."""
        self._load_data()

        # Ensure Xray is running
        if not self._is_xray_running():
            raise RuntimeError("Xray is not running. Please start Xray first.")

        runtime_ports = set(self.get_runtime_proxy_ports())
        active_proxies = [
            proxy for proxy in self._data.get("proxies", [])
            if self.is_proxy_enabled(proxy) and int(proxy["port"]) in runtime_ports
        ]
        if not active_proxies:
            return {
                "results": [],
                "success_count": 0,
                "failed_count": 0,
                "attempts": max(1, attempts),
                "cooldown_candidates": [],
            }
        
        # Build proxy nodes and port mappings for tester
        proxy_nodes = self._build_proxy_nodes()
        
        from src.xray_prism.models import PortMapping
        mappings = []
        for node in proxy_nodes:
            local_port = getattr(node, '_local_port', None)
            if local_port:
                mappings.append(PortMapping(local_port=local_port, node=node))
        
        tester = ProxyTester(timeout=timeout, max_workers=workers)
        attempts = max(1, attempts)
        attempt_results = [tester.test_all(mappings) for _ in range(attempts)]

        aggregated: Dict[int, Dict[str, object]] = {
            proxy["port"]: {
                "node_id": proxy["node_id"],
                "name": proxy["node_name"],
                "port": proxy["port"],
                "failed_attempts": 0,
                "success_result": None,
                "last_error": None,
            }
            for proxy in active_proxies
        }

        for results in attempt_results:
            for result in results:
                item = aggregated.get(result.local_port)
                if not item:
                    continue
                if result.success:
                    item["success_result"] = result
                else:
                    item["failed_attempts"] = int(item["failed_attempts"]) + 1
                    item["last_error"] = result.error

        test_results = []
        cooldown_candidates = []
        for proxy in active_proxies:
            item = aggregated[proxy["port"]]
            success_result = item["success_result"]
            failed_attempts = int(item["failed_attempts"])

            if success_result is not None:
                proxy["test_status"] = "success"
                proxy["latency_ms"] = int(success_result.latency_ms) if success_result.latency_ms else None
                proxy["exit_ip"] = success_result.exit_ip
                proxy["exit_country"] = success_result.country
                proxy["exit_country_code"] = success_result.country_code
                error = None
            else:
                proxy["test_status"] = "failed"
                proxy["latency_ms"] = None
                proxy["exit_ip"] = None
                proxy["exit_country"] = None
                proxy["exit_country_code"] = None
                error = item["last_error"]

            test_results.append({
                "node_id": proxy["node_id"],
                "name": proxy["node_name"],
                "port": proxy["port"],
                "status": proxy["test_status"],
                "latency_ms": proxy["latency_ms"],
                "exit_ip": proxy["exit_ip"],
                "exit_country": proxy.get("exit_country"),
                "exit_country_code": proxy.get("exit_country_code"),
                "error": error,
                "failed_attempts": failed_attempts,
            })

            if failed_attempts >= attempts and proxy["test_status"] == "failed":
                cooldown_candidates.append({
                    "node_id": proxy["node_id"],
                    "name": proxy["node_name"],
                    "proxy_port": proxy["port"],
                    "failed_attempts": failed_attempts,
                    "error": error,
                })

        self._save_data()
        success_count = sum(1 for item in test_results if item["status"] == "success")
        failed_count = len(test_results) - success_count
        return {
            "results": test_results,
            "success_count": success_count,
            "failed_count": failed_count,
            "attempts": attempts,
            "cooldown_candidates": cooldown_candidates,
        }
    
    def test_single_proxy(self, port: int, timeout: int = 5) -> Optional[Dict]:
        """Test a single proxy by port."""
        self._load_data()
        
        proxy = next((p for p in self._data.get("proxies", []) if p["port"] == port), None)
        if not proxy:
            return None
        if not self.is_proxy_enabled(proxy):
            raise ValueError(f"Proxy on port {port} is dedupe-disabled")
        
        # Ensure Xray is running
        if not self._is_xray_running():
            raise RuntimeError("Xray is not running. Please start Xray first.")
        if port not in set(self.get_runtime_proxy_ports()):
            raise ValueError(f"Proxy on port {port} is not loaded into current Xray runtime")
        
        tester = ProxyTester(timeout=timeout, max_workers=1)
        result = tester.test_port(port, proxy["node_name"])
        
        if result.success:
            proxy["test_status"] = "success"
            proxy["latency_ms"] = int(result.latency_ms) if result.latency_ms else None
            proxy["exit_ip"] = result.exit_ip
            proxy["exit_country"] = result.country
            proxy["exit_country_code"] = result.country_code
        else:
            proxy["test_status"] = "failed"
            proxy["latency_ms"] = None
            proxy["exit_ip"] = None
            proxy["exit_country"] = None
            proxy["exit_country_code"] = None
        
        self._save_data()
        
        return {
            "node_id": proxy["node_id"],
            "name": proxy["node_name"],
            "port": proxy["port"],
            "status": proxy["test_status"],
            "latency_ms": proxy["latency_ms"],
            "exit_ip": proxy["exit_ip"],
            "exit_country": proxy.get("exit_country"),
            "exit_country_code": proxy.get("exit_country_code"),
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
