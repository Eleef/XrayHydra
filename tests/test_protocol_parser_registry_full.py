"""
Additional registry behavior tests for vmess/vless/trojan.
"""

import base64
import json
import unittest

from src.xray_prism.models import Protocol
from src.xray_prism.parser import parse_line, parse_trojan, parse_vless, parse_vmess


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


class TestProtocolParserRegistryFull(unittest.TestCase):
    def test_parse_line_dispatches_vmess(self):
        payload = {
            "ps": "HK-VMESS",
            "add": "vm.example.com",
            "port": "443",
            "id": "11111111-1111-1111-1111-111111111111",
            "aid": "0",
            "net": "ws",
            "tls": "tls",
            "host": "cdn.example.com",
            "path": "/ws",
        }
        uri = "vmess://" + _b64(json.dumps(payload))
        node = parse_line(uri)
        self.assertIsNotNone(node)
        self.assertEqual(node.protocol, Protocol.VMESS)
        self.assertEqual(node.name, "HK-VMESS")

    def test_parse_line_dispatches_vless(self):
        uri = (
            "vless://11111111-1111-1111-1111-111111111111@example.com:443"
            "?type=ws&security=tls&host=cdn.example.com&path=%2Fws&sni=example.com#HK-VLESS"
        )
        node = parse_line(uri)
        self.assertIsNotNone(node)
        self.assertEqual(node.protocol, Protocol.VLESS)
        self.assertEqual(node.name, "HK-VLESS")

    def test_parse_line_dispatches_trojan(self):
        uri = "trojan://secret@example.com:443?type=ws&path=%2Ftrojan&sni=example.com#HK-TROJAN"
        node = parse_line(uri)
        self.assertIsNotNone(node)
        self.assertEqual(node.protocol, Protocol.TROJAN)
        self.assertEqual(node.name, "HK-TROJAN")

    def test_compat_entrypoints_keep_behavior(self):
        payload = {
            "ps": "VMESS",
            "add": "vm.example.com",
            "port": "443",
            "id": "11111111-1111-1111-1111-111111111111",
        }
        vmess_uri = "vmess://" + _b64(json.dumps(payload))
        vless_uri = "vless://11111111-1111-1111-1111-111111111111@example.com:443#VLESS"
        trojan_uri = "trojan://secret@example.com:443#TROJAN"

        self.assertEqual(parse_vmess(vmess_uri).protocol, Protocol.VMESS)
        self.assertEqual(parse_vless(vless_uri).protocol, Protocol.VLESS)
        self.assertEqual(parse_trojan(trojan_uri).protocol, Protocol.TROJAN)


if __name__ == "__main__":
    unittest.main()
