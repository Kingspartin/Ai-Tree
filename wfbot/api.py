"""warframe.market v1 API client: rate limited, cached, retrying."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import stat
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Sequence, TypeVar
from concurrent.futures import ThreadPoolExecutor

import requests

from . import USER_AGENT
from .config import ApiConfig
from .models import Item, ItemStats, OrderBook

log = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class WFMError(RuntimeError):
    """Any failure talking to warframe.market."""


class AuthError(WFMError):
    """Missing, rejected or expired credentials."""


class NotFound(WFMError):
    """The requested item or resource does not exist."""


class TokenBucket:
    """Shared request budget so every thread respects one global rate."""

    def __init__(self, rate: float, burst: float | None = None) -> None:
        self.rate = max(rate, 0.1)
        self.capacity = burst if burst is not None else max(self.rate, 1.0)
        self._tokens = self.capacity
        self._updated = time.monotonic()
        self._lock = threading.Lock()

    def take(self, amount: float = 1.0) -> None:
        while True:
            with self._lock:
                current = time.monotonic()
                self._tokens = min(
                    self.capacity, self._tokens + (current - self._updated) * self.rate
                )
                self._updated = current
                if self._tokens >= amount:
                    self._tokens -= amount
                    return
                wait = (amount - self._tokens) / self.rate
            time.sleep(min(wait, 1.0))

    def penalise(self, seconds: float) -> None:
        """Drain the bucket after a 429 so the whole pool backs off together."""
        with self._lock:
            self._tokens = -abs(seconds) * self.rate


class DiskCache:
    """Small JSON cache on disk; the API data is public and cheap to re-fetch."""

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self.directory / f"{digest}.json"

    def get(self, key: str, ttl: float) -> Any | None:
        if ttl <= 0:
            return None
        path = self._path(key)
        try:
            age = time.time() - path.stat().st_mtime
        except OSError:
            return None
        if age > ttl:
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._path(key)
        tmp = path.with_suffix(".tmp")
        try:
            with self._lock:
                with open(tmp, "w", encoding="utf-8") as handle:
                    json.dump(value, handle)
                os.replace(tmp, path)
        except OSError as exc:  # a broken cache must never break a scan
            log.debug("cache write failed for %s: %s", key, exc)

    def clear(self) -> int:
        removed = 0
        for path in self.directory.glob("*.json"):
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
        return removed


class WarframeMarketClient:
    """Read and write warframe.market data.

    Read endpoints are cached and safe to hammer within the rate limit. Write
    endpoints only ever touch orders belonging to the authenticated account.
    """

    def __init__(
        self,
        config: ApiConfig | None = None,
        *,
        cache_dir: Path | None = None,
        token_path: Path | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config or ApiConfig()
        self.cache = DiskCache(cache_dir) if cache_dir else None
        self.token_path = Path(token_path) if token_path else None
        self.bucket = TokenBucket(self.config.requests_per_second)
        self.session = session or requests.Session()
        self.token: str | None = None
        self.user_name: str | None = None
        if self.token_path:
            self._load_token()

    # ---------------------------------------------------------------- plumbing

    def _headers(self, authenticated: bool = False) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; utf-8",
            "User-Agent": USER_AGENT,
            "platform": self.config.platform,
            "language": self.config.language,
            "accept-language": self.config.language,
        }
        if authenticated:
            if not self.token:
                raise AuthError("not signed in - run 'wfbot login' first")
            headers["Authorization"] = f"JWT {self.token}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        authenticated: bool = False,
        cache_ttl: float = 0,
    ) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{self.config.base_url}{path}"
        cache_key = f"{method}:{url}:{self.config.platform}"
        if method == "GET" and self.cache and cache_ttl > 0:
            cached = self.cache.get(cache_key, cache_ttl)
            if cached is not None:
                return cached

        last_error: Exception | None = None
        for attempt in range(self.config.max_retries):
            self.bucket.take()
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=self._headers(authenticated),
                    data=json.dumps(payload) if payload is not None else None,
                    timeout=self.config.timeout,
                )
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(min(2**attempt, 16))
                continue

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After") or 2**attempt)
                self.bucket.penalise(retry_after)
                last_error = WFMError("rate limited by warframe.market")
                time.sleep(min(retry_after, 30))
                continue
            if response.status_code in (401, 403):
                # The JWT expired or was rejected; drop it so the next call
                # asks for credentials instead of retrying a dead token.
                if authenticated:
                    self.forget_token()
                raise AuthError(
                    f"warframe.market rejected the request ({response.status_code}). "
                    "Sign in again with 'wfbot login'."
                )
            if response.status_code == 404:
                raise NotFound(f"not found: {url}")
            if response.status_code >= 500:
                last_error = WFMError(f"server error {response.status_code} from {url}")
                time.sleep(min(2**attempt, 16))
                continue
            if response.status_code >= 400:
                raise WFMError(f"HTTP {response.status_code} from {url}: {response.text[:200]}")

            self._capture_token(response)
            try:
                data = response.json()
            except ValueError as exc:
                raise WFMError(f"invalid JSON from {url}") from exc
            if method == "GET" and self.cache and cache_ttl > 0:
                self.cache.set(cache_key, data)
            return data

        raise WFMError(f"giving up on {method} {url}: {last_error}")

    def map(self, func: Callable[[T], R], items: Sequence[T]) -> Iterator[tuple[T, R | None, Exception | None]]:
        """Run `func` over items on a small pool; the rate limiter is shared."""
        workers = max(1, min(self.config.max_workers, len(items) or 1))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            # Submit everything up front, then yield in submission order: the
            # rate limiter, not the pool, decides how fast this actually runs.
            futures = {pool.submit(func, item): item for item in items}
            for future, item in futures.items():
                try:
                    yield item, future.result(), None
                except Exception as exc:  # surfaced per item, never fatal
                    yield item, None, exc

    # -------------------------------------------------------------------- auth

    def _load_token(self) -> None:
        if not self.token_path or not self.token_path.exists():
            return
        try:
            with open(self.token_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.token = data.get("token") or None
            self.user_name = data.get("ingame_name") or None
        except (OSError, json.JSONDecodeError):
            self.token = None

    def _save_token(self) -> None:
        if not self.token_path or not self.token:
            return
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as handle:
            json.dump({"token": self.token, "ingame_name": self.user_name}, handle)
        try:
            os.chmod(self.token_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        except OSError:
            pass

    def _capture_token(self, response: requests.Response) -> None:
        header = response.headers.get("Authorization") or ""
        if header.lower().startswith("jwt "):
            self.token = header[4:].strip()
            self._save_token()

    def forget_token(self) -> None:
        self.token = None
        if self.token_path and self.token_path.exists():
            try:
                self.token_path.unlink()
            except OSError:
                pass

    def set_token(self, token: str, ingame_name: str | None = None) -> None:
        """Use a JWT captured from the browser, for accounts that need 2FA."""
        self.token = token.strip()
        if ingame_name:
            self.user_name = ingame_name
        self._save_token()

    def signin(self, email: str, password: str) -> str:
        data = self.request(
            "POST",
            "/auth/signin",
            payload={"email": email, "password": password, "auth_type": "header"},
        )
        user = (data.get("payload") or {}).get("user") or {}
        self.user_name = user.get("ingame_name") or self.user_name
        if not self.token:
            raise AuthError(
                "sign-in returned no JWT. warframe.market may be asking for a "
                "captcha or 2FA - sign in from a browser and pass the JWT cookie "
                "to 'wfbot login --token'."
            )
        self._save_token()
        return self.token

    @property
    def authenticated(self) -> bool:
        return bool(self.token)

    # ------------------------------------------------------------ read methods

    def items(self) -> list[Item]:
        data = self.request("GET", "/items", cache_ttl=self.config.items_cache_ttl)
        raw = (data.get("payload") or {}).get("items") or []
        return [Item.from_api(entry) for entry in raw]

    def orders(self, url_name: str) -> OrderBook:
        data = self.request(
            "GET", f"/items/{url_name}/orders", cache_ttl=self.config.orders_cache_ttl
        )
        # The endpoint returns every platform's listings; you can only trade
        # with people on your own.
        return OrderBook.from_api(url_name, data).filtered(platform=self.config.platform)

    def statistics(self, url_name: str) -> ItemStats:
        data = self.request(
            "GET",
            f"/items/{url_name}/statistics",
            cache_ttl=self.config.statistics_cache_ttl,
        )
        return ItemStats.from_api(url_name, data)

    def item_detail(self, url_name: str) -> dict[str, Any]:
        data = self.request(
            "GET", f"/items/{url_name}", cache_ttl=self.config.items_cache_ttl
        )
        return (data.get("payload") or {}).get("item") or {}

    def user_orders(self, ingame_name: str) -> list[dict[str, Any]]:
        """Public order list for a profile; also works for your own account."""
        data = self.request("GET", f"/profile/{ingame_name}/orders", cache_ttl=0)
        payload = data.get("payload") or {}
        return list(payload.get("sell_orders") or []) + list(payload.get("buy_orders") or [])

    # ----------------------------------------------------------- write methods

    def create_order(
        self,
        item_id: str,
        order_type: str,
        platinum: int,
        quantity: int,
        *,
        visible: bool = True,
        rank: int | None = None,
        subtype: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "item": item_id,
            "order_type": order_type,
            "platinum": int(platinum),
            "quantity": int(quantity),
            "visible": visible,
        }
        if rank is not None:
            payload["rank"] = int(rank)
        if subtype:
            payload["subtype"] = subtype
        return self.request("POST", "/profile/orders", payload=payload, authenticated=True)

    def update_order(
        self,
        order_id: str,
        *,
        platinum: int,
        quantity: int,
        visible: bool = True,
        rank: int | None = None,
        subtype: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "platinum": int(platinum),
            "quantity": int(quantity),
            "visible": visible,
        }
        if rank is not None:
            payload["rank"] = int(rank)
        if subtype:
            payload["subtype"] = subtype
        return self.request(
            "PUT", f"/profile/orders/{order_id}", payload=payload, authenticated=True
        )

    def delete_order(self, order_id: str) -> dict[str, Any]:
        return self.request("DELETE", f"/profile/orders/{order_id}", authenticated=True)

    def close_order(self, order_id: str) -> dict[str, Any]:
        """Mark an order as filled, which is what credits your reputation."""
        return self.request("PUT", f"/profile/orders/close/{order_id}", authenticated=True)


def chunked(items: Iterable[T], size: int) -> Iterator[list[T]]:
    batch: list[T] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
