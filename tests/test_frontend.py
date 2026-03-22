"""
Frontend smoke tests for static entrypoints and documentation syncs.
"""
import unittest

from fastapi.testclient import TestClient

from api.main import app


class TestFrontendEntrypoints(unittest.TestCase):
    """Verify frontend-facing static entrypoints behave predictably."""

    def setUp(self):
        self.client = TestClient(app)

    def test_root_serves_frontend_html(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        body = response.text
        self.assertIn('id="btn-add-to-proxy"', body)
        self.assertIn('id="btn-add-to-group"', body)
        self.assertIn("测试选中", body)
        self.assertIn("测试全部", body)
        self.assertIn('id="btn-dedupe-exit-ip"', body)
        self.assertIn("节点组", body)

    def test_favicon_request_does_not_404(self):
        response = self.client.get("/favicon.ico")
        self.assertIn(response.status_code, (200, 204))

    def test_frontend_mentions_exclusion_keywords(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.text
        self.assertIn("排除关键词", body)
        self.assertIn('id="node-exclusion-input"', body)
        self.assertIn('id="modal-exit-ip-dedupe-review"', body)
        self.assertIn('id="modal-create-group-entry"', body)
        self.assertIn('id="modal-add-custom-group"', body)
        self.assertIn('id="modal-copy-to-group"', body)

    def test_docs_track_keyword_counts_and_progress(self):
        with open("docs/product/frontend_spec.md", encoding="utf-8") as spec:
            spec_text = spec.read()
        self.assertIn("匹配数量", spec_text)
        self.assertIn("Progress Bar Feedback", spec_text)
        self.assertIn("进度条", spec_text)
        self.assertIn("/api/nodes/test-jobs", spec_text)
        self.assertIn("progress_percent", spec_text)
        self.assertIn("去重禁用", spec_text)
        self.assertIn("加入到分组", spec_text)
        self.assertIn("自定义组", spec_text)
        with open("docs/guide/development.md", encoding="utf-8") as guide:
            guide_text = guide.read()
        self.assertIn("排除关键词标签后会显示", guide_text)
        self.assertIn("节点测试进度条", guide_text)
        self.assertIn("/api/nodes/test-jobs/{job_id}", guide_text)
        self.assertIn("去重禁用", guide_text)
        self.assertIn("节点组", guide_text)
        self.assertIn("加入到分组", guide_text)

    def test_docs_describe_progress_polling_fields(self):
        with open("docs/product/frontend_spec.md", encoding="utf-8") as spec:
            spec_text = spec.read()
        self.assertIn("failed_count", spec_text)
        self.assertIn("success_count", spec_text)
        self.assertIn("current_target_completed", spec_text)
