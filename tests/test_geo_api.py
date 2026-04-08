import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app
from api.services.lease_service import get_lease_manager
from api.services.proxy_service import get_proxy_service


class TestGeoApi(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_lookup_ip_region_returns_country_code(self):
        with patch("api.routes.geo.get_geo_service") as mock_geo:
            mock_geo.return_value.lookup_ip.return_value = {
                "ip": "8.8.8.8",
                "country": "United States",
                "country_code": "US",
            }
            response = self.client.get("/api/geo/ip/8.8.8.8")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["country_code"], "US")

    def test_lookup_ip_region_rejects_invalid_ip(self):
        response = self.client.get("/api/geo/ip/not-an-ip")
        self.assertEqual(response.status_code, 400)

    def test_list_exit_ips_by_country_code_groups_proxy_pool_by_workspace_state(self):
        proxy_service = get_proxy_service()
        lease_manager = get_lease_manager()

        original_get_proxies_by_country_code = proxy_service.get_proxies_by_country_code
        original_classify = lease_manager.classify_ports_for_workspace
        try:
            proxy_service.get_proxies_by_country_code = lambda code, include_disabled=True: [
                {
                    "port": 10001,
                    "exit_ip": "203.0.113.10",
                    "exit_country": "United States",
                    "exit_country_code": "US",
                },
                {
                    "port": 10002,
                    "exit_ip": "203.0.113.10",
                    "exit_country": "United States",
                    "exit_country_code": "US",
                },
                {
                    "port": 10003,
                    "exit_ip": "203.0.113.11",
                    "exit_country": "United States",
                    "exit_country_code": "US",
                },
            ]
            lease_manager.classify_ports_for_workspace = lambda workspace_id, ports: {
                "available": {port for port in ports if port == 10001},
                "occupied": {port for port in ports if port == 10002},
                "unavailable": {port for port in ports if port == 10003},
            }
            response = self.client.get(
                "/api/proxies/exit-ips/by-country/US",
                params={"workspace_id": "crawler_a"},
            )
        finally:
            proxy_service.get_proxies_by_country_code = original_get_proxies_by_country_code
            lease_manager.classify_ports_for_workspace = original_classify

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["workspace_id"], "crawler_a")
        self.assertEqual(payload["country_code"], "US")
        self.assertEqual(payload["total"], 2)
        first = payload["items"][0]
        self.assertIn("available_proxy_count", first)
        self.assertIn("occupied_proxy_count", first)
        self.assertIn("unavailable_proxy_count", first)


if __name__ == "__main__":
    unittest.main()
