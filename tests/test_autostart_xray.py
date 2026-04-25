import os
import unittest
from unittest.mock import patch


class TestXrayAutoStart(unittest.TestCase):
    def test_maybe_autostart_xray_disabled_by_default(self):
        import api.main as main

        with patch.dict(os.environ, {}, clear=True), patch.object(main.threading, "Thread") as thread_ctor:
            main.maybe_autostart_xray()
            thread_ctor.assert_not_called()

    def test_maybe_autostart_xray_starts_thread_when_enabled(self):
        import api.main as main

        with patch.dict(os.environ, {"XRAY_PRISM_AUTOSTART_XRAY": "1"}, clear=True), patch.object(main.threading, "Thread") as thread_ctor:
            main.maybe_autostart_xray()
            thread_ctor.assert_called_once()
            kwargs = thread_ctor.call_args.kwargs
            self.assertTrue(kwargs.get("daemon"))
            self.assertEqual(kwargs.get("name"), "XrayAutoStart")


if __name__ == "__main__":
    unittest.main()

