"""Tests for server startup port conflict checks."""
import argparse
import errno
import unittest
from unittest.mock import patch

import server


class TestServerPortConflict(unittest.TestCase):
    def test_run_server_rejects_occupied_port(self):
        args = argparse.Namespace(host="127.0.0.1", port=8000, reload=False)

        with patch.object(server, "can_bind_port", return_value=(False, "端口已被占用: http://127.0.0.1:8000/")), \
             patch.object(server.uvicorn, "run") as uvicorn_run:
            exit_code = server.run_server(args)

        self.assertEqual(exit_code, 1)
        uvicorn_run.assert_not_called()

    def test_run_server_starts_when_port_is_available(self):
        args = argparse.Namespace(host="127.0.0.1", port=8000, reload=False)

        with patch.object(server, "can_bind_port", return_value=(True, None)), \
             patch.object(server.uvicorn, "run") as uvicorn_run:
            exit_code = server.run_server(args)

        self.assertEqual(exit_code, 0)
        uvicorn_run.assert_called_once_with(
            "api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
            log_level="info",
        )

    def test_can_bind_port_maps_address_in_use_error(self):
        with patch("server.socket.socket") as socket_ctor:
            sock = socket_ctor.return_value
            sock.bind.side_effect = OSError(errno.EADDRINUSE, "Address already in use")

            ok, reason = server.can_bind_port("127.0.0.1", 8000)

        self.assertFalse(ok)
        self.assertIn("端口已被占用", reason)

    def test_format_port_conflict_message_contains_port(self):
        message = server.format_port_conflict_message("127.0.0.1", 8010)
        self.assertIn("http://127.0.0.1:8010/", message)
        self.assertIn("改用其他端口", message)


if __name__ == "__main__":
    unittest.main()
