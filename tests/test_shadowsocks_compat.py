"""
Shadowsocks compatibility tests for SIP002/UoT/runtime capability.
"""

import unittest
from unittest.mock import patch

from api.services.subscription_service import SubscriptionService
from src.xray_prism.capabilities import evaluate_node_runtime
from src.xray_prism.generator import ConfigGenerator
from src.xray_prism.models import Protocol, ProxyNode
from src.xray_prism.parser import parse_shadowsocks


class TestShadowsocksCompat(unittest.TestCase):
    def test_parse_shadowsocks_supports_sip002_plain_userinfo(self):
        node = parse_shadowsocks(
            "ss://aes-256-gcm:pass@example.com:8388#SS-Plain"
        )

        self.assertEqual(node.protocol, Protocol.SHADOWSOCKS)
        self.assertEqual(node.security, "aes-256-gcm")
        self.assertEqual(node.password, "pass")
        self.assertEqual(node.address, "example.com")
        self.assertEqual(node.port, 8388)
        self.assertEqual(node.name, "SS-Plain")

    def test_parse_shadowsocks_extracts_plugin_and_uot(self):
        node = parse_shadowsocks(
            "ss://aes-128-gcm:pass@example.com:8388"
            "?plugin=v2ray-plugin%3Bmode%3Dwebsocket%3Bhost%3Dcdn.example.com"
            "&uot=1&UoTVersion=2#SS-Plugin"
        )

        self.assertEqual(node.ss_plugin, "v2ray-plugin")
        self.assertEqual(node.ss_plugin_opts, "mode=websocket;host=cdn.example.com")
        self.assertTrue(node.ss_uot)
        self.assertEqual(node.ss_uot_version, 2)

    def test_shadowsocks_plugin_is_runtime_unsupported(self):
        node = ProxyNode(
            name="SS-Plugin",
            protocol=Protocol.SHADOWSOCKS,
            address="example.com",
            port=8388,
            password="pass",
            security="aes-128-gcm",
            ss_plugin="v2ray-plugin",
            ss_plugin_opts="mode=websocket",
        )

        capability = evaluate_node_runtime(node)
        self.assertFalse(capability.runtime_supported)
        self.assertIn("Shadowsocks plugin", capability.reason or "")

    def test_shadowsocks_outbound_includes_uot_fields(self):
        node = ProxyNode(
            name="SS-UOT",
            protocol=Protocol.SHADOWSOCKS,
            address="example.com",
            port=8388,
            password="pass",
            security="aes-128-gcm",
            ss_uot=True,
            ss_uot_version=2,
        )

        outbound = ConfigGenerator()._node_to_outbound(node, "out_10000")
        server = outbound["settings"]["servers"][0]
        self.assertTrue(server["uot"])
        self.assertEqual(server["UoTVersion"], 2)

    def test_subscription_service_persists_shadowsocks_extension_fields(self):
        node = ProxyNode(
            name="SS-UOT",
            protocol=Protocol.SHADOWSOCKS,
            address="example.com",
            port=8388,
            password="pass",
            security="aes-128-gcm",
            ss_plugin="v2ray-plugin",
            ss_plugin_opts="mode=websocket",
            ss_uot=True,
            ss_uot_version=2,
        )
        service = SubscriptionService.__new__(SubscriptionService)

        with patch("api.services.subscription_service.fetch_subscription", return_value="ss://demo"), \
             patch("api.services.subscription_service.parse_subscription", return_value=[node]):
            nodes = service._fetch_subscription_nodes_data("sub_demo", "https://example.com/sub")

        payload = next(iter(nodes.values()))
        self.assertEqual(payload["ss_plugin"], "v2ray-plugin")
        self.assertEqual(payload["ss_plugin_opts"], "mode=websocket")
        self.assertTrue(payload["ss_uot"])
        self.assertEqual(payload["ss_uot_version"], 2)


if __name__ == "__main__":
    unittest.main()
