"""Read-only tail of Warframe's EE.log.

The game writes a plain-text log. Reading it tells the bot when you are in-game
and when somebody is trying to trade with you, without touching the client:
no hooks, no injection, no synthetic input. Community overlays have read this
file for years.

The log markers change between game updates, so every pattern lives in the
config file rather than in this module. Grep your own EE.log and add what you
find.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from .config import LogWatchConfig, default_ee_log

log = logging.getLogger(__name__)


@dataclass
class LogEvent:
    kind: str  # whisper | trade | game_start | game_stop
    line: str
    user: str | None = None
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LogWatcher:
    """Follows a growing file, surviving truncation and rotation."""

    def __init__(self, config: LogWatchConfig) -> None:
        self.config = config
        self.path = Path(config.path).expanduser() if config.path else default_ee_log()
        self._position = 0
        self._signature: tuple[int, int] | None = None
        self.game_running: bool | None = None
        self._patterns: list[tuple[str, re.Pattern[str]]] = []
        for kind, sources in (
            ("whisper", config.whisper_patterns),
            ("trade", config.trade_patterns),
            ("game_start", config.game_start_patterns),
            ("game_stop", config.game_stop_patterns),
        ):
            for source in sources:
                try:
                    self._patterns.append((kind, re.compile(source, re.IGNORECASE)))
                except re.error as exc:
                    log.warning("ignoring invalid %s pattern %r: %s", kind, source, exc)

    # ------------------------------------------------------------------ reading

    def available(self) -> bool:
        return bool(self.path and self.path.exists())

    def _signature_of(self, path: Path) -> tuple[int, int] | None:
        try:
            info = path.stat()
        except OSError:
            return None
        # st_ino is 0 on some Windows filesystems, so pair it with the creation
        # time to still notice a replaced file.
        return (int(info.st_ino), int(info.st_ctime))

    def seek_to_end(self) -> None:
        if not self.available():
            return
        try:
            self._position = self.path.stat().st_size  # type: ignore[union-attr]
            self._signature = self._signature_of(self.path)  # type: ignore[arg-type]
        except OSError:
            self._position = 0

    def read_new_lines(self) -> list[str]:
        if not self.available():
            return []
        path = self.path
        assert path is not None
        signature = self._signature_of(path)
        try:
            size = path.stat().st_size
        except OSError:
            return []

        if self._signature is not None and signature != self._signature:
            # The game restarted and rewrote the log.
            self._position = 0
        elif size < self._position:
            # Truncated in place.
            self._position = 0
        self._signature = signature

        if size == self._position:
            return []
        try:
            # Warframe keeps this file open while running, so on Windows it must
            # be opened for reading only, and decode errors must be tolerated.
            with open(path, "r", encoding=self.config.encoding, errors="replace") as handle:
                handle.seek(self._position)
                data = handle.read()
                self._position = handle.tell()
        except OSError as exc:
            log.debug("could not read %s: %s", path, exc)
            return []
        return [line for line in data.splitlines() if line.strip()]

    def classify(self, line: str) -> LogEvent | None:
        for kind, pattern in self._patterns:
            match = pattern.search(line)
            if not match:
                continue
            user = None
            if match.groupdict().get("user"):
                # Chat lines wrap names in brackets and trail them with
                # punctuation: "[DE]Player," and "Tenno:" are the same person.
                user = match.group("user").strip().lstrip("[(<").rstrip(">)]:,.")
            if kind == "game_start":
                self.game_running = True
            elif kind == "game_stop":
                self.game_running = False
            return LogEvent(kind=kind, line=line.strip(), user=user)
        return None

    def poll(self) -> list[LogEvent]:
        events = []
        for line in self.read_new_lines():
            event = self.classify(line)
            if event:
                events.append(event)
        return events

    def follow(self, stop: threading.Event | None = None) -> Iterator[LogEvent]:
        """Yield events until `stop` is set. Waits patiently for a missing log."""
        stop = stop or threading.Event()
        self.seek_to_end()
        warned = False
        while not stop.is_set():
            if not self.available():
                if not warned:
                    log.warning("EE.log not found at %s; waiting for it to appear", self.path)
                    warned = True
                stop.wait(5.0)
                continue
            warned = False
            for event in self.poll():
                yield event
            stop.wait(self.config.poll_interval)

    def run_in_background(
        self, handler: Callable[[LogEvent], None], stop: threading.Event | None = None
    ) -> threading.Thread:
        stop = stop or threading.Event()

        def loop() -> None:
            for event in self.follow(stop):
                try:
                    handler(event)
                except Exception:  # noqa: BLE001 - a bad handler must not kill the tail
                    log.exception("log event handler failed")

        thread = threading.Thread(target=loop, name="wfbot-logwatch", daemon=True)
        thread.start()
        return thread


def describe_paths() -> str:
    guess = default_ee_log()
    return str(guess) if guess else "not found (set logwatch.path in your config)"


def tail_once(config: LogWatchConfig, seconds: float = 5.0) -> list[LogEvent]:
    """Small helper for `wfbot logwatch --test`."""
    watcher = LogWatcher(config)
    watcher.seek_to_end()
    deadline = time.monotonic() + seconds
    events: list[LogEvent] = []
    while time.monotonic() < deadline:
        events.extend(watcher.poll())
        time.sleep(0.5)
    return events
