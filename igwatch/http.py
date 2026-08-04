"""A very small urllib wrapper.

igwatch deliberately depends on nothing outside the standard library, so this
module papers over the parts of urllib that are annoying: HTTPError being an
exception rather than a response, cookies, and gzip.
"""

from __future__ import annotations

import gzip
import http.cookiejar
import json
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_TIMEOUT = 20.0


class TransportError(Exception):
    """The request never produced an HTTP response (DNS, TLS, timeout...)."""


@dataclass
class Response:
    status: int
    headers: Mapping[str, str]
    body: bytes
    url: str

    @property
    def text(self) -> str:
        charset = "utf-8"
        content_type = self.headers.get("Content-Type", "")
        if "charset=" in content_type:
            charset = content_type.split("charset=", 1)[1].split(";")[0].strip()
        return self.body.decode(charset, errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


def _decompress(body: bytes, encoding: str) -> bytes:
    encoding = (encoding or "").lower()
    try:
        if encoding == "gzip":
            return gzip.decompress(body)
        if encoding == "deflate":
            return zlib.decompress(body, -zlib.MAX_WBITS)
    except (OSError, zlib.error):
        # Servers occasionally mislabel; fall back to the raw bytes.
        return body
    return body


class HttpClient:
    """Cookie-aware HTTP client with browser-ish defaults."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT,
        cookies: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.cookies: Dict[str, str] = dict(cookies or {})
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar)
        )

    def _cookie_header(self) -> Optional[str]:
        if not self.cookies:
            return None
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def _request(
        self,
        url: str,
        method: str,
        data: Optional[bytes],
        headers: Mapping[str, str],
    ) -> Response:
        merged = {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}
        merged.update(headers)
        cookie = self._cookie_header()
        if cookie and "Cookie" not in merged:
            merged["Cookie"] = cookie

        request = urllib.request.Request(url, data=data, headers=merged, method=method)
        try:
            with self._opener.open(request, timeout=self.timeout) as raw:
                body = _decompress(raw.read(), raw.headers.get("Content-Encoding", ""))
                return Response(
                    status=raw.status,
                    headers=dict(raw.headers),
                    body=body,
                    url=raw.geturl(),
                )
        except urllib.error.HTTPError as exc:  # 4xx/5xx still carry a body
            body = _decompress(exc.read(), exc.headers.get("Content-Encoding", ""))
            return Response(
                status=exc.code,
                headers=dict(exc.headers),
                body=body,
                url=exc.url or url,
            )
        except urllib.error.URLError as exc:
            raise TransportError(str(exc.reason)) from exc
        except (TimeoutError, OSError) as exc:
            raise TransportError(str(exc)) from exc

    def get(self, url: str, headers: Optional[Mapping[str, str]] = None) -> Response:
        merged = {
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        merged.update(headers or {})
        return self._request(url, "GET", None, merged)

    def post_json(
        self,
        url: str,
        payload: Any,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Response:
        merged = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }
        merged.update(headers or {})
        return self._request(url, "POST", json.dumps(payload).encode("utf-8"), merged)

    def post_text(
        self,
        url: str,
        payload: str,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Response:
        merged = {"Content-Type": "text/plain; charset=utf-8"}
        merged.update(headers or {})
        return self._request(url, "POST", payload.encode("utf-8"), merged)
