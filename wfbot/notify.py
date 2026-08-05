"""Desktop notifications, clipboard, and the in-game whisper templates."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
import sys
from typing import Any

from .analysis import Opportunity
from .config import NotifyConfig

log = logging.getLogger(__name__)


def whisper(user: str, item_name: str, platinum: int, *, side: str = "buy", rank: int | None = None) -> str:
    """The message warframe.market expects you to paste into Warframe's chat."""
    verb = "buy" if side == "buy" else "sell"
    suffix = f" (rank {rank})" if rank is not None else ""
    return (
        f'/w {user} Hi! I want to {verb}: "{item_name}"{suffix} '
        f"for {platinum} platinum. (warframe.market)"
    )


def copy_to_clipboard(text: str) -> bool:
    """Best effort copy; every path is optional and failure is never fatal."""
    try:
        import pyperclip  # type: ignore

        pyperclip.copy(text)
        return True
    except Exception:  # noqa: BLE001 - pyperclip raises many unrelated types
        pass

    system = platform.system()
    commands: list[list[str]] = []
    if system == "Windows":
        commands = [["clip"]]
    elif system == "Darwin":
        commands = [["pbcopy"]]
    else:
        commands = [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]

    for command in commands:
        if not shutil.which(command[0]):
            continue
        try:
            subprocess.run(command, input=text.encode("utf-8"), check=True, timeout=5)
            return True
        except (subprocess.SubprocessError, OSError):
            continue
    return False


def desktop_notify(title: str, message: str) -> bool:
    system = platform.system()
    try:
        if system == "Darwin" and shutil.which("osascript"):
            body = message.replace('"', "'")
            head = title.replace('"', "'")
            subprocess.run(
                ["osascript", "-e", f'display notification "{body}" with title "{head}"'],
                check=True,
                timeout=5,
            )
            return True
        if system == "Linux" and shutil.which("notify-send"):
            subprocess.run(["notify-send", title, message], check=True, timeout=5)
            return True
        if system == "Windows":
            # Optional extras; neither is a hard dependency.
            try:
                from win10toast import ToastNotifier  # type: ignore

                ToastNotifier().show_toast(title, message, duration=8, threaded=True)
                return True
            except Exception:  # noqa: BLE001
                pass
            try:
                from plyer import notification  # type: ignore

                notification.notify(title=title, message=message, timeout=8)
                return True
            except Exception:  # noqa: BLE001
                pass
    except (subprocess.SubprocessError, OSError) as exc:
        log.debug("desktop notification failed: %s", exc)
    return False


class Notifier:
    """Console + desktop output with a per-key cooldown."""

    def __init__(self, config: NotifyConfig, database: Any | None = None) -> None:
        self.config = config
        self.db = database

    def _allowed(self, key: str) -> bool:
        if not self.db:
            return True
        return self.db.should_notify(key, self.config.cooldown_seconds)

    def send(self, title: str, message: str, *, key: str | None = None) -> None:
        if key and not self._allowed(key):
            return
        if self.config.console:
            stream = sys.stdout
            bell = "\a" if stream.isatty() else ""
            print(f"{bell}[{title}] {message}", file=stream, flush=True)
        if self.config.desktop:
            desktop_notify(title, message)

    def opportunity(self, opportunity: Opportunity) -> None:
        if opportunity.score < self.config.min_score:
            return
        key = f"opp:{opportunity.item_url}:{opportunity.mod_rank}:{opportunity.buy_at}"
        message = (
            f"{opportunity.describe()} - {opportunity.units}x, "
            f"{opportunity.total_profit}p total, confidence {opportunity.confidence:.0%}"
        )
        self.send("wfbot opportunity", message, key=key)
        if self.config.clipboard and opportunity.buy_from:
            text = whisper(
                opportunity.buy_from,
                opportunity.item_name,
                opportunity.buy_at,
                side="buy",
                rank=opportunity.mod_rank,
            )
            if copy_to_clipboard(text):
                print(f"    copied to clipboard: {text}")
            else:
                print(f"    whisper: {text}")


def supports_colour() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
