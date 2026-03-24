"""
Subscription decoder registry tests.
"""

import base64
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

    def test_decodes_base64_uri_payload(self):
        registry = create_default_decoder_registry()
        payload = "trojan://secret@example.com:443#demo\nss://YWVzLTEyOC1nY206cGFzc0BleGFtcGxlLmNvbTo4Mzg4#ss"
        encoded = base64.b64encode(payload.encode("utf-8")).decode("utf-8")
        decoded = registry.decode(encoded)
        self.assertEqual(decoded.mode, "uri_lines")
        self.assertIn("trojan://secret@example.com:443#demo", decoded.content)
        self.assertIn("ss://YWVzLTEyOC1nY206cGFzc0BleGFtcGxlLmNvbTo4Mzg4#ss", decoded.content)

    def test_decodes_base64_clash_payload(self):
        registry = create_default_decoder_registry()
        payload = (
            "proxies:\n"
            "  - name: hk\n"
            "    type: ss\n"
            "    server: hk.example.com\n"
            "    port: 8388\n"
            "    cipher: aes-128-gcm\n"
            "    password: pass\n"
        )
        encoded = base64.b64encode(payload.encode("utf-8")).decode("utf-8")
        decoded = registry.decode(encoded)
        self.assertEqual(decoded.mode, "clash_yaml")
        self.assertIn("proxies:", decoded.content)

    def test_detects_sip008_json_and_normalizes_to_ss_uris(self):
        registry = create_default_decoder_registry()
        payload = (
            '{"version":1,"servers":[{"remarks":"hk","server":"hk.example.com","server_port":8388,'
            '"method":"aes-128-gcm","password":"pass"}]}'
        )
        decoded = registry.decode(payload)
        self.assertEqual(decoded.mode, "uri_lines")
        self.assertIn("ss://", decoded.content)
        self.assertIn("#hk", decoded.content)

    def test_detects_clash_provider_list_shape(self):
        registry = create_default_decoder_registry()
        payload = (
            "- name: hk\n"
            "  type: ss\n"
            "  server: hk.example.com\n"
            "  port: 8388\n"
            "  cipher: aes-128-gcm\n"
            "  password: pass\n"
        )
        decoded = registry.decode(payload)
        self.assertEqual(decoded.mode, "clash_yaml")


if __name__ == "__main__":
    unittest.main()
