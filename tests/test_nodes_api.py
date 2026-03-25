"""
API tests for node list enrichment and node testing workflow contracts.
"""
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.main import app


class _FakeSubscriptionService:
    def get_subscription(self, sub_id: str):
        return {"id": sub_id, "name": "demo", "url": "https://example.com"}

    def get_nodes_by_subscription(self, sub_id: str):
        return [{
            "id": "node_1",
            "subscription_id": sub_id,
            "name": "HK-01",
            "protocol": "trojan",
            "address": "demo.example.com",
            "port": 443,
            "password": "secret",
            "network": "tcp",
            "tls": True,
            "test_status": "pending",
            "latency_ms": None,
            "exit_ip": None,
            "exit_country": None,
            "in_proxy_pool": True,
            "proxy_port": 10022,
        }]


class _FakeNodeTestService:
    def __init__(self):
        self.calls = []
        self.jobs = {
            "job_demo": {
                "job_id": "job_demo",
                "status": "running",
                "total": 2,
                "completed_count": 1,
                "success_count": 1,
                "failed_count": 0,
                "progress_percent": 33,
                "active_target": "http://ip-api.com/json",
                "target_index": 1,
                "target_total": 3,
                "current_target_completed": 1,
                "current_target_total": 2,
                "note": "目标 1/3 已检测 1/2",
                "test_profile": "multi_target",
                "results": [],
                "error": None,
            }
        }

    def test_nodes(self, node_ids, timeout=5, test_profile="multi_target"):
        self.calls.append({
            "node_ids": list(node_ids),
            "timeout": timeout,
            "test_profile": test_profile,
        })
        return {
            "results": [
                {
                    "node_id": node_ids[0],
                    "name": "HK-01",
                    "status": "success",
                    "latency_ms": 240,
                    "exit_ip": "203.0.113.2",
                    "successful_target": "http://ip-api.com/json",
                },
                {
                    "node_id": node_ids[-1],
                    "name": "JP-02",
                    "status": "failed",
                    "error": "all targets failed",
                    "tested_target": "https://api.ipify.org?format=json",
                },
            ],
            "success_count": 1,
            "failed_count": 1,
            "test_profile": test_profile,
        }

    def start_test_job(self, node_ids, timeout=5, test_profile="multi_target"):
        self.calls.append({
            "job_node_ids": list(node_ids),
            "job_timeout": timeout,
            "job_test_profile": test_profile,
        })
        return self.jobs["job_demo"]

    def get_test_job(self, job_id):
        return self.jobs.get(job_id)


