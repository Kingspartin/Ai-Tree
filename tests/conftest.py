"""Shared builders. No test in this suite touches the network."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import pytest

from wfbot.models import ItemStats, OrderBook

FIXTURES = Path(__file__).parent / "fixtures"


def iso(hours_ago: float = 0.0) -> str:
    stamp = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return stamp.isoformat(timespec="milliseconds")


def order(
    platinum: int,
    order_type: str = "sell",
    *,
    user: str = "seller",
    status: str = "ingame",
    quantity: int = 1,
    visible: bool = True,
    hours_ago: float = 1.0,
    mod_rank: int | None = None,
    subtype: str | None = None,
    order_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": order_id or f"{order_type}-{user}-{platinum}",
        "order_type": order_type,
        "platinum": platinum,
        "quantity": quantity,
        "visible": visible,
        "platform": "pc",
        "region": "en",
        "mod_rank": mod_rank,
        "subtype": subtype,
        "creation_date": iso(hours_ago + 24),
        "last_update": iso(hours_ago),
        "user": {"ingame_name": user, "status": status, "reputation": 10, "region": "en"},
    }


def book(orders: Iterable[dict[str, Any]], item: str = "test_item") -> OrderBook:
    return OrderBook.from_api(item, {"payload": {"orders": list(orders)}})


def stat_point(price: float, volume: float, hours_ago: float, order_type: str = "sell") -> dict[str, Any]:
    return {
        "datetime": iso(hours_ago),
        "volume": volume,
        "min_price": price * 0.9,
        "max_price": price * 1.1,
        "avg_price": price,
        "wa_price": price,
        "median": price,
        "moving_avg": price,
        "order_type": order_type,
    }


def stats(
    prices: Sequence[float] = (100, 100, 100),
    volume: float = 10.0,
    item: str = "test_item",
) -> ItemStats:
    payload = {
        "payload": {
            "statistics_closed": {
                "48hours": [
                    stat_point(price, volume, hours_ago=index * 6 + 1)
                    for index, price in enumerate(prices)
                ],
                "90days": [
                    stat_point(price, volume * 24, hours_ago=index * 24 + 24)
                    for index, price in enumerate(prices)
                ],
            }
        }
    }
    return ItemStats.from_api(item, payload)


def empty_stats(item: str = "test_item") -> ItemStats:
    return ItemStats.from_api(item, {"payload": {"statistics_closed": {"48hours": [], "90days": []}}})


class FakeClient:
    """Stands in for WarframeMarketClient in trader and scanner tests."""

    def __init__(
        self,
        books: dict[str, OrderBook] | None = None,
        statistics: dict[str, ItemStats] | None = None,
        profile_orders: list[dict[str, Any]] | None = None,
        user_name: str = "Tester",
    ) -> None:
        self.books = books or {}
        self.statistics_by_item = statistics or {}
        self.profile_orders = profile_orders or []
        self.user_name = user_name
        self.updates: list[dict[str, Any]] = []
        self.failures: dict[str, Exception] = {}

    def orders(self, url_name: str) -> OrderBook:
        if url_name in self.failures:
            raise self.failures[url_name]
        return self.books[url_name]

    def statistics(self, url_name: str) -> ItemStats:
        return self.statistics_by_item.get(url_name, empty_stats(url_name))

    def item_detail(self, url_name: str) -> dict[str, Any]:
        return {"items_in_set": [{"url_name": url_name, "en": {"item_name": url_name}}]}

    def items(self) -> list[Any]:
        from wfbot.models import Item

        return [Item(url_name=url, name=url.replace("_", " ").title()) for url in self.books]

    def user_orders(self, ingame_name: str) -> list[dict[str, Any]]:
        return list(self.profile_orders)

    def update_order(self, order_id: str, **kwargs: Any) -> dict[str, Any]:
        if order_id in self.failures:
            raise self.failures[order_id]
        self.updates.append({"id": order_id, **kwargs})
        return {"payload": {}}

    def map(self, func: Callable[[Any], Any], items: Sequence[Any]):
        for item in items:
            try:
                yield item, func(item), None
            except Exception as exc:  # noqa: BLE001
                yield item, None, exc


def my_order(
    order_id: str,
    item: str,
    order_type: str,
    platinum: int,
    *,
    quantity: int = 1,
    name: str | None = None,
    mod_rank: int | None = None,
) -> dict[str, Any]:
    return {
        "id": order_id,
        "order_type": order_type,
        "platinum": platinum,
        "quantity": quantity,
        "visible": True,
        "mod_rank": mod_rank,
        "item": {
            "id": f"item-{item}",
            "url_name": item,
            "en": {"item_name": name or item.replace("_", " ").title()},
        },
    }


@pytest.fixture
def config(tmp_path):
    from wfbot.config import Config

    cfg = Config()
    cfg.state_dir = tmp_path
    cfg.trade.ingame_name = "Tester"
    (tmp_path / "cache").mkdir(exist_ok=True)
    return cfg


@pytest.fixture
def database(tmp_path):
    from wfbot.storage import Database

    db = Database(tmp_path / "test.sqlite3", tmp_path / "audit.jsonl")
    yield db
    db.close()


@pytest.fixture
def real_orders_payload() -> dict[str, Any]:
    with open(FIXTURES / "orders_loki_prime_set.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def real_statistics_payload() -> dict[str, Any]:
    with open(FIXTURES / "statistics_loki_prime_set.json", "r", encoding="utf-8") as handle:
        return json.load(handle)
