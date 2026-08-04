import unittest

from igwatch.models import Availability, CheckResult
from igwatch.notifiers import Notifier, NotifierGroup
from igwatch.state import StateStore
from igwatch.watcher import MIN_INTERVAL_SECONDS, WatchConfig, Watcher


class ScriptedChecker:
    """Returns queued statuses; repeats the last one forever."""

    def __init__(self, *statuses):
        self.statuses = list(statuses)
        self.calls = []

    def check(self, username):
        self.calls.append(username)
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return CheckResult(username=username, status=status, strategy="test")


class RecordingNotifier(Notifier):
    name = "recording"

    def __init__(self):
        self.alerts = []

    def deliver(self, title, body, result):
        self.alerts.append((title, body, result))


class FakeClock:
    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += max(seconds, 0)
        return False  # never interrupted


def build(statuses, config=None, state=None):
    clock = FakeClock()
    checker = ScriptedChecker(*statuses)
    notifier = RecordingNotifier()
    watcher = Watcher(
        ["someone"],
        checker,
        NotifierGroup([notifier]),
        config=config or WatchConfig(interval=60, jitter=0, confirmations=1),
        state=state,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )
    return watcher, checker, notifier, clock


class ConfirmationTests(unittest.TestCase):
    def test_single_available_check_alerts_when_confirmations_is_one(self):
        watcher, _, notifier, _ = build([Availability.AVAILABLE])
        watcher.run()
        self.assertEqual(len(notifier.alerts), 1)
        self.assertIn("@someone is available", notifier.alerts[0][0])

    def test_flapping_available_is_not_alerted(self):
        config = WatchConfig(interval=60, jitter=0, confirmations=2, confirm_delay=1)
        watcher, checker, notifier, _ = build(
            [Availability.AVAILABLE, Availability.TAKEN], config=config
        )
        result = watcher.check_once("someone")
        self.assertIs(result.status, Availability.UNKNOWN)
        self.assertEqual(notifier.alerts, [])
        self.assertEqual(len(checker.calls), 2)

    def test_two_agreeing_checks_alert(self):
        config = WatchConfig(interval=60, jitter=0, confirmations=2, confirm_delay=1)
        watcher, checker, notifier, _ = build([Availability.AVAILABLE], config=config)
        watcher.run()
        self.assertEqual(len(notifier.alerts), 1)
        self.assertEqual(len(checker.calls), 2)

    def test_three_confirmations_require_three_checks(self):
        config = WatchConfig(interval=60, jitter=0, confirmations=3, confirm_delay=1)
        watcher, checker, notifier, _ = build([Availability.AVAILABLE], config=config)
        watcher.run()
        self.assertEqual(len(checker.calls), 3)
        self.assertEqual(len(notifier.alerts), 1)


class SchedulingTests(unittest.TestCase):
    def test_interval_floor_is_enforced(self):
        config = WatchConfig(interval=5)
        self.assertEqual(config.interval, MIN_INTERVAL_SECONDS)

    def test_taken_reschedules_at_the_interval(self):
        watcher, _, _, clock = build([Availability.TAKEN])
        target = watcher.targets[0]
        watcher._handle(target)
        self.assertAlmostEqual(target.next_due - clock.monotonic(), 60.0, places=5)

    def test_inconclusive_checks_back_off_exponentially(self):
        watcher, _, _, clock = build([Availability.RATE_LIMITED])
        target = watcher.targets[0]
        delays = []
        for _ in range(3):
            watcher._handle(target)
            delays.append(target.next_due - clock.monotonic())
        self.assertLess(delays[0], delays[1])
        self.assertLess(delays[1], delays[2])

    def test_backoff_is_capped(self):
        config = WatchConfig(interval=60, jitter=0, confirmations=1, max_backoff=300)
        watcher, _, _, clock = build([Availability.UNKNOWN], config=config)
        target = watcher.targets[0]
        for _ in range(10):
            watcher._handle(target)
        self.assertLessEqual(target.next_due - clock.monotonic(), 300.0)

    def test_stop_ends_the_loop(self):
        watcher, _, _, _ = build([Availability.TAKEN])
        watcher.stop()
        watcher.run()
        self.assertTrue(watcher.stopped)

    def test_run_stops_after_alert_by_default(self):
        watcher, checker, _, _ = build([Availability.AVAILABLE])
        watcher.run()
        self.assertEqual(len(checker.calls), 1)
        self.assertTrue(watcher.targets[0].done)

    def test_multiple_usernames_are_staggered(self):
        clock = FakeClock()
        watcher = Watcher(
            ["alpha", "beta", "gamma"],
            ScriptedChecker(Availability.TAKEN),
            NotifierGroup([]),
            config=WatchConfig(interval=60, jitter=0, confirmations=1),
            sleep=clock.sleep,
            monotonic=clock.monotonic,
        )
        dues = [t.next_due for t in watcher.targets]
        self.assertEqual(sorted(dues), dues)
        self.assertNotEqual(dues[0], dues[1])

    def test_duplicate_usernames_are_collapsed(self):
        watcher = Watcher(
            ["same", "same"],
            ScriptedChecker(Availability.TAKEN),
            NotifierGroup([]),
        )
        self.assertEqual(len(watcher.targets), 1)


class StateTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = f"{self.tmp.name}/state.json"

    def test_alert_is_not_repeated_across_restarts(self):
        config = WatchConfig(interval=60, jitter=0, confirmations=1, stop_after_alert=False)

        state = StateStore(self.path)
        watcher, _, notifier, _ = build([Availability.AVAILABLE], config=config, state=state)
        watcher._handle(watcher.targets[0])
        self.assertEqual(len(notifier.alerts), 1)

        # A fresh process reading the same state file must stay quiet.
        state2 = StateStore(self.path)
        watcher2, _, notifier2, _ = build([Availability.AVAILABLE], config=config, state=state2)
        watcher2._handle(watcher2.targets[0])
        self.assertEqual(notifier2.alerts, [])

    def test_repeat_alert_overrides_the_dedupe(self):
        config = WatchConfig(
            interval=60, jitter=0, confirmations=1, stop_after_alert=False, repeat_alert=True
        )
        state = StateStore(self.path)
        watcher, _, notifier, _ = build([Availability.AVAILABLE], config=config, state=state)
        watcher._handle(watcher.targets[0])
        watcher._handle(watcher.targets[0])
        self.assertEqual(len(notifier.alerts), 2)

    def test_name_going_taken_again_clears_the_alert_flag(self):
        state = StateStore(self.path)
        state.record_check("someone", "available")
        state.record_notification("someone")
        self.assertTrue(state.already_notified("someone"))
        state.record_check("someone", "taken")
        self.assertFalse(state.already_notified("someone"))


class NotifierGroupTests(unittest.TestCase):
    def test_one_broken_channel_does_not_block_the_others(self):
        class Exploding(Notifier):
            name = "boom"

            def deliver(self, title, body, result):
                raise RuntimeError("webhook down")

        good = RecordingNotifier()
        group = NotifierGroup([Exploding(), good])
        delivered = group.send("t", "b", None)
        self.assertEqual(delivered, 1)
        self.assertEqual(len(good.alerts), 1)


if __name__ == "__main__":
    unittest.main()
