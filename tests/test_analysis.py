import pytest

from conftest import book, empty_stats, order, stats
from wfbot.analysis import (
    book_price,
    evaluate,
    find_opportunities,
    historical_price,
    suggest_price,
)
from wfbot.config import ScanConfig, TradeConfig
from wfbot.models import OrderBook


def scan_config(**overrides) -> ScanConfig:
    config = ScanConfig()
    config.min_volume = 1.0
    config.min_book_depth = 2
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def test_book_price_ignores_the_cheapest_listing():
    sells = book(
        [order(10, "sell", user="mistake"), order(100, "sell", user="a"),
         order(104, "sell", user="b"), order(110, "sell", user="c")]
    ).sells()
    # 10p is somebody's typo; it must not drag the reference price down.
    assert book_price(sells) == 104


def test_historical_price_falls_back_to_90_days():
    assert historical_price(stats(prices=[100, 100, 100])) == 100
    assert historical_price(empty_stats()) is None


def test_fair_value_is_the_conservative_of_history_and_book():
    market = book([order(200, "sell", user="a"), order(210, "sell", user="b"),
                   order(220, "sell", user="c"), order(230, "sell", user="d")])
    valuation = evaluate("x", "X", market, stats(prices=[100, 100, 100]), scan_config())
    # History says 100, the book says 215. Trust the cheaper number.
    assert valuation.fair == 100
    assert any("disagree" in risk for risk in valuation.risks)


def test_crossed_book_is_found():
    market = book(
        [
            order(80, "sell", user="seller"),
            order(120, "sell", user="other"),
            order(130, "sell", user="other2"),
            order(100, "buy", user="buyer", quantity=2),
        ]
    )
    config = scan_config(min_profit=5, min_margin=0.1)
    valuation = evaluate("x", "X", market, stats(prices=[110, 110, 110]), config)
    found = find_opportunities(valuation, market, config)
    crossed = [o for o in found if o.kind == "crossed"]
    assert len(crossed) == 1
    assert crossed[0].buy_at == 80 and crossed[0].sell_at == 100
    assert crossed[0].profit == 20
    assert crossed[0].buy_from == "seller" and crossed[0].sell_to == "buyer"


def test_flip_prices_just_under_the_next_listing():
    market = book(
        [
            order(60, "sell", user="cheap"),
            order(100, "sell", user="a"),
            order(102, "sell", user="b"),
            order(105, "sell", user="c"),
        ]
    )
    config = scan_config(min_margin=0.2, min_profit=5)
    valuation = evaluate("x", "X", market, stats(prices=[100, 100, 100]), config)
    flips = [o for o in find_opportunities(valuation, market, config) if o.kind == "flip"]
    assert len(flips) == 1
    # fair = 100 (history) vs 102 (book); exit is one under the cheaper of the two.
    assert flips[0].buy_at == 60
    assert flips[0].sell_at == 99
    assert flips[0].profit == 39


def test_margin_and_profit_gates_reject_thin_trades():
    market = book([order(95, "sell", user="cheap"), order(100, "sell", user="a"),
                   order(101, "sell", user="b"), order(102, "sell", user="c")])
    config = scan_config(min_margin=0.25, min_profit=10)
    valuation = evaluate("x", "X", market, stats(prices=[100, 100, 100]), config)
    assert find_opportunities(valuation, market, config) == []


def test_budget_limits_units_and_excludes_unaffordable_items():
    market = book([order(400, "sell", user="cheap", quantity=10),
                   order(900, "sell", user="a"), order(950, "sell", user="b"),
                   order(980, "sell", user="c")])
    config = scan_config(budget=850, min_margin=0.2, min_profit=10)
    valuation = evaluate("x", "X", market, stats(prices=[900, 900, 900], volume=40), config)
    flips = find_opportunities(valuation, market, config)
    assert flips and flips[0].units == 2  # 850p buys two at 400p

    config.budget = 300
    assert find_opportunities(valuation, market, config) == []


def test_units_are_capped_by_daily_volume():
    market = book([order(10, "sell", user="cheap", quantity=99),
                   order(50, "sell", user="a"), order(52, "sell", user="b"),
                   order(55, "sell", user="c")])
    config = scan_config(budget=10_000, min_margin=0.2, min_profit=5)
    # Barely one trade a day: buying 99 copies means holding 99 copies.
    valuation = evaluate("x", "X", market, stats(prices=[50, 50, 50], volume=0.2), config)
    flips = find_opportunities(valuation, market, config)
    assert flips and flips[0].units == 1


def test_risks_are_reported():
    market = book([order(50, "sell", user="only"), order(400, "sell", user="only")])
    valuation = evaluate("x", "X", market, stats(prices=[100], volume=0.1), ScanConfig())
    joined = " ".join(valuation.risks)
    assert "thin book" in joined
    assert "low volume" in joined
    assert "one seller controls the book" in joined


