"""
Guard rails that keep the architecture doc aligned with current SSR handling.
"""
from pathlib import Path
import unittest


class TestProtocolDocs(unittest.TestCase):
    """Ensure the architecture doc explains protocol recognition and SSR rejection."""

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
        self.assertIn("`vmess`、`vless`、`shadowsocks`、`trojan` 和 `ssr`", doc)
        self.assertIn("RUNTIME_SUPPORTED_PROTOCOLS", doc)
        self.assertIn("vmess/vless/shadowsocks/trojan", doc)

    def test_ssr_import_behavior_is_clearly_described(self):
        doc = self.architecture_doc
        self.assertIn("订阅仅包含当前 Xray 不支持的协议: ssr", doc)
        self.assertIn("只导入可运行节点", doc)
        self.assertIn("忽略 SSR 节点", doc)


if __name__ == "__main__":
    unittest.main()
