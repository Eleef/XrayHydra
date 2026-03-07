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
        self.assertIn("setManualLeaseCooldown", operation_ids)
        self.assertIn("recallLeaseCooldown", operation_ids)

    def test_openapi_includes_request_examples(self):
        """Request schemas should carry examples for API consumers."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)

        spec = response.json()
        schemas = spec["components"]["schemas"]
        self.assertIn("example", schemas["LeaseAcquireRequest"])
        self.assertIn("example", schemas["SubscriptionCreate"])
        self.assertIn("example", schemas["ProxyAddRequest"])

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

        lease_props = schemas["LeaseAcquireResponse"]["properties"]
        self.assertIn("proxy_scheme", lease_props)
        self.assertIn("http_proxy_url", lease_props)
        self.assertIn("socks5_proxy_url", lease_props)
        self.assertIn("socks5h_proxy_url", lease_props)
        self.assertIn("supported_proxy_protocols", lease_props)

        release_props = schemas["LeaseReleaseResponse"]["properties"]
        self.assertIn("success", release_props)
        self.assertIn("cooldown_until", release_props)

        cooldown_props = schemas["CooldownInfo"]["properties"]
        self.assertIn("source", cooldown_props)
        self.assertIn("until", cooldown_props)

        lease_status_props = schemas["LeaseStatusResponse"]["properties"]
        self.assertIn("workspaces", lease_status_props)


if __name__ == "__main__":
    unittest.main()
