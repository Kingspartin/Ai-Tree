"""Alert channels.

Every notifier is fail-soft: a broken webhook or missing ``notify-send`` must
never take down a watcher that has been running for three weeks. Failures are
logged and the loop continues.
"""

from __future__ import annotations

import logging
import os
import platform
import shlex
import shutil
import smtplib
import subprocess
import urllib.parse
from email.message import EmailMessage
from typing import List, Optional, Sequence

from .http import HttpClient, TransportError
from .models import CheckResult

log = logging.getLogger("igwatch.notify")


class Notifier:
    """Base class. Subclasses implement :meth:`deliver`."""

    name = "notifier"

    def deliver(self, title: str, body: str, result: Optional[CheckResult]) -> None:
        raise NotImplementedError

    def send(self, title: str, body: str, result: Optional[CheckResult] = None) -> bool:
        try:
            self.deliver(title, body, result)
            return True
        except Exception as exc:  # noqa: BLE001 - notifiers must not crash the watcher
            log.warning("%s notifier failed: %s", self.name, exc)
            return False


class ConsoleNotifier(Notifier):
    name = "console"

    def deliver(self, title: str, body: str, result: Optional[CheckResult]) -> None:
        line = "=" * 60
        print(f"\n{line}\n{title}\n{body}\n{line}\n", flush=True)


class DesktopNotifier(Notifier):
    """macOS ``osascript`` / Linux ``notify-send`` / Windows toast."""

    name = "desktop"

    def deliver(self, title: str, body: str, result: Optional[CheckResult]) -> None:
        system = platform.system()
        if system == "Darwin":
            script = (
                f'display notification {_osa_quote(body)} '
                f'with title {_osa_quote(title)} sound name "Glass"'
            )
            subprocess.run(["osascript", "-e", script], check=True, timeout=15)
            return
        if system == "Linux":
            if not shutil.which("notify-send"):
                raise RuntimeError("notify-send not installed (try: apt install libnotify-bin)")
            subprocess.run(
                ["notify-send", "--urgency=critical", title, body],
                check=True,
                timeout=15,
            )
            return
        if system == "Windows":
            ps = (
                "[reflection.assembly]::loadwithpartialname('System.Windows.Forms')|Out-Null;"
                "$n=New-Object System.Windows.Forms.NotifyIcon;"
                "$n.Icon=[System.Drawing.SystemIcons]::Information;"
                "$n.BalloonTipTitle=" + _ps_quote(title) + ";"
                "$n.BalloonTipText=" + _ps_quote(body) + ";"
                "$n.Visible=$true;$n.ShowBalloonTip(20000);Start-Sleep -s 6"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=40)
            return
        raise RuntimeError(f"no desktop notification support for {system}")


class WebhookNotifier(Notifier):
    """Generic JSON webhook, with Slack and Discord shapes detected by URL."""

    name = "webhook"

    def __init__(self, url: str, client: Optional[HttpClient] = None) -> None:
        self.url = url
        self.client = client or HttpClient()

    def _payload(self, title: str, body: str, result: Optional[CheckResult]) -> dict:
        host = urllib.parse.urlparse(self.url).netloc.lower()
        text = f"{title}\n{body}"
        if "hooks.slack.com" in host:
            return {"text": text}
        if "discord.com" in host or "discordapp.com" in host:
            return {"content": text[:1900]}
        payload = {"title": title, "body": body, "text": text}
        if result is not None:
            payload.update(
                {
                    "username": result.username,
                    "status": result.status.value,
                    "profile_url": result.profile_url,
                    "checked_at": result.checked_at,
                }
            )
        return payload

    def deliver(self, title: str, body: str, result: Optional[CheckResult]) -> None:
        response = self.client.post_json(self.url, self._payload(title, body, result))
        if response.status >= 400:
            raise RuntimeError(f"webhook returned HTTP {response.status}: {response.text[:200]}")


