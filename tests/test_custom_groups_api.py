"""
API tests for custom group endpoints.
"""
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app


class _FakeCustomGroupService:
    def __init__(self):
        self.groups = {
            "grp_demo": {
                "id": "grp_demo",
                "name": "Favorites",
                "group_type": "custom",
                "node_count": 1,
                "created_at": "2026-03-20T10:00:00",
                "updated_at": "2026-03-20T10:05:00",
            }
        }
        self.nodes = {
            "cnode_grp_demo_0001": {
                "id": "cnode_grp_demo_0001",
                "group_id": "grp_demo",
                "name": "HK-01",
                "protocol": "trojan",
                "address": "hk.example.com",
                "port": 443,
                "test_status": "pending",
                "latency_ms": None,
                "exit_ip": None,
                "exit_country": None,
            }
        }

    def get_all_groups(self):
        return list(self.groups.values())

    def create_group(self, name: str):
        name = name.strip()
        if not name:
            raise ValueError("分组名称不能为空")
        created = {
            "id": "grp_new",
            "name": name,
            "group_type": "custom",
            "node_count": 0,
            "created_at": "2026-03-20T11:00:00",
            "updated_at": "2026-03-20T11:00:00",
        }
        self.groups["grp_new"] = created
        return created

    def rename_group(self, group_id: str, name: str):
        name = name.strip()
        if not name:
            raise ValueError("分组名称不能为空")
        if group_id not in self.groups:
            return None
        self.groups[group_id]["name"] = name
        return self.groups[group_id]

    def delete_group(self, group_id: str):
        return self.groups.pop(group_id, None) is not None

    def get_group(self, group_id: str):
        return self.groups.get(group_id)

    def get_nodes_by_group(self, group_id: str):
        return [node for node in self.nodes.values() if node.get("group_id") == group_id]

    def import_nodes(self, group_id: str, content: str):
        if group_id not in self.groups:
            raise ValueError("not found")
        if not content.strip():
            raise ValueError("empty")
        parsed = 2
        imported = 1
        if "ssr://only" in content:
            parsed = 1
            imported = 1
        if "trojan://demo\nssr://demo" in content:
            parsed = 2
            imported = 2
        return {
            "imported_count": imported,
            "skipped_duplicates": 0,
            "total_parsed": parsed,
            "ignored_unsupported_count": 0,
        }

    def get_nodes_by_ids(self, node_ids):
        return [self.nodes[node_id] for node_id in node_ids if node_id in self.nodes]

    def copy_nodes(self, group_id, source_nodes, missing_node_ids=None):
        if group_id not in self.groups:
            raise ValueError("not found")
        return {
            "copied_count": len(source_nodes),
            "skipped_duplicates": 0,
            "total_requested": len(source_nodes) + len(missing_node_ids or []),
            "missing_node_ids": list(missing_node_ids or []),
        }

    def delete_group_node(self, group_id: str, node_id: str):
        node = self.nodes.get(node_id)
        if not node or node.get("group_id") != group_id:
            return False
        del self.nodes[node_id]
        return True


class _FakeSubscriptionService:
    def get_nodes_by_ids(self, node_ids):
        nodes = []
        for node_id in node_ids:
            if node_id == "node_sub_0001":
                nodes.append({
                    "id": node_id,
                    "subscription_id": "sub_demo",
                    "name": "JP-01",
                    "protocol": "trojan",
                    "address": "jp.example.com",
                    "port": 443,
                })
        return nodes


class TestCustomGroupsApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_list_custom_groups(self):
        fake_service = _FakeCustomGroupService()
        with patch("api.routes.custom_groups.get_custom_group_service", return_value=fake_service):
            response = self.client.get("/api/custom-groups")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["groups"][0]["group_type"], "custom")

    def test_list_custom_group_nodes_enriches_proxy_pool_fields(self):
        fake_service = _FakeCustomGroupService()
        fake_proxy_service = MagicMock()
        fake_proxy_service.get_all_proxies.return_value = [
            {"node_id": "cnode_grp_demo_0001", "port": 10088}
        ]
        with patch("api.routes.custom_groups.get_custom_group_service", return_value=fake_service), \
             patch("api.routes.custom_groups.get_proxy_service", return_value=fake_proxy_service):
            response = self.client.get("/api/custom-groups/grp_demo/nodes")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        node = payload["nodes"][0]
        self.assertEqual(node["group_type"], "custom")
        self.assertEqual(node["group_id"], "grp_demo")
        self.assertTrue(node["in_proxy_pool"])
        self.assertEqual(node["proxy_port"], 10088)

    def test_copy_nodes_to_custom_group(self):
        fake_custom_service = _FakeCustomGroupService()
        fake_subscription_service = _FakeSubscriptionService()
        with patch("api.routes.custom_groups.get_custom_group_service", return_value=fake_custom_service), \
             patch("api.routes.custom_groups.get_subscription_service", return_value=fake_subscription_service):
            response = self.client.post(
                "/api/custom-groups/grp_demo/nodes/copy",
                json={"source_node_ids": ["node_sub_0001", "missing_node"]},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["copied_count"], 1)
        self.assertEqual(payload["missing_node_ids"], ["missing_node"])

    def test_create_custom_group_rejects_blank_name(self):
        fake_service = _FakeCustomGroupService()
        with patch("api.routes.custom_groups.get_custom_group_service", return_value=fake_service):
            response = self.client.post(
                "/api/custom-groups",
                json={"name": "   "},
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("不能为空", response.json()["detail"])

    def test_import_custom_group_nodes_returns_ignored_unsupported_count(self):
        fake_service = _FakeCustomGroupService()
        with patch("api.routes.custom_groups.get_custom_group_service", return_value=fake_service):
            response = self.client.post(
                "/api/custom-groups/grp_demo/nodes/import",
                json={"content": "trojan://demo\nssr://demo"},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["imported_count"], 2)
        self.assertEqual(payload["ignored_unsupported_count"], 0)

    def test_import_custom_group_nodes_accepts_ssr_only_content(self):
        fake_service = _FakeCustomGroupService()
        with patch("api.routes.custom_groups.get_custom_group_service", return_value=fake_service):
            response = self.client.post(
                "/api/custom-groups/grp_demo/nodes/import",
                json={"content": "ssr://only"},
            )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["imported_count"], 1)
        self.assertEqual(payload["total_parsed"], 1)


if __name__ == "__main__":
    unittest.main()