class TestNodesApi(unittest.TestCase):
    """Validate node-facing API behavior required by the frontend flow."""

    def setUp(self):
        self.client = TestClient(app)

    def test_list_subscription_nodes_exposes_proxy_pool_fields(self):
        fake_service = _FakeSubscriptionService()
        fake_proxy_service = MagicMock()
        fake_proxy_service.get_all_proxies.return_value = [
            {"node_id": "node_1", "port": 10022}
        ]

        with patch("api.routes.subscriptions.get_subscription_service", return_value=fake_service), \
             patch("api.routes.subscriptions.get_proxy_service", return_value=fake_proxy_service):
            response = self.client.get("/api/subscriptions/sub_demo/nodes")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertIn("group_id", payload["nodes"][0])
        self.assertIn("group_type", payload["nodes"][0])
        self.assertIn("in_proxy_pool", payload["nodes"][0])
        self.assertIn("proxy_port", payload["nodes"][0])
        self.assertIn("group_id", payload["nodes"][0])
        self.assertIn("group_type", payload["nodes"][0])
        self.assertIn("subscription_id", payload["nodes"][0])
        self.assertIn("runtime_supported", payload["nodes"][0])
        self.assertIn("runtime_support_reason", payload["nodes"][0])
        self.assertEqual(payload["nodes"][0]["group_type"], "subscription")
        self.assertEqual(payload["nodes"][0]["group_id"], "sub_demo")
        self.assertTrue(payload["nodes"][0]["runtime_supported"])
        self.assertIsInstance(payload["nodes"][0]["in_proxy_pool"], bool)
        self.assertTrue(
            payload["nodes"][0]["proxy_port"] is None or isinstance(payload["nodes"][0]["proxy_port"], int)
        )

    def test_list_subscription_nodes_marks_plugin_shadowsocks_as_runtime_unsupported(self):
        fake_service = MagicMock()
        fake_service.get_subscription.return_value = {"id": "sub_demo", "name": "demo", "url": "https://example.com"}
        fake_service.get_nodes_by_subscription.return_value = [{
            "id": "node_ss_plugin",
            "subscription_id": "sub_demo",
            "name": "SS-Plugin",
            "protocol": "shadowsocks",
            "address": "ss.example.com",
            "port": 8388,
            "password": "pass",
            "security": "aes-128-gcm",
            "ss_plugin": "v2ray-plugin",
            "ss_plugin_opts": "mode=websocket",
            "test_status": "pending",
        }]
        fake_proxy_service = MagicMock()
        fake_proxy_service.get_all_proxies.return_value = []

        with patch("api.routes.subscriptions.get_subscription_service", return_value=fake_service), \
             patch("api.routes.subscriptions.get_proxy_service", return_value=fake_proxy_service):
            response = self.client.get("/api/subscriptions/sub_demo/nodes")

        self.assertEqual(response.status_code, 200)
        node = response.json()["nodes"][0]
        self.assertFalse(node["runtime_supported"])
        self.assertIn("Shadowsocks plugin", node["runtime_support_reason"])

    def test_test_nodes_defaults_to_multi_target_and_does_not_touch_main_runner(self):
        fake_test_service = _FakeNodeTestService()
        fake_proxy_service = MagicMock()
        fake_proxy_service._runner = MagicMock()

        with patch("api.routes.nodes.get_node_test_service", return_value=fake_test_service, create=True), \
             patch("api.routes.nodes.get_proxy_service", return_value=fake_proxy_service, create=True):
            response = self.client.post("/api/nodes/test", json={
                "node_ids": ["node_1", "node_2"],
                "timeout": 7,
            })

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["success_count"], 1)
        self.assertEqual(payload["failed_count"], 1)
        self.assertEqual(payload["test_profile"], "multi_target")
        self.assertEqual(len(payload["results"]), 2)
        self.assertEqual(payload["results"][0]["status"], "success")
        self.assertEqual(payload["results"][1]["status"], "failed")

        self.assertEqual(len(fake_test_service.calls), 1)
        self.assertEqual(fake_test_service.calls[0]["node_ids"], ["node_1", "node_2"])
        self.assertEqual(fake_test_service.calls[0]["timeout"], 7)
        self.assertEqual(fake_test_service.calls[0]["test_profile"], "multi_target")
        fake_proxy_service._runner.stop.assert_not_called()
        fake_proxy_service._runner.start.assert_not_called()

    def test_node_test_job_endpoints_expose_progress_contract(self):
        fake_test_service = _FakeNodeTestService()

        with patch("api.routes.nodes.get_node_test_service", return_value=fake_test_service, create=True):
            start_response = self.client.post("/api/nodes/test-jobs", json={
                "node_ids": ["node_1", "node_2"],
                "timeout": 5,
            })
            progress_response = self.client.get("/api/nodes/test-jobs/job_demo")

        self.assertEqual(start_response.status_code, 200)
        self.assertEqual(progress_response.status_code, 200)

        started_payload = start_response.json()
        progress_payload = progress_response.json()

        self.assertEqual(started_payload["job_id"], "job_demo")
        self.assertEqual(progress_payload["status"], "running")
        self.assertEqual(progress_payload["progress_percent"], 33)
        self.assertEqual(progress_payload["active_target"], "http://ip-api.com/json")
        self.assertEqual(progress_payload["target_index"], 1)
        self.assertEqual(progress_payload["target_total"], 3)
        self.assertEqual(progress_payload["current_target_completed"], 1)
        self.assertEqual(progress_payload["current_target_total"], 2)


if __name__ == "__main__":
    unittest.main()