def test_confidence_drops_for_stale_counterparties():
    fresh = book([order(60, "sell", user="a", hours_ago=1), order(100, "sell", user="b"),
                  order(102, "sell", user="c"), order(104, "sell", user="d")])
    stale = book([order(60, "sell", user="a", hours_ago=60), order(100, "sell", user="b"),
                  order(102, "sell", user="c"), order(104, "sell", user="d")])
    config = scan_config(min_margin=0.2, min_profit=5)
    price_history = stats(prices=[100, 100, 100])
    fresh_opportunity = find_opportunities(
        evaluate("x", "X", fresh, price_history, config), fresh, config
    )[0]
    stale_opportunity = find_opportunities(
        evaluate("x", "X", stale, price_history, config), stale, config
    )[0]
    assert fresh_opportunity.confidence > stale_opportunity.confidence


def test_no_opportunity_without_a_live_seller():
    market = book([order(50, "sell", user="a", status="offline")])
    config = scan_config()
    valuation = evaluate("x", "X", market, stats(), config)
    assert valuation.best_ask is None
    assert find_opportunities(valuation, market, config) == []


# ----------------------------------------------------------------- repricing


def trade_config(**overrides) -> TradeConfig:
    config = TradeConfig(ingame_name="Me")
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def test_sell_undercuts_the_cheapest_live_rival():
    market = book([order(100, "sell", user="Me"), order(95, "sell", user="rival"),
                   order(99, "sell", user="rival2")])
    valuation = evaluate("x", "X", market, stats(prices=[100]), scan_config())
    target, reason = suggest_price("sell", 100, market, valuation, trade_config(), me="Me")
    assert target == 94
    assert "rival" in reason


def test_sell_stops_at_the_floor_instead_of_chasing():
    market = book(
        [
            order(100, "sell", user="Me"),
            order(30, "sell", user="lowballer"),
            order(100, "sell", user="rival"),
            order(102, "sell", user="rival2"),
        ]
    )
    valuation = evaluate("x", "X", market, stats(prices=[100, 100, 100]), scan_config())
    target, reason = suggest_price("sell", 100, market, valuation, trade_config(), me="Me")
    assert target == 60  # 60% of the 100p fair value
    assert "floor" in reason


def test_sell_raises_when_you_are_alone_at_the_bottom():
    market = book([order(50, "sell", user="Me"), order(120, "sell", user="rival")])
    valuation = evaluate("x", "X", market, stats(prices=[120, 120, 120]), scan_config())
    target, reason = suggest_price("sell", 50, market, valuation, trade_config(), me="Me")
    assert target == 119
    assert "raising" in reason


def test_buy_outbids_up_to_a_ceiling():
    market = book([order(50, "buy", user="Me"), order(60, "buy", user="rival")])
    valuation = evaluate("x", "X", market, stats(prices=[100, 100, 100]), scan_config())
    target, _ = suggest_price("buy", 50, market, valuation, trade_config(), me="Me")
    assert target == 61

    hot = book([order(50, "buy", user="Me"), order(90, "buy", user="rival")])
    valuation = evaluate("x", "X", hot, stats(prices=[100, 100, 100]), scan_config())
    target, reason = suggest_price("buy", 50, hot, valuation, trade_config(), me="Me")
    assert target == 75  # 75% of fair value
    assert "ceiling" in reason


def test_no_fair_value_means_no_change():
    market = OrderBook(item_url="x")
    valuation = evaluate("x", "X", market, empty_stats(), scan_config())
    target, reason = suggest_price("sell", 42, market, valuation, trade_config(), me="Me")
    assert target == 42
    assert "no fair value" in reason


# ------------------------------------------------------ against real payloads


def test_real_payload_end_to_end(real_orders_payload, real_statistics_payload):
    from wfbot.models import ItemStats

    market = OrderBook.from_api("loki_prime_set", real_orders_payload).filtered(platform="pc")
    price_history = ItemStats.from_api("loki_prime_set", real_statistics_payload)
    # The fixture timestamps are fixed, so age out the staleness filter.
    config = scan_config(stale_order_days=100_000, min_profit=5, min_margin=0.2)

    valuation = evaluate("loki_prime_set", "Loki Prime Set", market, price_history, config)
    assert valuation.ask == 96  # cheapest ingame PC seller
    assert valuation.bid == 105  # richest ingame PC buyer
    assert valuation.depth_sell == 3
    assert valuation.hist_ref == pytest.approx(118.6)
    assert valuation.book_ref == 120
    assert valuation.fair == pytest.approx(118.6)
    assert valuation.volume_per_day == pytest.approx(21.0, abs=0.01)
    assert valuation.risks == []

    kinds = {o.kind: o for o in find_opportunities(valuation, market, config)}
    assert kinds["crossed"].profit == 9  # sell to PlatBurner at 105
    assert kinds["flip"].sell_at == 117 and kinds["flip"].profit == 21
    assert kinds["flip"].confidence > 0.8
