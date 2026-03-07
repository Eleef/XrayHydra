"""
Frontend smoke tests for static entrypoints.
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

    def test_favicon_request_does_not_404(self):
        response = self.client.get("/favicon.ico")
        self.assertIn(response.status_code, (200, 204))


if __name__ == "__main__":
    unittest.main()
