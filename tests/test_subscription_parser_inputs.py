"""
Subscription input compatibility tests (URI/Base64/Clash/SIP008).
"""

import base64
import unittest
from unittest.mock import patch

from src.xray_prism.capabilities import evaluate_node_runtime
from src.xray_prism.models import Protocol
from src.xray_prism.parser import parse_shadowsocks, parse_subscription


class TestSubscriptionParserInputs(unittest.TestCase):
    def test_parse_subscription_accepts_base64_multiline_uri_payload(self):
        payload = (
            "trojan://secret@example.com:443#TROJAN\n"
            "ss://YWVzLTEyOC1nY206cGFzc0BleGFtcGxlLmNvbTo4Mzg4#SS"
        )
        encoded = base64.b64encode(payload.encode("utf-8")).decode("utf-8")

        nodes = parse_subscription(encoded)
        self.assertEqual(len(nodes), 2)
        protocols = sorted(item.protocol.value for item in nodes)
        self.assertEqual(protocols, [Protocol.SHADOWSOCKS.value, Protocol.TROJAN.value])

    def test_parse_subscription_accepts_clash_provider_top_level_list(self):
        content = (
            "- name: HK-SS\n"
            "  type: ss\n"
            "  server: hk.example.com\n"
            "  port: 8388\n"
            "  cipher: aes-128-gcm\n"
            "  password: pass\n"
            "- name: HK-Trojan\n"
            "  type: trojan\n"
            "  server: tr.example.com\n"
            "  port: 443\n"
            "  password: secret\n"
            "  sni: tr.example.com\n"
            "  skip-cert-verify: true\n"
        )

        nodes = parse_subscription(content)
        self.assertEqual(len(nodes), 2)
        by_name = {item.name: item for item in nodes}
        self.assertEqual(by_name["HK-SS"].protocol, Protocol.SHADOWSOCKS)
        self.assertEqual(by_name["HK-Trojan"].protocol, Protocol.TROJAN)

    def test_parse_subscription_accepts_clash_vless_grpc_reality_fields(self):
        content = (
            "proxies:\n"
            "  - name: VLESS-GRPC\n"
            "    type: vless\n"
            "    server: vl.example.com\n"
            "    port: 443\n"
            "    uuid: 11111111-1111-1111-1111-111111111111\n"
            "    tls: true\n"
            "    network: grpc\n"
            "    client-fingerprint: chrome\n"
            "    grpc-opts:\n"
            "      grpc-service-name: grpc-demo\n"
            "    reality-opts:\n"
            "      public-key: pubkey-demo\n"
            "      short-id: short-demo\n"
        )

        nodes = parse_subscription(content)
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.protocol, Protocol.VLESS)
        self.assertEqual(node.service_name, "grpc-demo")
        self.assertEqual(node.public_key, "pubkey-demo")
        self.assertEqual(node.short_id, "short-demo")
        self.assertEqual(node.fingerprint, "chrome")

    def test_parse_subscription_accepts_sip008_json_payload(self):
        content = (
            '{"version":1,"servers":[{"remarks":"SS-SIP008","server":"hk.example.com","server_port":8388,'
            '"method":"aes-128-gcm","password":"pass","plugin":"v2ray-plugin",'
            '"plugin_opts":{"mode":"websocket","host":"cdn.example.com"},"uot":true,"UoTVersion":2}]}'
        )

        nodes = parse_subscription(content)
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.protocol, Protocol.SHADOWSOCKS)
        self.assertEqual(node.name, "SS-SIP008")
        self.assertEqual(node.ss_plugin, "v2ray-plugin")
        self.assertEqual(node.ss_plugin_opts, "mode=websocket;host=cdn.example.com")
        self.assertTrue(node.ss_uot)
        self.assertEqual(node.ss_uot_version, 2)

    def test_parse_subscription_accepts_clash_hysteria2_fields(self):
        content = (
            "proxies:\n"
            "  - name: HY2-HK\n"
            "    type: hysteria2\n"
            "    server: hy.example.com\n"
            "    port: 8443\n"
            "    password: secret\n"
            "    sni: cdn.example.com\n"
            "    skip-cert-verify: true\n"
            "    obfs: salamander\n"
            "    obfs-password: obfs-secret\n"
            "    alpn:\n"
            "      - h3\n"
            "      - h3-29\n"
        )

        nodes = parse_subscription(content)
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.protocol, Protocol.HYSTERIA2)
        self.assertEqual(node.hy_obfs, "salamander")
        self.assertEqual(node.hy_obfs_password, "obfs-secret")
        self.assertEqual(node.hy_alpn, "h3,h3-29")
        self.assertTrue(node.allow_insecure)

    def test_parse_shadowsocks_supports_query_remarks_and_plugin_opts_alias(self):
        node = parse_shadowsocks(
            "ss://aes-128-gcm:pass@example.com:8388"
            "?plugin_name=v2ray-plugin&plugin-opts=mode%3Dwebsocket&remarks=NamedByQuery"
        )
        self.assertEqual(node.name, "NamedByQuery")
        self.assertEqual(node.ss_plugin, "v2ray-plugin")
        self.assertEqual(node.ss_plugin_opts, "mode=websocket")

    def test_clash_regex_fallback_keeps_node_visible_but_runtime_unsupported(self):
        # Force fallback parser path by disabling yaml loader in parser module.
        content = (
            "- { name: 'Fallback-Trojan', type: trojan, "
            "server: demo.example.com, port: 443, password: secret }"
        )

        with patch("src.xray_prism.parser.yaml", None):
            nodes = parse_subscription(content)

        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].protocol, Protocol.TROJAN)
        capability = evaluate_node_runtime(nodes[0])
        self.assertFalse(capability.runtime_supported)

    def test_unknown_network_in_clash_node_is_not_runtime_supported(self):
        content = (
            "proxies:\n"
            "  - name: VLESS-Unknown-Network\n"
            "    type: vless\n"
            "    server: vl.example.com\n"
            "    port: 443\n"
            "    uuid: 11111111-1111-1111-1111-111111111111\n"
            "    tls: true\n"
            "    network: quicx\n"
        )
        nodes = parse_subscription(content)
        self.assertEqual(len(nodes), 1)
        capability = evaluate_node_runtime(nodes[0])
        self.assertFalse(capability.runtime_supported)
        self.assertIn("network", (capability.reason or "").lower())


if __name__ == "__main__":
    unittest.main()
