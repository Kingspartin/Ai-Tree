from datetime import datetime, timezone

import pytest

from conftest import book, order
from wfbot.models import Order, OrderBook, median, parse_dt, weighted_median


def test_parse_dt_handles_api_formats():
    assert parse_dt("2026-08-04T18:02:11.000+00:00").year == 2026
    assert parse_dt("2026-08-04T18:02:11Z").tzinfo == timezone.utc
    naive = parse_dt("2026-08-04T18:02:11")
    assert naive is not None and naive.tzinfo == timezone.utc
    assert parse_dt("2026-08-04T18:02:11.1234567+00:00") is not None
    assert parse_dt(None) is None
    assert parse_dt("nonsense") is None


def test_order_actionable_requires_ingame_and_stock():
    live = Order.from_api(order(100, status="ingame"))
    away = Order.from_api(order(100, status="online"))
    empty = Order.from_api(order(100, quantity=0))
    hidden = Order.from_api(order(100, visible=False))
    assert live.actionable()
    assert not away.actionable()
    assert not empty.actionable()
    assert not hidden.actionable()


def test_order_age_days_without_timestamps_is_infinite():
    bare = Order.from_api({"id": "x", "order_type": "sell", "platinum": 5, "quantity": 1})
    assert bare.age_days() == float("inf")


def test_sides_are_sorted_for_the_trader():
    market = book(
        [
            order(120, "sell"),
            order(96, "sell", user="cheap"),
            order(110, "sell", user="mid"),
            order(80, "buy", user="b1"),
            order(95, "buy", user="b2"),
        ]
    )
    assert [o.platinum for o in market.sells()] == [96, 110, 120]
    assert [o.platinum for o in market.buys()] == [95, 80]
    assert market.best_sell().platinum == 96
    assert market.best_buy().platinum == 95


def test_side_filters_offline_stale_and_self():
    market = book(
        [
            order(90, "sell", user="Me"),
            order(95, "sell", user="offline_guy", status="offline"),
            order(100, "sell", user="stale_guy", hours_ago=24 * 10),
            order(110, "sell", user="fresh_guy"),
        ]
    )
    prices = [o.platinum for o in market.sells(exclude_user="me", max_age_days=3)]
    assert prices == [110]
    assert len(market.sells(actionable_only=False)) == 4


def test_filtered_splits_mod_ranks():
    market = book(
        [
            order(20, "sell", mod_rank=0, user="a"),
            order(150, "sell", mod_rank=10, user="b"),
            order(160, "sell", mod_rank=10, user="c"),
        ]
    )
    assert [o.platinum for o in market.filtered(mod_rank=0).sells()] == [20]
    assert [o.platinum for o in market.filtered(mod_rank=10).sells()] == [150, 160]
    assert set(market.variants()) == {(0, None), (10, None)}


def test_filtered_by_platform():
    payload = {
        "payload": {
            "orders": [
                order(100, "sell") | {"platform": "pc"},
                order(200, "sell", user="console") | {"platform": "ps4"},
            ]
        }
    }
    market = OrderBook.from_api("x", payload).filtered(platform="pc")
    assert [o.platinum for o in market.sells()] == [100]


def test_weighted_median_respects_volume():
    # The 500p outlier traded once; the 100p price traded fifty times.
    assert weighted_median([100, 500], [50, 1]) == 100
    assert weighted_median([100, 500], [1, 50]) == 500
    # With no usable weights it degrades to a plain median.
    assert weighted_median([10, 20, 30], [0, 0, 0]) == 20
    assert weighted_median([], []) is None


def test_median():
    assert median([1, 2, 3]) == 2
    assert median([1, 2, 3, 4]) == 2.5
    assert median([]) is None


def test_stats_volume_per_day(real_statistics_payload):
    from wfbot.models import ItemStats

    stats = ItemStats.from_api("loki_prime_set", real_statistics_payload)
    # 7 + 5 + 9 sell trades across a 24h span.
    assert stats.volume_per_day(window="48hours") == pytest.approx(21.0, abs=0.01)
    # Buy-side rows must not leak into the sell series.
    assert all(point.order_type == "sell" for point in stats.points())