class NtfyNotifier(Notifier):
    """Push to a phone via ntfy.sh (or a self-hosted ntfy server)."""

    name = "ntfy"

    def __init__(self, topic: str, client: Optional[HttpClient] = None) -> None:
        self.url = topic if topic.startswith(("http://", "https://")) else f"https://ntfy.sh/{topic}"
        self.client = client or HttpClient()

    def deliver(self, title: str, body: str, result: Optional[CheckResult]) -> None:
        headers = {
            # HTTP headers must be latin-1; ntfy titles are ours, but stay safe.
            "Title": title.encode("ascii", "ignore").decode() or "igwatch",
            "Priority": "high",
            "Tags": "tada" if result and result.status.value == "available" else "eyes",
            "Content-Type": "text/plain",
        }
        if result is not None:
            headers["Click"] = result.profile_url
        response = self.client.post_text(self.url, body, headers=headers)
        if response.status >= 400:
            raise RuntimeError(f"ntfy returned HTTP {response.status}")


class EmailNotifier(Notifier):
    """SMTP mail. Credentials come from the environment, never the CLI."""

    name = "email"

    def __init__(self, to_addr: str) -> None:
        self.to_addr = to_addr
        self.host = os.environ.get("IGWATCH_SMTP_HOST", "")
        self.port = int(os.environ.get("IGWATCH_SMTP_PORT", "587"))
        self.user = os.environ.get("IGWATCH_SMTP_USER", "")
        self.password = os.environ.get("IGWATCH_SMTP_PASSWORD", "")
        self.from_addr = os.environ.get("IGWATCH_SMTP_FROM", self.user or to_addr)
        self.use_ssl = os.environ.get("IGWATCH_SMTP_SSL", "").lower() in ("1", "true", "yes")
        if not self.host:
            raise ValueError(
                "email alerts need IGWATCH_SMTP_HOST "
                "(plus IGWATCH_SMTP_USER / IGWATCH_SMTP_PASSWORD for authenticated servers)"
            )

    def deliver(self, title: str, body: str, result: Optional[CheckResult]) -> None:
        message = EmailMessage()
        message["Subject"] = title
        message["From"] = self.from_addr
        message["To"] = self.to_addr
        message.set_content(body)

        if self.use_ssl:
            server = smtplib.SMTP_SSL(self.host, self.port, timeout=30)
        else:
            server = smtplib.SMTP(self.host, self.port, timeout=30)
        with server:
            if not self.use_ssl:
                try:
                    server.starttls()
                except smtplib.SMTPException:
                    log.debug("STARTTLS unavailable on %s; continuing unencrypted", self.host)
            if self.user:
                server.login(self.user, self.password)
            server.send_message(message)


class CommandNotifier(Notifier):
    """Run a shell command. ``{username}``/``{url}``/``{status}``/``{title}``/
    ``{body}`` are substituted before execution."""

    name = "exec"

    def __init__(self, template: str) -> None:
        self.template = template

    def deliver(self, title: str, body: str, result: Optional[CheckResult]) -> None:
        values = {
            "title": title,
            "body": body,
            "username": result.username if result else "",
            "url": result.profile_url if result else "",
            "status": result.status.value if result else "",
        }
        parts = [part.format(**values) for part in shlex.split(self.template)]
        completed = subprocess.run(parts, timeout=60)
        if completed.returncode != 0:
            raise RuntimeError(f"command exited {completed.returncode}")


class NotifierGroup:
    """Fan a single alert out to every configured channel."""

    def __init__(self, notifiers: Sequence[Notifier]) -> None:
        self.notifiers: List[Notifier] = list(notifiers)

    def __len__(self) -> int:
        return len(self.notifiers)

    @property
    def names(self) -> List[str]:
        return [n.name for n in self.notifiers]

    def send(self, title: str, body: str, result: Optional[CheckResult] = None) -> int:
        """Returns how many channels accepted the alert."""

        delivered = 0
        for notifier in self.notifiers:
            if notifier.send(title, body, result):
                delivered += 1
        if delivered == 0 and self.notifiers:
            log.error("every notifier failed for: %s", title)
        return delivered


def _osa_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


__all__ = [
    "Notifier",
    "ConsoleNotifier",
    "DesktopNotifier",
    "WebhookNotifier",
    "NtfyNotifier",
    "EmailNotifier",
    "CommandNotifier",
    "NotifierGroup",
    "TransportError",
]
