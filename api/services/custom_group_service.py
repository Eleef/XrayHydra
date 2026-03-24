"""
Custom group management service.
Handles CRUD operations for manual node groups and their snapshot nodes.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent

from src.xray_prism.models import ProxyNode
from src.xray_prism.parser import parse_subscription

logger = logging.getLogger(__name__)


NODE_SNAPSHOT_FIELDS = (
    "name",
    "protocol",
    "address",
    "port",
    "uuid",
    "password",
    "security",
    "network",
    "tls",
    "sni",
    "fingerprint",
    "allow_insecure",
    "ws_path",
    "ws_host",
    "alter_id",
    "flow",
    "grpc_service_name",
    "public_key",
    "short_id",
    "hy_obfs",
    "hy_obfs_password",
    "hy_alpn",
    "ss_plugin",
    "ss_plugin_opts",
    "ss_uot",
    "ss_uot_version",
    "test_status",
    "latency_ms",
    "exit_ip",
    "exit_country",
)

SEMANTIC_DEDUPE_FIELDS = (
    "protocol",
    "address",
    "port",
    "uuid",
    "password",
    "security",
    "network",
    "tls",
    "sni",
    "fingerprint",
    "allow_insecure",
    "ws_path",
    "ws_host",
    "alter_id",
    "flow",
    "grpc_service_name",
    "public_key",
    "short_id",
    "hy_obfs",
    "hy_obfs_password",
    "hy_alpn",
    "ss_plugin",
    "ss_plugin_opts",
    "ss_uot",
    "ss_uot_version",
)


class CustomGroupService:
    """Service for managing custom node groups."""

    DATA_DIR = PROJECT_ROOT / "data"
    CUSTOM_GROUPS_FILE = DATA_DIR / "custom_groups.json"

    def __init__(self):
        self._ensure_data_dir()
        self._load_data()

    def _ensure_data_dir(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not self.CUSTOM_GROUPS_FILE.exists():
            self._save_data({"groups": {}, "nodes": {}})

    def _load_data(self) -> Dict:
        if self.CUSTOM_GROUPS_FILE.exists():
            with open(self.CUSTOM_GROUPS_FILE, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {"groups": {}, "nodes": {}}
        normalized_nodes = {
            node_id: self._normalize_node_record(node_data)
            for node_id, node_data in self._data.get("nodes", {}).items()
        }
        normalized_groups = {
            group_id: self._normalize_group_record(group_data)
            for group_id, group_data in self._data.get("groups", {}).items()
        }
        if (
            normalized_nodes != self._data.get("nodes", {})
            or normalized_groups != self._data.get("groups", {})
        ):
            self._data["nodes"] = normalized_nodes
            self._data["groups"] = normalized_groups
            self._save_data()
        return self._data

    def _save_data(self, data: Optional[Dict] = None):
        if data:
            self._data = data
        with open(self.CUSTOM_GROUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2, default=str)

    @staticmethod
    def _normalize_group_record(group_data: Dict) -> Dict:
        normalized = dict(group_data)
        now = datetime.now().isoformat()
        normalized.setdefault("created_at", now)
        normalized.setdefault("updated_at", normalized["created_at"])
        return normalized

    @staticmethod
    def _normalize_node_record(node_data: Dict) -> Dict:
        normalized = dict(node_data)
        normalized["test_status"] = str(normalized.get("test_status") or "pending")
        normalized.setdefault("group_type", "custom")
        return normalized

    @staticmethod
    def _semantic_key(node_data: Dict) -> tuple:
        return tuple(node_data.get(field) for field in SEMANTIC_DEDUPE_FIELDS)

    @staticmethod
    def _normalize_group_name(name: str) -> str:
        normalized = (name or "").strip()
        if not normalized:
            raise ValueError("分组名称不能为空")
        return normalized

    @staticmethod
    def _snapshot_from_proxy_node(node: ProxyNode) -> Dict:
        return {
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
            "fingerprint": node.fingerprint,
            "allow_insecure": node.allow_insecure,
            "ws_path": node.path,
            "ws_host": node.host,
            "alter_id": node.alter_id,
            "flow": node.flow,
            "grpc_service_name": node.service_name,
            "public_key": node.public_key,
            "short_id": node.short_id,
            "hy_obfs": node.hy_obfs,
            "hy_obfs_password": node.hy_obfs_password,
            "hy_alpn": node.hy_alpn,
            "ss_plugin": node.ss_plugin,
            "ss_plugin_opts": node.ss_plugin_opts,
            "ss_uot": node.ss_uot,
            "ss_uot_version": node.ss_uot_version,
            "test_status": "pending",
            "latency_ms": None,
            "exit_ip": None,
            "exit_country": None,
        }

    @staticmethod
    def _snapshot_from_node_dict(node: Dict) -> Dict:
        snapshot = {}
        for field in NODE_SNAPSHOT_FIELDS:
            snapshot[field] = node.get(field)
        snapshot["test_status"] = snapshot.get("test_status") or "pending"
        snapshot["security"] = snapshot.get("security") or "auto"
        snapshot["network"] = snapshot.get("network") or "tcp"
        snapshot["tls"] = bool(snapshot.get("tls", False))
        snapshot["allow_insecure"] = bool(snapshot.get("allow_insecure", False))
        snapshot["port"] = int(snapshot.get("port") or 0)
        snapshot["alter_id"] = int(snapshot.get("alter_id") or 0)
        return snapshot

    def _detect_nodes_for_import(self, content: str) -> tuple[List[ProxyNode], int]:
        parsed_nodes = parse_subscription(content)
        if not parsed_nodes:
            raw_nodes = parse_subscription(content, filter_nodes=False)
            if raw_nodes:
                raise ValueError("导入内容仅包含元数据节点")
            raise ValueError("No nodes found in import content")
        return parsed_nodes, 0

    def _group_node_count(self, group_id: str) -> int:
        return len([
            node_data for node_data in self._data.get("nodes", {}).values()
            if node_data.get("group_id") == group_id
        ])

    def get_all_groups(self) -> List[Dict]:
        self._load_data()
        groups = []
        for group_id, group_data in self._data.get("groups", {}).items():
            groups.append({
                "id": group_id,
                "name": group_data["name"],
                "group_type": "custom",
                "node_count": self._group_node_count(group_id),
                "created_at": group_data.get("created_at"),
                "updated_at": group_data.get("updated_at"),
            })
        groups.sort(
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )
        return groups

    def get_group(self, group_id: str) -> Optional[Dict]:
        self._load_data()
        group_data = self._data.get("groups", {}).get(group_id)
        if not group_data:
            return None
        return {
            "id": group_id,
            "name": group_data["name"],
            "group_type": "custom",
            "node_count": self._group_node_count(group_id),
            "created_at": group_data.get("created_at"),
            "updated_at": group_data.get("updated_at"),
        }

    def create_group(self, name: str) -> Dict:
        self._load_data()
        normalized_name = self._normalize_group_name(name)
        group_id = f"grp_{uuid.uuid4().hex[:8]}"
        now = datetime.now().isoformat()
        self._data["groups"][group_id] = {
            "name": normalized_name,
            "created_at": now,
            "updated_at": now,
        }
        self._save_data()
        return self.get_group(group_id)

    def rename_group(self, group_id: str, name: str) -> Optional[Dict]:
        self._load_data()
        group_data = self._data.get("groups", {}).get(group_id)
        if not group_data:
            return None
        group_data["name"] = self._normalize_group_name(name)
        group_data["updated_at"] = datetime.now().isoformat()
        self._save_data()
        return self.get_group(group_id)

    def delete_group(self, group_id: str) -> bool:
        self._load_data()
        if group_id not in self._data.get("groups", {}):
            return False
        del self._data["groups"][group_id]
        nodes_to_remove = [
            node_id for node_id, node_data in self._data.get("nodes", {}).items()
            if node_data.get("group_id") == group_id
        ]
        for node_id in nodes_to_remove:
            del self._data["nodes"][node_id]
        self._save_data()
        return True

    def get_nodes_by_group(self, group_id: str) -> List[Dict]:
        self._load_data()
        nodes = []
        for node_id, node_data in self._data.get("nodes", {}).items():
            if node_data.get("group_id") == group_id:
                nodes.append({"id": node_id, **node_data})
        return nodes

    def get_node(self, node_id: str) -> Optional[Dict]:
        self._load_data()
        node_data = self._data.get("nodes", {}).get(node_id)
        if not node_data:
            return None
        return {"id": node_id, **node_data}

    def get_nodes_by_ids(self, node_ids: List[str]) -> List[Dict]:
        self._load_data()
        nodes = []
        for node_id in node_ids:
            node_data = self._data.get("nodes", {}).get(node_id)
            if node_data:
                nodes.append({"id": node_id, **node_data})
        return nodes

    def _add_node_snapshots(self, group_id: str, node_snapshots: List[Dict]) -> Dict:
        self._load_data()
        group_data = self._data.get("groups", {}).get(group_id)
        if not group_data:
            raise ValueError(f"Custom group {group_id} not found")

        existing_keys = {
            self._semantic_key(node_data)
            for node_data in self._data.get("nodes", {}).values()
            if node_data.get("group_id") == group_id
        }

        imported_count = 0
        skipped_duplicates = 0
        for snapshot in node_snapshots:
            semantic_key = self._semantic_key(snapshot)
            if semantic_key in existing_keys:
                skipped_duplicates += 1
                continue

            node_id = f"cnode_{group_id}_{uuid.uuid4().hex[:8]}"
            self._data["nodes"][node_id] = {
                "group_id": group_id,
                "group_type": "custom",
                **snapshot,
            }
            existing_keys.add(semantic_key)
            imported_count += 1

        group_data["updated_at"] = datetime.now().isoformat()
        self._save_data()
        return {
            "imported_count": imported_count,
            "skipped_duplicates": skipped_duplicates,
        }

    def import_nodes(self, group_id: str, content: str) -> Dict:
        parsed_nodes, ignored_unsupported = self._detect_nodes_for_import(content)
        snapshots = [self._snapshot_from_proxy_node(node) for node in parsed_nodes]
        result = self._add_node_snapshots(group_id, snapshots)
        result["ignored_unsupported_count"] = ignored_unsupported
        result["total_parsed"] = len(parsed_nodes) + ignored_unsupported
        return result

    def copy_nodes(
        self,
        group_id: str,
        source_nodes: List[Dict],
        missing_node_ids: Optional[List[str]] = None,
    ) -> Dict:
        snapshots = [self._snapshot_from_node_dict(node) for node in source_nodes]
        result = self._add_node_snapshots(group_id, snapshots)
        result["copied_count"] = result.pop("imported_count")
        result["total_requested"] = len(source_nodes) + len(missing_node_ids or [])
        result["missing_node_ids"] = list(missing_node_ids or [])
        return result

    def delete_node(self, group_id: str, node_id: str) -> bool:
        self._load_data()
        node_data = self._data.get("nodes", {}).get(node_id)
        if not node_data or node_data.get("group_id") != group_id:
            return False
        del self._data["nodes"][node_id]
        group_data = self._data.get("groups", {}).get(group_id)
        if group_data:
            group_data["updated_at"] = datetime.now().isoformat()
        self._save_data()
        return True

    def delete_group_node(self, group_id: str, node_id: str) -> bool:
        return self.delete_node(group_id, node_id)

    def update_node_test_result(
        self,
        node_id: str,
        status: str,
        latency_ms: Optional[int] = None,
        exit_ip: Optional[str] = None,
        exit_country: Optional[str] = None,
    ) -> None:
        self._load_data()
        if node_id not in self._data.get("nodes", {}):
            return
        node_record = self._data["nodes"][node_id]
        node_record["test_status"] = status
        node_record["latency_ms"] = latency_ms
        node_record["exit_ip"] = exit_ip
        node_record["exit_country"] = exit_country
        self._save_data()


_custom_group_service: Optional[CustomGroupService] = None


def get_custom_group_service() -> CustomGroupService:
    global _custom_group_service
    if _custom_group_service is None:
        _custom_group_service = CustomGroupService()
    return _custom_group_service
