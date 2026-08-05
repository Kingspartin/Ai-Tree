import json
import time

import pytest

from wfbot import api as api_module
from wfbot.api import AuthError, DiskCache, NotFound, TokenBucket, WarframeMarketClient, WFMError
from wfbot.config import ApiConfig


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"payload": {}}
        self.headers = headers or {}
        self.text = text or json.dumps(self._payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, headers=None, data=None, timeout=None):
        self.calls.append({"method": method, "url": url, "headers": headers, "data": data})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(api_module.time, "sleep", lambda seconds: None)


def client_with(responses, tmp_path, **config_kwargs):
    config = ApiConfig(requests_per_second=1000, **config_kwargs)
    return WarframeMarketClient(
        config, cache_dir=tmp_path / "cache", token_path=tmp_path / "token.json",
        session=FakeSession(responses),
    )


def test_token_bucket_limits_throughput():
    bucket = TokenBucket(rate=50, burst=1)
    started = time.monotonic()
    for _ in range(5):
        bucket.take()
    elapsed = time.monotonic() - started
    # Four of the five requests have to wait for a refill at 50/s.
    assert elapsed >= 0.06


def test_disk_cache_respects_ttl(tmp_path):
    cache = DiskCache(tmp_path)
    cache.set("k", {"v": 1})
    assert cache.get("k", ttl=60) == {"v": 1}
    assert cache.get("k", ttl=0) is None
    assert cache.get("missing", ttl=60) is None
    assert cache.clear() == 1


def test_headers_carry_platform_and_language(tmp_path):
    client = client_with([FakeResponse()], tmp_path)
    client.request("GET", "/items")
    headers = client.session.calls[0]["headers"]
    assert headers["platform"] == "pc"
    assert headers["language"] == "en"
    assert "Authorization" not in headers


def test_get_is_cached(tmp_path):
    client = client_with([FakeResponse(payload={"payload": {"items": []}})], tmp_path)
    first = client.request("GET", "/items", cache_ttl=600)
    second = client.request("GET", "/items", cache_ttl=600)
    assert first == second
    assert len(client.session.calls) == 1  # served from disk the second time


def test_server_errors_are_retried(tmp_path):
    client = client_with(
        [FakeResponse(500), FakeResponse(502), FakeResponse(payload={"payload": {"ok": True}})],
        tmp_path,
    )
    assert client.request("GET", "/items")["payload"] == {"ok": True}
    assert len(client.session.calls) == 3


def test_rate_limit_is_retried_and_backs_off(tmp_path):
    client = client_with(
        [FakeResponse(429, headers={"Retry-After": "1"}), FakeResponse(payload={"payload": {}})],
        tmp_path,
    )
    client.request("GET", "/items")
    assert len(client.session.calls) == 2


def test_retries_are_bounded(tmp_path):
    client = client_with([FakeResponse(500)] * 4, tmp_path, max_retries=4)
    with pytest.raises(WFMError, match="giving up"):
        client.request("GET", "/items")


def test_404_raises_not_found(tmp_path):
    client = client_with([FakeResponse(404)], tmp_path)
    with pytest.raises(NotFound):
        client.request("GET", "/items/nope/orders")


def test_401_clears_the_stored_token(tmp_path):
    client = client_with([FakeResponse(401)], tmp_path)
    client.set_token("stale-token")
    assert client.token_path.exists()
    with pytest.raises(AuthError):
        client.request("GET", "/profile/x/orders", authenticated=True)
    assert client.token is None
    assert not client.token_path.exists()


def test_token_is_captured_from_the_response_header(tmp_path):
    client = client_with(
        [FakeResponse(headers={"Authorization": "JWT abc.def.ghi"},
                      payload={"payload": {"user": {"ingame_name": "Tester"}}})],
        tmp_path,
    )
    token = client.signin("me@example.com", "hunter2")
    assert token == "abc.def.ghi"
    assert client.user_name == "Tester"
    stored = json.loads(client.token_path.read_text())
    assert stored["token"] == "abc.def.ghi"
    # The password must never be written to disk.
    assert "hunter2" not in client.token_path.read_text()


def test_signin_without_a_token_is_an_auth_error(tmp_path):
    client = client_with([FakeResponse(payload={"payload": {"user": {}}})], tmp_path)
    with pytest.raises(AuthError, match="no JWT"):
        client.signin("me@example.com", "hunter2")


def test_authenticated_request_sends_the_jwt(tmp_path):
    client = client_with([FakeResponse()], tmp_path)
    client.set_token("abc")
    client.update_order("order-1", platinum=100, quantity=1)
    call = client.session.calls[0]
    assert call["method"] == "PUT"
    assert call["url"].endswith("/profile/orders/order-1")
    assert call["headers"]["Authorization"] == "JWT abc"
    assert json.loads(call["data"]) == {"platinum": 100, "quantity": 1, "visible": True}


def test_write_without_a_token_refuses_early(tmp_path):
    client = client_with([], tmp_path)
    with pytest.raises(AuthError, match="not signed in"):
        client.update_order("order-1", platinum=100, quantity=1)


def test_orders_are_filtered_to_your_platform(tmp_path, real_orders_payload):
    client = client_with([FakeResponse(payload=real_orders_payload)], tmp_path)
    market = client.orders("loki_prime_set")
    assert all(order.platform == "pc" for order in market.orders)
    assert not any(order.user_name == "ConsolePlayer" for order in market.orders)


def test_map_reports_per_item_errors(tmp_path):
    client = client_with([], tmp_path)

    def work(value):
        if value == 2:
            raise WFMError("boom")
        return value * 10

    results = {item: (value, error) for item, value, error in client.map(work, [1, 2, 3])}
    assert results[1][0] == 10
    assert results[2][0] is None and isinstance(results[2][1], WFMError)
    assert results[3][0] == 30
