import argparse
import io
import contextlib
import tempfile
import unittest
from pathlib import Path

from igwatch import cli
from igwatch.models import Availability, CheckResult


class DurationTests(unittest.TestCase):
    def test_parses_common_forms(self):
        cases = {"30": 30, "90s": 90, "5m": 300, "1h": 3600, "1h30m": 5400, "2d": 172800}
        for text, expected in cases.items():
            self.assertEqual(cli.parse_duration(text), expected, text)

    def test_rejects_garbage(self):
        for text in ["", "soon", "5x", "-3", "m5"]:
            with self.assertRaises(argparse.ArgumentTypeError, msg=text):
                cli.parse_duration(text)


class ParserTests(unittest.TestCase):
    def test_defaults(self):
        args = cli.build_parser().parse_args(["someone"])
        self.assertEqual(args.interval, 300.0)
        self.assertEqual(args.confirmations, 2)
        self.assertEqual(args.strategy, "auto")

    def test_repeatable_alert_flags(self):
        args = cli.build_parser().parse_args(
            ["someone", "--webhook", "https://a", "--webhook", "https://b", "--ntfy", "topic"]
        )
        self.assertEqual(args.webhook, ["https://a", "https://b"])
        self.assertEqual(args.ntfy, ["topic"])

    def test_usernames_are_optional_so_test_notify_works(self):
        args = cli.build_parser().parse_args(["--test-notify"])
        self.assertEqual(args.usernames, [])


class OnceModeTests(unittest.TestCase):
    """--once is the cron entry point, so its exit codes are part of the API."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = str(Path(self.tmp.name) / "state.json")
        self._original = cli.AvailabilityChecker

        def restore():
            cli.AvailabilityChecker = self._original

        self.addCleanup(restore)

    def _patch_status(self, status):
        class StubChecker:
            def __init__(self, *_, **__):
                pass

            def check(self, username):
                return CheckResult(username=username, status=status, strategy="stub")

        cli.AvailabilityChecker = StubChecker

    def _run(self, status, extra=()):
        self._patch_status(status)
        argv = ["someone", "--once", "--no-console", "--state-file", self.state, *extra]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = cli.main(argv)
        return code, buffer.getvalue()

    def test_available_exits_zero(self):
        code, out = self._run(Availability.AVAILABLE, ["--confirmations", "1"])
        self.assertEqual(code, cli.EXIT_AVAILABLE)
        self.assertIn("available", out)

    def test_taken_exits_one(self):
        code, _ = self._run(Availability.TAKEN)
        self.assertEqual(code, cli.EXIT_TAKEN)

    def test_unknown_exits_two(self):
        code, _ = self._run(Availability.UNKNOWN)
        self.assertEqual(code, cli.EXIT_UNKNOWN)

    def test_rate_limited_exits_two(self):
        code, _ = self._run(Availability.RATE_LIMITED)
        self.assertEqual(code, cli.EXIT_UNKNOWN)


class UsageTests(unittest.TestCase):
    def test_no_username_and_no_test_notify_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                cli.main([])
        self.assertNotEqual(ctx.exception.code, 0)

    def test_invalid_username_is_a_usage_error(self):
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stderr(io.StringIO()):
                cli.main(["not a username"])
        self.assertNotEqual(ctx.exception.code, 0)


class NotifierBuildTests(unittest.TestCase):
    def test_console_is_on_by_default(self):
        args = cli.build_parser().parse_args(["someone"])
        self.assertEqual(cli.build_notifiers(args).names, ["console"])

    def test_channels_are_assembled_in_order(self):
        args = cli.build_parser().parse_args(
            ["someone", "--ntfy", "topic", "--webhook", "https://x", "--exec", "echo {username}"]
        )
        self.assertEqual(cli.build_notifiers(args).names, ["console", "webhook", "ntfy", "exec"])

    def test_no_console_can_leave_zero_channels(self):
        args = cli.build_parser().parse_args(["someone", "--no-console"])
        self.assertEqual(len(cli.build_notifiers(args)), 0)


if __name__ == "__main__":
    unittest.main()
