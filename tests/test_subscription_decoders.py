"""
Subscription decoder registry tests.
"""

import unittest

from src.xray_prism.subscription_decoders import create_default_decoder_registry


class TestSubscriptionDecoders(unittest.TestCase):
    def test_detects_clash_yaml(self):
        registry = create_default_decoder_registry()
        decoded = registry.decode(
            "proxies:\n"
            "  - { name: demo, type: trojan, server: example.com, port: 443, password: secret }\n"
        )
        self.assertEqual(decoded.mode, "clash_yaml")

    def test_falls_back_to_uri_lines(self):
        registry = create_default_decoder_registry()
        decoded = registry.decode("trojan://secret@example.com:443#demo")
        self.assertEqual(decoded.mode, "uri_lines")


if __name__ == "__main__":
    unittest.main()
