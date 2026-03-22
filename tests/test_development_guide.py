"""
Documentation smoke checks for development guide commands.
"""
from pathlib import Path
import unittest


class TestDevelopmentGuide(unittest.TestCase):
    """Ensure key local validation commands remain discoverable in docs."""

    def test_development_guide_mentions_real_validation_flow_script(self):
        guide_path = Path(__file__).resolve().parent.parent / "docs" / "guide" / "development.md"
        content = guide_path.read_text(encoding="utf-8")

        self.assertIn("run_real_node_to_proxy_flow.py", content)
        self.assertIn("--subscription-url", content)
        self.assertIn("--cleanup-subscription", content)
        self.assertIn("--cleanup-added-proxies", content)


if __name__ == "__main__":
    unittest.main()
