"""
Guard rails that keep protocol-compatibility documentation aligned across docs.
"""
from pathlib import Path
import unittest


class TestProtocolDocs(unittest.TestCase):
    """Ensure docs explain recognition-vs-runtime boundaries consistently."""

    @classmethod
    def setUpClass(cls):
        repo_root = Path(__file__).resolve().parent.parent
        cls.architecture_doc = (repo_root / "docs" / "tech" / "architecture.md").read_text(encoding="utf-8")
        cls.product_doc = (repo_root / "docs" / "product" / "requirements.md").read_text(encoding="utf-8")
        cls.readme_zh = (repo_root / "README.md").read_text(encoding="utf-8")
        cls.readme_en = (repo_root / "README.en.md").read_text(encoding="utf-8")

    def test_protocol_recognition_and_runtime_support_are_documented(self):
        doc = self.architecture_doc
        self.assertIn("`vmess`、`vless`、`shadowsocks`、`trojan`、`hysteria2` 和 `ssr`", doc)
        self.assertIn("RUNTIME_SUPPORTED_PROTOCOLS", doc)
        self.assertIn("vmess/vless/shadowsocks/trojan/hysteria2", doc)

    def test_unsupported_protocol_display_behavior_is_clearly_described(self):
        doc = self.architecture_doc
        self.assertIn("不兼容协议节点也会保留在节点列表中", doc)
        self.assertIn("SSR（ShadowsocksR）", doc)
        self.assertIn("灰色不可选", doc)
        self.assertIn("带当前未映射的 SS plugin 节点会保留在列表中", doc)

    def test_architecture_doc_mentions_mainstream_subscription_input(self):
        doc = self.architecture_doc
        self.assertIn("Clash YAML / provider", doc)
        self.assertIn("SIP008 / SIP002", doc)
        self.assertIn("v2rayN / v2rayNG", doc)
        self.assertIn("Xray-only", doc)

    def test_product_requirements_match_runtime_boundary(self):
        doc = self.product_doc
        self.assertIn("Xray-only", doc)
        self.assertIn("识别到的节点不等于可运行节点", doc)
        self.assertIn("vmess/vless/shadowsocks/trojan/hysteria2", doc)

    def test_readme_zh_documents_mainstream_input_and_boundaries(self):
        doc = self.readme_zh
        self.assertIn("主流", doc)
        self.assertIn("Clash YAML / provider", doc)
        self.assertIn("SIP008", doc)
        self.assertIn("v2rayN/v2rayNG", doc)
        self.assertIn("Xray-only", doc)
        self.assertIn("runtime_supported", doc)
        self.assertIn("runtime_support_reason", doc)

    def test_readme_en_documents_mainstream_input_and_boundaries(self):
        doc = self.readme_en
        self.assertIn("mainstream", doc)
        self.assertIn("Clash YAML/provider", doc)
        self.assertIn("SIP008", doc)
        self.assertIn("v2rayN/v2rayNG", doc)
        self.assertIn("Xray-only", doc)
        self.assertIn("runtime_supported", doc)
        self.assertIn("runtime_support_reason", doc)


if __name__ == "__main__":
    unittest.main()
