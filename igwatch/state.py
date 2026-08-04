"""Small JSON state file so restarts don't re-alert or lose history."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

log = logging.getLogger("igwatch.state")


def default_state_path() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    root = Path(base) if base else Path.home() / ".local" / "state"
    return root / "igwatch" / "state.json"


class StateStore:
    """Per-username record of the last check and the last alert.

    Writes are atomic (temp file + replace) so a kill -9 mid-write cannot leave
    a truncated file behind.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else default_state_path()
        self.data: Dict[str, Any] = {"version": 1, "usernames": {}}
        self.load()

    def load(self) -> None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return
        except OSError as exc:
            log.warning("could not read state file %s: %s", self.path, exc)
            return
        try:
            parsed = json.loads(raw)
        except ValueError:
            log.warning("state file %s is corrupt; starting fresh", self.path)
            return
        if isinstance(parsed, dict) and isinstance(parsed.get("usernames"), dict):
            self.data = parsed

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".igwatch-")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, indent=2, sort_keys=True)
            os.replace(tmp, self.path)
        except OSError as exc:
            log.warning("could not write state file %s: %s", self.path, exc)

    # -- record helpers -----------------------------------------------------

    def get(self, username: str) -> Dict[str, Any]:
        return self.data.setdefault("usernames", {}).setdefault(
            username,
            {
                "checks": 0,
                "last_status": None,
                "last_checked_at": None,
                "first_seen_available_at": None,
                "notified_at": None,
            },
        )

    def record_check(self, username: str, status: str) -> Dict[str, Any]:
        record = self.get(username)
        record["checks"] = int(record.get("checks", 0)) + 1
        record["last_status"] = status
        record["last_checked_at"] = time.time()
        if status == "available":
            record.setdefault("first_seen_available_at", None)
            if not record["first_seen_available_at"]:
                record["first_seen_available_at"] = time.time()
        else:
            record["first_seen_available_at"] = None
            # A username that came back is fair game for a fresh alert later.
            record["notified_at"] = None
        return record

    def already_notified(self, username: str) -> bool:
        return bool(self.get(username).get("notified_at"))

    def record_notification(self, username: str) -> None:
        self.get(username)["notified_at"] = time.time()
