"""
Contract tests for generated OpenAPI output.
"""
import unittest

from fastapi.testclient import TestClient

from api.main import app


class TestOpenAPIContract(unittest.TestCase):
    """Ensure client-facing OpenAPI stays SDK-friendly."""

    def setUp(self):
        self.client = TestClient(app)

    def test_openapi_exposes_lease_bearer_security_scheme(self):
        """Lease API should publish a standard HTTP bearer scheme."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)

        spec = response.json()
        security_schemes = spec["components"]["securitySchemes"]
        self.assertIn("LeaseBearerAuth", security_schemes)
        self.assertEqual(security_schemes["LeaseBearerAuth"]["type"], "http")
        self.assertEqual(security_schemes["LeaseBearerAuth"]["scheme"], "bearer")

    def test_operation_ids_are_stable_for_client_generation(self):
        """Client SDK generation depends on deterministic operation ids."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)

        spec = response.json()
        operation_ids = []
        for path_item in spec["paths"].values():
            for operation in path_item.values():
                if isinstance(operation, dict) and "operationId" in operation:
                    operation_ids.append(operation["operationId"])

        self.assertEqual(len(operation_ids), len(set(operation_ids)))
        self.assertIn("acquireLease", operation_ids)
        self.assertIn("createSubscription", operation_ids)
        self.assertIn("getSystemStatus", operation_ids)
        self.assertIn("previewProxyExitIpDuplicates", operation_ids)
        self.assertIn("dedupeProxiesByExitIp", operation_ids)
        self.assertIn("setManualLeaseCooldown", operation_ids)
        self.assertIn("recallLeaseCooldown", operation_ids)
        self.assertIn("applyTimedLeaseCooldownBatch", operation_ids)
        self.assertIn("resetWorkspaceLeaseState", operation_ids)
        self.assertIn("testNodes", operation_ids)
        self.assertIn("startNodeTestJob", operation_ids)
        self.assertIn("getNodeTestJob", operation_ids)
        self.assertIn("listCustomGroups", operation_ids)
        self.assertIn("createCustomGroup", operation_ids)
        self.assertIn("renameCustomGroup", operation_ids)
        self.assertIn("deleteCustomGroup", operation_ids)
        self.assertIn("listCustomGroupNodes", operation_ids)
        self.assertIn("importCustomGroupNodes", operation_ids)
        self.assertIn("copyNodesToCustomGroup", operation_ids)
        self.assertIn("deleteCustomGroupNode", operation_ids)
        self.assertIn("listCustomGroups", operation_ids)
        self.assertIn("createCustomGroup", operation_ids)
        self.assertIn("renameCustomGroup", operation_ids)
        self.assertIn("deleteCustomGroup", operation_ids)
        self.assertIn("listCustomGroupNodes", operation_ids)
        self.assertIn("importCustomGroupNodes", operation_ids)
        self.assertIn("copyNodesToCustomGroup", operation_ids)
        self.assertIn("deleteCustomGroupNode", operation_ids)

    def test_openapi_includes_request_examples(self):
        """Request schemas should carry examples for API consumers."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)

        spec = response.json()
        schemas = spec["components"]["schemas"]
        self.assertIn("example", schemas["LeaseAcquireRequest"])
        self.assertIn("example", schemas["SubscriptionCreate"])
        self.assertIn("example", schemas["ProxyAddRequest"])
        acquire_request_props = schemas["LeaseAcquireRequest"]["properties"]
        self.assertIn("initial_port_ordering", acquire_request_props)
        release_request_props = schemas["LeaseReleaseRequest"]["properties"]
        cooldown_request_props = schemas["LeaseCooldownRequest"]["properties"]
        batch_cooldown_request_props = schemas["LeaseTimedCooldownBatchRequest"]["properties"]
        reset_request_props = schemas["WorkspaceResetRequest"]["properties"]
        self.assertIn("result", release_request_props)
        self.assertIn("result", cooldown_request_props)
        self.assertIn("result", batch_cooldown_request_props)
        self.assertIn("clear_metrics", reset_request_props)

    def test_proxy_and_lease_schemas_expose_explicit_proxy_urls(self):
        """Client consumers should not need to guess whether a local port is HTTP or SOCKS5."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)

        spec = response.json()
        schemas = spec["components"]["schemas"]

        proxy_props = schemas["ProxyResponse"]["properties"]
        self.assertIn("proxy_scheme", proxy_props)
        self.assertIn("http_proxy_url", proxy_props)
        self.assertIn("socks5_proxy_url", proxy_props)
        self.assertIn("socks5h_proxy_url", proxy_props)
        self.assertIn("supported_proxy_protocols", proxy_props)
        self.assertIn("pool_status", proxy_props)
        self.assertIn("disabled_reason", proxy_props)

        lease_props = schemas["LeaseAcquireResponse"]["properties"]
        self.assertIn("proxy_scheme", lease_props)
        self.assertIn("http_proxy_url", lease_props)
        self.assertIn("socks5_proxy_url", lease_props)
        self.assertIn("socks5h_proxy_url", lease_props)
        self.assertIn("supported_proxy_protocols", lease_props)
        self.assertIn("metrics", lease_props)

        release_props = schemas["LeaseReleaseResponse"]["properties"]
        self.assertIn("success", release_props)
        self.assertIn("cooldown_until", release_props)

        cooldown_props = schemas["CooldownInfo"]["properties"]
        self.assertIn("source", cooldown_props)
        self.assertIn("until", cooldown_props)
        self.assertIn("node_name", cooldown_props)

        active_lease_props = schemas["ActiveLeaseInfo"]["properties"]
        self.assertIn("node_name", active_lease_props)
        self.assertIn("metrics", active_lease_props)

        metrics_props = schemas["LeaseProxyMetrics"]["properties"]
        self.assertIn("usage_count", metrics_props)
        self.assertIn("success_count", metrics_props)
        self.assertIn("failure_count", metrics_props)
        self.assertIn("last_used_at", metrics_props)

        proxy_test_all_props = schemas["ProxyTestAllResponse"]["properties"]
        self.assertIn("attempts", proxy_test_all_props)
        self.assertIn("cooldown_candidates", proxy_test_all_props)

        self.assertIn("/api/proxies/duplicates/exit-ip", spec["paths"])
        self.assertIn("/api/proxies/dedupe/exit-ip", spec["paths"])
        dedupe_request_ref = spec["paths"]["/api/proxies/dedupe/exit-ip"]["post"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        dedupe_request_name = dedupe_request_ref.rsplit("/", 1)[-1]
        dedupe_request_props = schemas[dedupe_request_name]["properties"]
        self.assertIn("disable_ports", dedupe_request_props)

        dedupe_response_ref = spec["paths"]["/api/proxies/dedupe/exit-ip"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        dedupe_response_name = dedupe_response_ref.rsplit("/", 1)[-1]
        dedupe_response_props = schemas[dedupe_response_name]["properties"]
        self.assertIn("disabled_count", dedupe_response_props)
        self.assertIn("disabled_ports", dedupe_response_props)
        self.assertIn("kept_ports", dedupe_response_props)

        lease_status_props = schemas["LeaseStatusResponse"]["properties"]
        self.assertIn("workspaces", lease_status_props)

        reset_props = schemas["WorkspaceResetResponse"]["properties"]
        self.assertIn("released_count", reset_props)
        self.assertIn("recalled_count", reset_props)
        self.assertIn("cleared_metric_entries", reset_props)

        usage_item_ref = schemas["LeaseStatsResponse"]["properties"]["proxies_by_usage"]["items"]["$ref"]
        usage_item_name = usage_item_ref.rsplit("/", 1)[-1]
        usage_item_props = schemas[usage_item_name]["properties"]
        self.assertIn("workspace_id", usage_item_props)
        self.assertIn("success_count", usage_item_props)
        self.assertIn("failure_count", usage_item_props)

    def test_node_schemas_expose_pool_status_and_test_contract(self):
        """Node responses should expose pool status and node testing contract."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)

        spec = response.json()
        schemas = spec["components"]["schemas"]

        node_props = schemas["NodeResponse"]["properties"]
        self.assertIn("group_id", node_props)
        self.assertIn("group_type", node_props)
        self.assertIn("in_proxy_pool", node_props)
        self.assertIn("proxy_port", node_props)
        self.assertIn("subscription_id", node_props)
        self.assertIn("runtime_supported", node_props)
        self.assertIn("runtime_support_reason", node_props)
        self.assertIn("group_id", node_props)
        self.assertIn("group_type", node_props)
        self.assertIn("subscription_id", node_props)
        protocol_enum_name = node_props["protocol"]["$ref"].rsplit("/", 1)[-1]
        protocol_enum = schemas[protocol_enum_name]["enum"]
        self.assertIn("hysteria2", protocol_enum)
        self.assertIn("ssr", protocol_enum)

        self.assertIn("/api/nodes/test", spec["paths"])
        test_operation = spec["paths"]["/api/nodes/test"]["post"]
        request_schema = test_operation["requestBody"]["content"]["application/json"]["schema"]
        request_ref = request_schema.get("$ref")
        self.assertTrue(request_ref)
        request_name = request_ref.rsplit("/", 1)[-1]
        req_props = schemas[request_name]["properties"]
        self.assertIn("node_ids", req_props)
        self.assertIn("timeout", req_props)
        self.assertIn("test_profile", req_props)

        response_schema = test_operation["responses"]["200"]["content"]["application/json"]["schema"]
        response_ref = response_schema.get("$ref")
        self.assertTrue(response_ref)
        response_name = response_ref.rsplit("/", 1)[-1]
        resp_props = schemas[response_name]["properties"]
        self.assertIn("results", resp_props)
        self.assertIn("success_count", resp_props)
        self.assertIn("failed_count", resp_props)
        self.assertIn("test_profile", resp_props)

        result_schema = resp_props["results"]["items"]
        result_ref = result_schema.get("$ref")
        self.assertTrue(result_ref)
        result_name = result_ref.rsplit("/", 1)[-1]
        result_props = schemas[result_name]["properties"]
        self.assertIn("status", result_props)
        test_status_name = result_props["status"]["$ref"].rsplit("/", 1)[-1]
        test_status_enum = schemas[test_status_name]["enum"]
        self.assertIn("success", test_status_enum)
        self.assertIn("failed", test_status_enum)

        self.assertIn("/api/nodes/test-jobs", spec["paths"])
        start_job_operation = spec["paths"]["/api/nodes/test-jobs"]["post"]
        start_job_response = start_job_operation["responses"]["200"]["content"]["application/json"]["schema"]
        start_job_ref = start_job_response.get("$ref")
        self.assertTrue(start_job_ref)
        job_name = start_job_ref.rsplit("/", 1)[-1]
        job_props = schemas[job_name]["properties"]
        self.assertIn("job_id", job_props)
        self.assertIn("status", job_props)
        self.assertIn("progress_percent", job_props)
        self.assertIn("current_target_completed", job_props)
        self.assertIn("current_target_total", job_props)

        self.assertIn("/api/custom-groups", spec["paths"])
        self.assertIn("/api/custom-groups/{group_id}/nodes", spec["paths"])
        self.assertIn("/api/custom-groups/{group_id}/nodes/import", spec["paths"])
        self.assertIn("/api/custom-groups/{group_id}/nodes/copy", spec["paths"])
        self.assertIn("/api/custom-groups/{group_id}/nodes/{node_id}", spec["paths"])

        import_operation = spec["paths"]["/api/custom-groups/{group_id}/nodes/import"]["post"]
        import_response = import_operation["responses"]["200"]["content"]["application/json"]["schema"]
        import_ref = import_response.get("$ref")
        self.assertTrue(import_ref)
        import_name = import_ref.rsplit("/", 1)[-1]
        import_props = schemas[import_name]["properties"]
        self.assertIn("imported_count", import_props)
        self.assertIn("skipped_duplicates", import_props)
        self.assertIn("total_parsed", import_props)
        self.assertIn("ignored_unsupported_count", import_props)


if __name__ == "__main__":
    unittest.main()
