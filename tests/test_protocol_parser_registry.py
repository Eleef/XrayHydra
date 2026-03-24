"""
Parser registry behavior tests.
"""

import base64
import unittest

from src.xray_prism.models import Protocol
from src.xray_prism.parser import parse_hysteria2, parse_line, parse_shadowsocks, parse_ssr


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


class TestProtocolParserRegistry(unittest.TestCase):
    def test_parse_line_dispatches_shadowsocks(self):
        uri = "ss://" + _b64("aes-128-gcm:pass@example.com:8388") + "#HK-SS"
        node = parse_line(uri)
        self.assertIsNotNone(node)
        self.assertEqual(node.protocol, Protocol.SHADOWSOCKS)
        self.assertEqual(node.name, "HK-SS")

    def test_parse_line_dispatches_hy2_alias(self):
        uri = "hy2://secret@example.com:8443/?sni=example.com#HY2"
        node = parse_line(uri)
        self.assertIsNotNone(node)
        self.assertEqual(node.protocol, Protocol.HYSTERIA2)
        self.assertEqual(node.name, "HY2")

    def test_parse_line_dispatches_ssr(self):
        raw = "example.com:8388:origin:aes-256-cfb:plain:" + _b64("pwd") + "/?remarks=" + _b64("SSR-Node")
        uri = "ssr://" + _b64(raw)
        node = parse_line(uri)
        self.assertIsNotNone(node)
        self.assertEqual(node.protocol, Protocol.SSR)
        self.assertEqual(node.name, "SSR-Node")

    def test_compat_entrypoints_keep_behavior(self):
        ss_uri = "ss://" + _b64("aes-128-gcm:pass@example.com:8388") + "#SS"
        hy2_uri = "hysteria2://secret@example.com:8443/?sni=example.com#HY2"
        ssr_raw = "example.com:8388:origin:aes-256-cfb:plain:" + _b64("pwd") + "/?remarks=" + _b64("SSR")
        ssr_uri = "ssr://" + _b64(ssr_raw)

        self.assertEqual(parse_shadowsocks(ss_uri).protocol, Protocol.SHADOWSOCKS)
        self.assertEqual(parse_hysteria2(hy2_uri).protocol, Protocol.HYSTERIA2)
        self.assertEqual(parse_ssr(ssr_uri).protocol, Protocol.SSR)


if __name__ == "__main__":
    unittest.main()
