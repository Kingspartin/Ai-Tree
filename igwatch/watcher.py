"""The polling loop.

Design notes:

* Instagram punishes bursts far more than it punishes patience, so the loop
  jitters every sleep, keeps a hard floor under the interval, and backs off
  exponentially whenever a check comes back inconclusive.
* A single "available" answer is not trusted. The loop re-checks a few seconds
  later and only alerts when every confirmation agrees, which filters out the
  404s Instagram serves during a hiccup.
* Alerting is idempotent across restarts via the state file.
"""

from __future__ import annotations

import dataclasses
import logging
import random
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, Sequence

from .checker import AvailabilityChecker
from .models import Availability, CheckResult
from .notifiers import NotifierGroup
from .state import StateStore

log = logging.getLogger("igwatch.watch")

#: Anything faster than this gets you throttled (and helps nobody).
MIN_INTERVAL_SECONDS = 60.0


@dataclasses.dataclass
class WatchConfig:
    interval: float = 300.0
    jitter: float = 0.2
    confirmations: int = 2
    confirm_delay: float = 15.0
    max_backoff: float = 3600.0
    #: Minimum gap between any two outbound requests, across all usernames.
    request_spacing: float = 5.0
    stop_after_alert: bool = True
    repeat_alert: bool = False

    def __post_init__(self) -> None:
        if self.interval < MIN_INTERVAL_SECONDS:
            log.warning(
                "interval %.0fs is below the %.0fs floor; using the floor "
                "so Instagram doesn't rate-limit you",
                self.interval,
                MIN_INTERVAL_SECONDS,
            )
            self.interval = MIN_INTERVAL_SECONDS
        self.jitter = min(max(self.jitter, 0.0), 0.9)
        self.confirmations = max(int(self.confirmations), 1)
        self.max_backoff = max(self.max_backoff, self.interval)


@dataclasses.dataclass
class Target:
    username: str
    next_due: float = 0.0
    fail_streak: int = 0
    checks: int = 0
    done: bool = False
    last_status: Optional[Availability] = None


class Watcher:
    def __init__(
        self,
        usernames: Sequence[str],
        checker: AvailabilityChecker,
        notifiers: NotifierGroup,
        config: Optional[WatchConfig] = None,
        state: Optional[StateStore] = None,
        sleep: Optional[Callable[[float], bool]] = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not usernames:
            raise ValueError("nothing to watch")
        self.config = config or WatchConfig()
        self.checker = checker
        self.notifiers = notifiers
        self.state = state
        self._monotonic = monotonic
        self._stop = threading.Event()
        self._sleep = sleep or self._default_sleep
        self._last_request_at = 0.0

        now = self._monotonic()
        # Stagger the first round so several usernames don't fire at once.
        self.targets: List[Target] = [
            Target(username=name, next_due=now + index * self.config.request_spacing)
            for index, name in enumerate(dict.fromkeys(usernames))
        ]

    # -- lifecycle ----------------------------------------------------------

    def stop(self) -> None:
        """Ask the loop to wind down (safe to call from a signal handler)."""

        self._stop.set()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def _default_sleep(self, seconds: float) -> bool:
        """Interruptible sleep. Returns True if we were asked to stop."""

        if seconds <= 0:
            return self._stop.is_set()
        return self._stop.wait(seconds)

    # -- checking -----------------------------------------------------------

    def _paced_check(self, username: str) -> CheckResult:
        gap = self.config.request_spacing - (self._monotonic() - self._last_request_at)
        if gap > 0:
            self._sleep(gap)
        result = self.checker.check(username)
        self._last_request_at = self._monotonic()
        return result

    def _confirm(self, username: str) -> Optional[CheckResult]:
        """Re-check an apparently free username. None means not confirmed."""

        needed = self.config.confirmations - 1
        if needed <= 0:
            return self._paced_check(username)

        last: Optional[CheckResult] = None
        for attempt in range(needed):
            log.info(
                "@%s looks free - confirming (%d/%d)", username, attempt + 1, needed
            )
            if self._sleep(self.config.confirm_delay):
                return None
            last = self._paced_check(username)
            if last.status is not Availability.AVAILABLE:
                log.info("confirmation disagreed: %s", last)
                return None
        return last

    def check_once(self, username: str) -> CheckResult:
        """One check, plus confirmations when it looks available."""

        result = self._paced_check(username)
        if result.status is Availability.AVAILABLE and self.config.confirmations > 1:
            confirmed = self._confirm(username)
            if confirmed is None:
                return dataclasses.replace(
                    result,
                    status=Availability.UNKNOWN,
                    detail="looked available but confirmation did not agree",
                )
            return confirmed
        return result

    # -- alerting -----------------------------------------------------------

    def alert(self, result: CheckResult) -> None:
        when = datetime.fromtimestamp(result.checked_at).strftime("%Y-%m-%d %H:%M:%S")
        title = f"@{result.username} is available on Instagram"
        body = (
            f"Instagram username @{result.username} looks free as of {when}.\n"
            f"Claim it: {result.profile_url}\n"
            f"(detected via {result.strategy}"
            + (f", HTTP {result.http_status}" if result.http_status else "")
            + ")\n"
            "Heads up: Instagram sometimes holds recently-deleted or reserved "
            "names, so signup can still refuse it."
        )
        delivered = self.notifiers.send(title, body, result)
        log.info("alert delivered to %d/%d channels", delivered, len(self.notifiers))
        if self.state is not None:
            self.state.record_notification(result.username)
            self.state.save()

    # -- scheduling ---------------------------------------------------------

    def _delay_for(self, target: Target, status: Availability) -> float:
        if status.is_conclusive:
            target.fail_streak = 0
            base = self.config.interval
        else:
            target.fail_streak += 1
            factor = 2 ** min(target.fail_streak, 8)
            extra = self.config.interval * 0.5 if status is Availability.RATE_LIMITED else 0
            base = min(self.config.interval * factor + extra, self.config.max_backoff)
        spread = base * self.config.jitter
        return max(1.0, base + random.uniform(-spread, spread))

    def _handle(self, target: Target) -> None:
        result = self.check_once(target.username)
        target.checks += 1
        target.last_status = result.status

        if self.state is not None:
            self.state.record_check(target.username, result.status.value)
            self.state.save()

        if result.status is Availability.AVAILABLE:
            already = self.state.already_notified(target.username) if self.state else False
            if already and not self.config.repeat_alert:
                log.info("@%s still free; already alerted, staying quiet", target.username)
            else:
                self.alert(result)
            if self.config.stop_after_alert:
                target.done = True
                return
        else:
            log.info("%s", result)

        target.next_due = self._monotonic() + self._delay_for(target, result.status)

    def run(self) -> Dict[str, Optional[Availability]]:
        """Poll until every target is done or :meth:`stop` is called."""

        log.info(
            "watching %s every ~%.0fs (%d confirmation%s, alerts: %s)",
            ", ".join("@" + t.username for t in self.targets),
            self.config.interval,
            self.config.confirmations,
            "" if self.config.confirmations == 1 else "s",
            ", ".join(self.notifiers.names) or "none",
        )

        while not self._stop.is_set():
            pending = [t for t in self.targets if not t.done]
            if not pending:
                break
            nxt = min(pending, key=lambda t: t.next_due)
            wait = nxt.next_due - self._monotonic()
            if wait > 0 and self._sleep(wait):
                break
            self._handle(nxt)

        return {t.username: t.last_status for t in self.targets}
