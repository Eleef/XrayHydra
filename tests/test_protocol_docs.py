"""
Guard rails that keep the architecture doc aligned with current SSR handling.
"""
from pathlib import Path
import unittest


class TestProtocolDocs(unittest.TestCase):
    """Ensure the architecture doc explains protocol recognition and runtime boundaries."""

    @classmethod
    def setUpClass(cls):
        cls.architecture_doc = (
            Path(__file__).resolve().parent.parent
            / "docs"
            / "tech"
            / "architecture.md"
        ).read_text(encoding="utf-8")

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


if __name__ == "__main__":
    unittest.main()
