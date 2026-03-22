"""
Subscription management service.
Handles CRUD operations for subscriptions and their nodes.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.xray_prism.fetcher import fetch_subscription
from src.xray_prism.parser import parse_subscription
from src.xray_prism.models import ProxyNode, is_runtime_supported_protocol

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Service for managing subscriptions and their nodes."""
    
    DATA_DIR = PROJECT_ROOT / "data"
    SUBSCRIPTIONS_FILE = DATA_DIR / "subscriptions.json"
    
    def __init__(self):
        """Initialize the subscription service."""
        self._ensure_data_dir()
        self._load_data()
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.SUBSCRIPTIONS_FILE.exists():
            self._save_data({"subscriptions": {}, "nodes": {}})
    
    def _load_data(self) -> Dict:
        """Load data from JSON file."""
        if self.SUBSCRIPTIONS_FILE.exists():
            with open(self.SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        else:
            self._data = {"subscriptions": {}, "nodes": {}}
        normalized_nodes = {
            node_id: self._normalize_node_record(node_data)
            for node_id, node_data in self._data.get("nodes", {}).items()
        }
        if normalized_nodes != self._data.get("nodes", {}):
            self._data["nodes"] = normalized_nodes
            self._save_data()
        return self._data
    
    def _save_data(self, data: Optional[Dict] = None):
        """Save data to JSON file."""
        if data:
            self._data = data
        with open(self.SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)

    def _normalize_node_record(self, node_data: Dict) -> Dict:
        """Normalize persisted node records."""
        normalized = dict(node_data)
        normalized.pop("runtime_supported", None)
        normalized.pop("runtime_support_reason", None)
        return normalized
    
    def get_all_subscriptions(self) -> List[Dict]:
        """Get all subscriptions."""
        self._load_data()
        subscriptions = []
        for sub_id, sub_data in self._data.get("subscriptions", {}).items():
            # Count nodes for this subscription
            node_count = len([
                n for n in self._data.get("nodes", {}).values() 
                if n.get("subscription_id") == sub_id
            ])
            subscriptions.append({
                "id": sub_id,
                "name": sub_data["name"],
                "url": sub_data["url"],
                "node_count": node_count,
                "last_updated": sub_data.get("last_updated"),
                "created_at": sub_data.get("created_at")
            })
        return subscriptions
    
    def get_subscription(self, sub_id: str) -> Optional[Dict]:
        """Get a single subscription by ID."""
        self._load_data()
        sub_data = self._data.get("subscriptions", {}).get(sub_id)
        if not sub_data:
            return None
        
        node_count = len([
            n for n in self._data.get("nodes", {}).values() 
            if n.get("subscription_id") == sub_id
        ])
        
        return {
            "id": sub_id,
            "name": sub_data["name"],
            "url": sub_data["url"],
            "node_count": node_count,
            "last_updated": sub_data.get("last_updated"),
            "created_at": sub_data.get("created_at")
        }
    
    def create_subscription(self, name: str, url: str) -> Dict:
        """Create a new subscription and fetch its nodes."""
        self._load_data()
        
        sub_id = f"sub_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()

        nodes_data = self._fetch_subscription_nodes_data(sub_id, url)

        self._data["subscriptions"][sub_id] = {
            "name": name,
            "url": url,
            "created_at": now,
            "last_updated": now
        }
        self._data["nodes"].update(nodes_data)
        self._save_data()
        
        return self.get_subscription(sub_id)
    
    def delete_subscription(self, sub_id: str) -> bool:
        """Delete a subscription and its nodes."""
        self._load_data()
        
        if sub_id not in self._data.get("subscriptions", {}):
            return False
        
        # Remove subscription
        del self._data["subscriptions"][sub_id]
        
        # Remove associated nodes
        nodes_to_remove = [
            node_id for node_id, node_data in self._data.get("nodes", {}).items()
            if node_data.get("subscription_id") == sub_id
        ]
        for node_id in nodes_to_remove:
            del self._data["nodes"][node_id]
        
        self._save_data()
        return True
    
    def refresh_subscription(self, sub_id: str) -> Optional[Dict]:
        """Refresh a subscription's nodes."""
        self._load_data()
        
        sub_data = self._data.get("subscriptions", {}).get(sub_id)
        if not sub_data:
            return None
        
        self._refresh_subscription_nodes(sub_id, sub_data["url"])
        return self.get_subscription(sub_id)
    
    def _fetch_subscription_nodes_data(self, sub_id: str, url: str) -> Dict[str, Dict]:
        """Fetch and parse subscription nodes without mutating persisted state."""
        # Fetch subscription content
        content = fetch_subscription(url=url)
        if not content:
            raise ValueError("Failed to fetch subscription content")

        parsed_nodes: List[ProxyNode] = parse_subscription(content)
        if not parsed_nodes:
            raw_nodes: List[ProxyNode] = parse_subscription(content, filter_nodes=False)
            if raw_nodes:
                detected_protocols = sorted({node.protocol.value for node in raw_nodes})
                unsupported_protocols = sorted({
                    node.protocol.value
                    for node in raw_nodes
                    if not is_runtime_supported_protocol(node.protocol)
                })
                if unsupported_protocols and set(unsupported_protocols) == set(detected_protocols):
                    raise ValueError(
                        f"订阅仅包含当前 Xray 不支持的协议: {', '.join(unsupported_protocols)}"
                    )
                raise ValueError("订阅仅包含元数据或当前不支持的节点")
            raise ValueError("No nodes found in subscription")

        nodes = [node for node in parsed_nodes if is_runtime_supported_protocol(node.protocol)]
        if not nodes:
            unsupported_protocols = sorted({node.protocol.value for node in parsed_nodes})
            raise ValueError(
                f"订阅仅包含当前 Xray 不支持的协议: {', '.join(unsupported_protocols)}"
            )
        if len(nodes) < len(parsed_nodes):
            ignored_protocols = sorted({
                node.protocol.value
                for node in parsed_nodes
                if not is_runtime_supported_protocol(node.protocol)
            })
            logger.info(
                "忽略订阅 %s 中当前 Xray 不支持的协议节点: %s",
                sub_id,
                ", ".join(ignored_protocols),
            )

        nodes_data: Dict[str, Dict] = {}
        for idx, node in enumerate(nodes):
            node_id = f"node_{sub_id}_{idx:04d}"
            nodes_data[node_id] = {
                "subscription_id": sub_id,
                "name": node.name,
                "protocol": node.protocol.value,
                "address": node.address,
                "port": node.port,
                "uuid": node.uuid,
                "password": node.password,
                "security": node.security,
                "network": node.network.value,
                "tls": node.tls,
                "sni": node.sni,
                "allow_insecure": node.allow_insecure,
                "ws_path": node.path,  # ProxyNode uses 'path'
                "ws_host": node.host,  # ProxyNode uses 'host'
                "alter_id": node.alter_id,
                "flow": node.flow,
                "grpc_service_name": node.service_name,  # ProxyNode uses 'service_name'
                "fingerprint": node.fingerprint,
                "public_key": node.public_key,
                "short_id": node.short_id,
                "test_status": "pending",
                "latency_ms": None,
                "exit_ip": None,
                "exit_country": None
            }

        return nodes_data

    def _refresh_subscription_nodes(self, sub_id: str, url: str):
        """Fetch and update nodes for a subscription."""
        nodes_data = self._fetch_subscription_nodes_data(sub_id, url)

        # Remove old nodes for this subscription only after the new payload is ready.
        nodes_to_remove = [
            node_id for node_id, node_data in self._data.get("nodes", {}).items()
            if node_data.get("subscription_id") == sub_id
        ]
        for node_id in nodes_to_remove:
            del self._data["nodes"][node_id]

        self._data["nodes"].update(nodes_data)
        self._data["subscriptions"][sub_id]["last_updated"] = datetime.now().isoformat()
        self._save_data()
    
    def get_nodes_by_subscription(self, sub_id: str) -> List[Dict]:
        """Get all nodes for a subscription."""
        self._load_data()
        
        nodes = []
        for node_id, node_data in self._data.get("nodes", {}).items():
            if node_data.get("subscription_id") == sub_id:
                nodes.append({
                    "id": node_id,
                    **node_data
                })
        return nodes
    
    def get_node(self, node_id: str) -> Optional[Dict]:
        """Get a single node by ID."""
        self._load_data()
        node_data = self._data.get("nodes", {}).get(node_id)
        if not node_data:
            return None
        return {"id": node_id, **node_data}
    
    def get_nodes_by_ids(self, node_ids: List[str]) -> List[Dict]:
        """Get multiple nodes by their IDs."""
        self._load_data()
        nodes = []
        for node_id in node_ids:
            node_data = self._data.get("nodes", {}).get(node_id)
            if node_data:
                nodes.append({"id": node_id, **node_data})
        return nodes
    
    def update_node_test_result(self, node_id: str, status: str, 
                                 latency_ms: Optional[int] = None,
                                 exit_ip: Optional[str] = None,
                                 exit_country: Optional[str] = None):
        """Update a node's test result."""
        self._load_data()
        
        if node_id in self._data.get("nodes", {}):
            self._data["nodes"][node_id]["test_status"] = status
            self._data["nodes"][node_id]["latency_ms"] = latency_ms
            self._data["nodes"][node_id]["exit_ip"] = exit_ip
            self._data["nodes"][node_id]["exit_country"] = exit_country
            self._save_data()


# Singleton instance
_subscription_service: Optional[SubscriptionService] = None

def get_subscription_service() -> SubscriptionService:
    """Get the singleton subscription service instance."""
    global _subscription_service
    if _subscription_service is None:
        _subscription_service = SubscriptionService()
    return _subscription_service
