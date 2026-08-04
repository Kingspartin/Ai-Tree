"""Availability checks against Instagram's public endpoints.

Two independent strategies are implemented:

``api``
    ``/api/v1/users/web_profile_info/`` — the JSON endpoint the website itself
    uses to render a profile. Cheap, unambiguous, but the one Instagram
    throttles first.

``page``
    A plain GET of ``instagram.com/<username>/``. Slower and noisier, but it
    keeps working for a while after the JSON endpoint starts refusing
    anonymous callers.

``auto`` (the default) runs ``api`` and falls back to ``page`` whenever the
first strategy comes back inconclusive.
"""

from __future__ import annotations

import re
from typing import Optional, Sequence

from .http import HttpClient, Response, TransportError
from .models import Availability, CheckResult

#: Public web app id the instagram.com frontend sends. Without it the JSON
#: endpoint answers 401 for anonymous callers.
IG_APP_ID = "936619743392459"

API_URL = "https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
PAGE_URL = "https://www.instagram.com/{username}/"

USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,30}$")

#: Text Instagram serves on its "no such profile" page (200, not 404).
_NOT_FOUND_MARKERS = (
    "Sorry, this page isn't available.",
    "Sorry, this page isn&#x27;t available.",
    "the link you followed may be broken",
)

_LOGIN_MARKERS = (
    "/accounts/login",
    "loginForm",
)


class InvalidUsername(ValueError):
    """The string cannot be an Instagram username, so no point asking."""


def normalize_username(raw: str) -> str:
    """Accept pastes like ``@name``, a profile URL, or plain ``name``."""

    value = raw.strip()
    if value.startswith("@"):
        value = value[1:]
    if "instagram.com" in value:
        value = value.split("instagram.com", 1)[1]
        value = value.split("?", 1)[0].split("#", 1)[0]
        value = value.strip("/").split("/")[0]
    value = value.strip().strip("/")
    if not USERNAME_RE.match(value):
        raise InvalidUsername(
            f"{raw!r} is not a valid Instagram username "
            "(1-30 characters, letters/digits/period/underscore only)"
        )
    return value.lower()


class AvailabilityChecker:
    """Runs availability strategies against Instagram."""

    def __init__(
        self,
        client: Optional[HttpClient] = None,
        strategy: str = "auto",
        session_id: Optional[str] = None,
    ) -> None:
        if strategy not in ("auto", "api", "page"):
            raise ValueError(f"unknown strategy: {strategy!r}")
        self.strategy = strategy
        cookies = {"sessionid": session_id} if session_id else None
        self.client = client or HttpClient(cookies=cookies)
        if client is not None and session_id:
            self.client.cookies["sessionid"] = session_id

    # -- public API ---------------------------------------------------------

    def check(self, username: str) -> CheckResult:
        order: Sequence[str]
        if self.strategy == "auto":
            order = ("api", "page")
        else:
            order = (self.strategy,)

        last: Optional[CheckResult] = None
        for name in order:
            result = self._run(name, username)
            if result.status.is_conclusive:
                return result
            # Keep the most informative inconclusive answer around.
            if last is None or (
                last.status is Availability.UNKNOWN
                and result.status is Availability.RATE_LIMITED
            ):
                last = result
        assert last is not None
        return last

    # -- strategies ---------------------------------------------------------

    def _run(self, name: str, username: str) -> CheckResult:
        try:
            if name == "api":
                return self._check_api(username)
            return self._check_page(username)
        except TransportError as exc:
            return CheckResult(
                username=username,
                status=Availability.UNKNOWN,
                strategy=name,
                detail=f"network error: {exc}",
            )

    def _check_api(self, username: str) -> CheckResult:
        response = self.client.get(
            API_URL.format(username=username),
            headers={
                "X-IG-App-ID": IG_APP_ID,
                "Accept": "application/json",
                "Referer": PAGE_URL.format(username=username),
            },
        )
        return self._interpret_api(username, response)

    def _interpret_api(self, username: str, response: Response) -> CheckResult:
        def result(status: Availability, detail: str = "") -> CheckResult:
            return CheckResult(
                username=username,
                status=status,
                strategy="api",
                http_status=response.status,
                detail=detail,
            )

        if response.status == 404:
            return result(Availability.AVAILABLE, "profile endpoint returned 404")
        if response.status == 429:
            return result(Availability.RATE_LIMITED, "throttled by Instagram")
        if response.status in (401, 403):
            return result(
                Availability.RATE_LIMITED,
                "anonymous access refused; slow down or supply --session-id",
            )
        if response.status >= 500:
            return result(Availability.UNKNOWN, "Instagram server error")
        if response.status != 200:
            return result(Availability.UNKNOWN, f"unexpected status {response.status}")

        try:
            payload = response.json()
        except ValueError:
            return result(Availability.UNKNOWN, "response was not JSON (login wall?)")

        if not isinstance(payload, dict):
            return result(Availability.UNKNOWN, "unexpected JSON shape")

        data = payload.get("data")
        if isinstance(data, dict) and "user" in data:
            user = data.get("user")
            if user in (None, {}):
                return result(Availability.AVAILABLE, "no user object in payload")
            if isinstance(user, dict):
                pk = user.get("id") or user.get("pk") or ""
                return result(Availability.TAKEN, f"user id {pk}" if pk else "user exists")

        message = str(payload.get("message", "")).lower()
        if "not found" in message:
            return result(Availability.AVAILABLE, "user not found")
        if "checkpoint" in message or "login_required" in message:
            return result(Availability.RATE_LIMITED, f"blocked: {message}")

        return result(Availability.UNKNOWN, "could not interpret payload")

    def _check_page(self, username: str) -> CheckResult:
        response = self.client.get(PAGE_URL.format(username=username))
        return self._interpret_page(username, response)

    def _interpret_page(self, username: str, response: Response) -> CheckResult:
        def result(status: Availability, detail: str = "") -> CheckResult:
            return CheckResult(
                username=username,
                status=status,
                strategy="page",
                http_status=response.status,
                detail=detail,
            )

        if response.status == 404:
            return result(Availability.AVAILABLE, "profile page returned 404")
        if response.status == 429:
            return result(Availability.RATE_LIMITED, "throttled by Instagram")
        if response.status >= 500:
            return result(Availability.UNKNOWN, "Instagram server error")
        if response.status != 200:
            return result(Availability.UNKNOWN, f"unexpected status {response.status}")

        # A redirect to the login form tells us nothing about the username.
        final = response.url or ""
        if "/accounts/login" in final:
            return result(Availability.UNKNOWN, "redirected to login wall")

        body = response.text
        lowered = body.lower()

        for marker in _NOT_FOUND_MARKERS:
            if marker.lower() in lowered:
                return result(Availability.AVAILABLE, "page says profile is unavailable")

        if f'"username":"{username}"' in lowered or f'@{username}' in lowered:
            return result(Availability.TAKEN, "profile page rendered")

        for marker in _LOGIN_MARKERS:
            if marker.lower() in lowered:
                return result(Availability.UNKNOWN, "login wall served instead of profile")

        # 200 with a real page body and no "unavailable" notice: treat as taken,
        # but say so, since this is the least certain branch.
        return result(Availability.TAKEN, "page loaded without a not-found notice")
