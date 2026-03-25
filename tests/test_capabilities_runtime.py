"""
Runtime capability tests for node-level validation.
"""

import unittest

from src.xray_prism.capabilities import evaluate_node_runtime
from src.xray_prism.models import NetworkType, Protocol, ProxyNode


class TestRuntimeCapabilities(unittest.TestCase):
    def test_vmess_requires_uuid(self):
        node = ProxyNode(
            name="vmess-missing-uuid",
            protocol=Protocol.VMESS,
            address="vm.example.com",
            port=443,
            uuid=None,
        )
        capability = evaluate_node_runtime(node)
        self.assertFalse(capability.runtime_supported)
        self.assertIn("uuid", (capability.reason or "").lower())

    def test_vless_requires_uuid(self):
        node = ProxyNode(
            name="vless-missing-uuid",
            protocol=Protocol.VLESS,
            address="vl.example.com",
            port=443,
            uuid=None,
        )
        capability = evaluate_node_runtime(node)
        self.assertFalse(capability.runtime_supported)
        self.assertIn("uuid", (capability.reason or "").lower())

    def test_vless_rejects_unsupported_flow(self):
        node = ProxyNode(
            name="vless-unsupported-flow",
            protocol=Protocol.VLESS,
            address="vl.example.com",
            port=443,
            uuid="11111111-1111-1111-1111-111111111111",
            flow="invalid-flow",
        )
        capability = evaluate_node_runtime(node)
        self.assertFalse(capability.runtime_supported)
        self.assertIn("flow", (capability.reason or "").lower())

    def test_trojan_requires_password(self):
        node = ProxyNode(
            name="trojan-missing-password",
            protocol=Protocol.TROJAN,
            address="tr.example.com",
            port=443,
            password=None,
        )
        capability = evaluate_node_runtime(node)
        self.assertFalse(capability.runtime_supported)
        self.assertIn("password", (capability.reason or "").lower())

    def test_hysteria2_requires_password(self):
        node = ProxyNode(
            name="hy2-missing-password",
            protocol=Protocol.HYSTERIA2,
            address="hy.example.com",
            port=8443,
            password=None,
            network=NetworkType.HYSTERIA,
        )
        capability = evaluate_node_runtime(node)
        self.assertFalse(capability.runtime_supported)
        self.assertIn("password", (capability.reason or "").lower())

    def test_hysteria2_obfs_requires_password_pair(self):
        node = ProxyNode(
            name="hy2-obfs-missing-secret",
            protocol=Protocol.HYSTERIA2,
            address="hy.example.com",
            port=8443,
            password="secret",
            network=NetworkType.HYSTERIA,
            hy_obfs="salamander",
            hy_obfs_password=None,
        )
        capability = evaluate_node_runtime(node)
        self.assertFalse(capability.runtime_supported)
        self.assertIn("obfs", (capability.reason or "").lower())

    def test_shadowsocks_requires_method_and_password(self):
        node = ProxyNode(
            name="ss-missing-method-password",
            protocol=Protocol.SHADOWSOCKS,
            address="ss.example.com",
            port=8388,
            security="auto",
            password=None,
        )
        capability = evaluate_node_runtime(node)
        self.assertFalse(capability.runtime_supported)
        self.assertTrue(
            "加密" in (capability.reason or "") or "密码" in (capability.reason or "")
        )

    def test_unknown_network_type_is_not_runtime_supported(self):
        node_payload = {
            "name": "vless-unknown-network",
            "protocol": "vless",
            "address": "vl.example.com",
            "port": 443,
            "uuid": "11111111-1111-1111-1111-111111111111",
            "network": "quicx",
        }
        capability = evaluate_node_runtime(node_payload)
        self.assertFalse(capability.runtime_supported)
        self.assertIn("network", (capability.reason or "").lower())


if __name__ == "__main__":
    unittest.main()
