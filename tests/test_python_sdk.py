"""
Tests for the generated Python SDK.
"""
import sys
import unittest
from typing import get_type_hints
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app


SDK_SRC = Path(__file__).resolve().parent.parent / "sdk" / "python" / "src"
if str(SDK_SRC) not in sys.path:
    sys.path.insert(0, str(SDK_SRC))

from xray_prism_sdk import XrayPrismClient, models  # noqa: E402


class TestPythonSdk(unittest.TestCase):
    """Smoke-test the generated SDK against the in-process FastAPI app."""

    def setUp(self):
        self.transport = TestClient(app)
        self.client = XrayPrismClient(base_url="", client=self.transport)

    def tearDown(self):
        self.client.close()

    def test_can_call_system_status(self):
        data = self.client.get_system_status()
        self.assertIn("xray_status", data)
        self.assertIn("subscription_count", data)

    def test_can_call_list_subscriptions(self):
        data = self.client.list_subscriptions()
        self.assertIn("subscriptions", data)
        self.assertIn("total", data)

    def test_can_call_lease_stats(self):
        data = self.client.get_lease_stats()
        self.assertIn("total_available_proxies", data)
        self.assertIn("workspaces", data)

    def test_can_call_lease_status_and_exposes_new_methods(self):
        data = self.client.get_lease_status()
        self.assertIn("workspaces", data)
        self.assertIn("active_leases", data)
        self.assertIn("cooldowns", data)
        self.assertTrue(hasattr(self.client, "set_manual_lease_cooldown"))
        self.assertTrue(hasattr(self.client, "recall_lease_cooldown"))
        self.assertTrue(hasattr(self.client, "apply_timed_lease_cooldown_batch"))
        self.assertTrue(hasattr(self.client, "reset_workspace_lease_state"))

    def test_sdk_exposes_node_test_contract(self):
        self.assertTrue(hasattr(models, "NodeTestRequest"))
        self.assertTrue(hasattr(models, "NodeBatchTestResponse"))
        self.assertTrue(hasattr(models, "NodeTestJobResponse"))
        self.assertTrue(hasattr(models, "NodeResponse"))
        self.assertTrue(hasattr(models, "CustomGroupResponse"))
        self.assertTrue(hasattr(models, "CustomGroupListResponse"))
        self.assertTrue(hasattr(models, "CustomGroupCreateRequest"))
        self.assertTrue(hasattr(models, "CustomGroupImportRequest"))

        node_test_hints = get_type_hints(XrayPrismClient.test_nodes, globalns=vars(sys.modules[XrayPrismClient.__module__]))
        start_job_hints = get_type_hints(XrayPrismClient.start_node_test_job, globalns=vars(sys.modules[XrayPrismClient.__module__]))
        get_job_hints = get_type_hints(XrayPrismClient.get_node_test_job, globalns=vars(sys.modules[XrayPrismClient.__module__]))
        get_node_hints = get_type_hints(XrayPrismClient.get_node, globalns=vars(sys.modules[XrayPrismClient.__module__]))
        list_custom_groups_hints = get_type_hints(XrayPrismClient.list_custom_groups, globalns=vars(sys.modules[XrayPrismClient.__module__]))
        create_custom_group_hints = get_type_hints(XrayPrismClient.create_custom_group, globalns=vars(sys.modules[XrayPrismClient.__module__]))

        self.assertIs(node_test_hints["return"], models.NodeBatchTestResponse)
        self.assertIs(start_job_hints["return"], models.NodeTestJobResponse)
        self.assertIs(get_job_hints["return"], models.NodeTestJobResponse)
        self.assertIs(get_node_hints["return"], models.NodeResponse)
        self.assertIs(list_custom_groups_hints["return"], models.CustomGroupListResponse)
        self.assertIs(create_custom_group_hints["return"], models.CustomGroupResponse)

        ts_models = (Path(__file__).resolve().parent.parent / "sdk" / "typescript" / "src" / "models.ts").read_text(encoding="utf-8")
        ts_client = (Path(__file__).resolve().parent.parent / "sdk" / "typescript" / "src" / "index.ts").read_text(encoding="utf-8")

        self.assertIn("export interface NodeTestRequest", ts_models)
        self.assertIn("export interface NodeBatchTestResponse", ts_models)
        self.assertIn("export interface NodeTestJobResponse", ts_models)
        self.assertIn("export interface CustomGroupResponse", ts_models)
        self.assertIn("export interface CustomGroupListResponse", ts_models)
        self.assertIn("in_proxy_pool", ts_models)
        self.assertIn("proxy_port", ts_models)
        self.assertIn("group_id", ts_models)
        self.assertIn("group_type", ts_models)
        self.assertIn("async test_nodes(payload: models.NodeTestRequest): Promise<models.NodeBatchTestResponse>", ts_client)
        self.assertIn("async start_node_test_job(payload: models.NodeTestRequest): Promise<models.NodeTestJobResponse>", ts_client)
        self.assertIn("async get_node_test_job(job_id: string): Promise<models.NodeTestJobResponse>", ts_client)
        self.assertIn("async list_custom_groups(): Promise<models.CustomGroupListResponse>", ts_client)
        self.assertIn("async create_custom_group(payload: models.CustomGroupCreateRequest): Promise<models.CustomGroupResponse>", ts_client)

    def test_sdk_exposes_custom_group_contract(self):
        self.assertTrue(hasattr(models, "CustomGroupCreateRequest"))
        self.assertTrue(hasattr(models, "CustomGroupRenameRequest"))
        self.assertTrue(hasattr(models, "CustomGroupImportRequest"))
        self.assertTrue(hasattr(models, "CustomGroupCopyNodesRequest"))
        self.assertTrue(hasattr(models, "CustomGroupResponse"))
        self.assertTrue(hasattr(models, "CustomGroupListResponse"))

        self.assertTrue(hasattr(self.client, "list_custom_groups"))
        self.assertTrue(hasattr(self.client, "create_custom_group"))
        self.assertTrue(hasattr(self.client, "rename_custom_group"))
        self.assertTrue(hasattr(self.client, "delete_custom_group"))
        self.assertTrue(hasattr(self.client, "list_custom_group_nodes"))
        self.assertTrue(hasattr(self.client, "import_custom_group_nodes"))
        self.assertTrue(hasattr(self.client, "copy_nodes_to_custom_group"))
        self.assertTrue(hasattr(self.client, "delete_custom_group_node"))

        ts_models = (Path(__file__).resolve().parent.parent / "sdk" / "typescript" / "src" / "models.ts").read_text(encoding="utf-8")
        ts_client = (Path(__file__).resolve().parent.parent / "sdk" / "typescript" / "src" / "index.ts").read_text(encoding="utf-8")

        self.assertIn("export interface CustomGroupCreateRequest", ts_models)
        self.assertIn("export interface CustomGroupRenameRequest", ts_models)
        self.assertIn("export interface CustomGroupImportRequest", ts_models)
        self.assertIn("export interface CustomGroupCopyNodesRequest", ts_models)
        self.assertIn("export interface CustomGroupResponse", ts_models)
        self.assertIn("async list_custom_groups()", ts_client)
        self.assertIn("async create_custom_group(payload: models.CustomGroupCreateRequest)", ts_client)
        self.assertIn("async list_custom_group_nodes(group_id: string)", ts_client)

    def test_sdk_exports_lease_response_models_and_return_types(self):
        self.assertTrue(hasattr(models, "LeaseAcquireResponse"))
        self.assertTrue(hasattr(models, "LeaseReleaseResponse"))
        self.assertTrue(hasattr(models, "LeaseStatusResponse"))
        self.assertTrue(hasattr(models, "LeaseStatsResponse"))

        acquire_hints = get_type_hints(XrayPrismClient.acquire_lease, globalns=vars(sys.modules[XrayPrismClient.__module__]))
        release_hints = get_type_hints(XrayPrismClient.release_lease, globalns=vars(sys.modules[XrayPrismClient.__module__]))
        status_hints = get_type_hints(XrayPrismClient.get_lease_status, globalns=vars(sys.modules[XrayPrismClient.__module__]))
        stats_hints = get_type_hints(XrayPrismClient.get_lease_stats, globalns=vars(sys.modules[XrayPrismClient.__module__]))

        self.assertIs(acquire_hints["return"], models.LeaseAcquireResponse)
        self.assertIs(release_hints["return"], models.LeaseReleaseResponse)
        self.assertIs(status_hints["return"], models.LeaseStatusResponse)
        self.assertIs(stats_hints["return"], models.LeaseStatsResponse)

    def test_typescript_sdk_emits_lease_response_models_and_return_types(self):
        ts_models = (Path(__file__).resolve().parent.parent / "sdk" / "typescript" / "src" / "models.ts").read_text(encoding="utf-8")
        ts_client = (Path(__file__).resolve().parent.parent / "sdk" / "typescript" / "src" / "index.ts").read_text(encoding="utf-8")

        self.assertIn("export interface LeaseAcquireResponse", ts_models)
        self.assertIn("export interface LeaseReleaseResponse", ts_models)
        self.assertIn("export interface LeaseStatusResponse", ts_models)
        self.assertIn("export interface LeaseStatsResponse", ts_models)
        self.assertIn("async acquire_lease(payload: models.LeaseAcquireRequest): Promise<models.LeaseAcquireResponse>", ts_client)
        self.assertIn("async release_lease(payload: models.LeaseReleaseRequest): Promise<models.LeaseReleaseResponse>", ts_client)
        self.assertIn("async get_lease_status(query: { workspace_id?: string | unknown } = {}): Promise<models.LeaseStatusResponse>", ts_client)
        self.assertIn("async get_lease_stats(): Promise<models.LeaseStatsResponse>", ts_client)


if __name__ == "__main__":
    unittest.main()
