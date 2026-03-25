"""
Focused tests for Hysteria2 parsing and outbound generation.
"""
import unittest

from src.xray_prism.generator import ConfigGenerator
from src.xray_prism.models import NetworkType, Protocol
from src.xray_prism.parser import parse_hysteria2


class TestHysteria2Support(unittest.TestCase):
    def test_parse_hysteria2_uri(self):
        node = parse_hysteria2(
            "hysteria2://secret@example.com:8443/?insecure=1&sni=example.com&alpn=h3#SG-HY2"
        )

        self.assertEqual(node.protocol, Protocol.HYSTERIA2)
        self.assertEqual(node.address, "example.com")
        self.assertEqual(node.port, 8443)
        self.assertEqual(node.password, "secret")
        self.assertEqual(node.network, NetworkType.HYSTERIA)
        self.assertTrue(node.tls)
        self.assertTrue(node.allow_insecure)
        self.assertEqual(node.sni, "example.com")
        self.assertEqual(node.hy_alpn, "h3")

    def test_generate_hysteria2_outbound(self):
        node = parse_hysteria2(
            "hysteria2://secret@example.com:8443/?insecure=1&sni=example.com&alpn=h3#SG-HY2"
        )
        config = ConfigGenerator(inbound_protocol="socks").generate([node])
        outbound = config["outbounds"][0]

        self.assertEqual(outbound["protocol"], "hysteria")
        self.assertEqual(outbound["settings"]["address"], "example.com")
        self.assertEqual(outbound["settings"]["port"], 8443)
        self.assertEqual(outbound["streamSettings"]["network"], "hysteria")
        self.assertEqual(outbound["streamSettings"]["security"], "tls")
        self.assertEqual(outbound["streamSettings"]["tlsSettings"]["serverName"], "example.com")
        self.assertTrue(outbound["streamSettings"]["tlsSettings"]["allowInsecure"])
        self.assertEqual(outbound["streamSettings"]["tlsSettings"]["alpn"], ["h3"])
        self.assertEqual(outbound["streamSettings"]["hysteriaSettings"]["version"], 2)
        self.assertEqual(outbound["streamSettings"]["hysteriaSettings"]["auth"], "secret")


if __name__ == "__main__":
    unittest.main()
