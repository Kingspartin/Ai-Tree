import pytest

from conftest import FakeClient, book, my_order, order, stats
from wfbot.api import WFMError
from wfbot.trader import MyOrder, Trader


def make_trader(config, database, *, profile_orders, books, statistics=None):
    client = FakeClient(books=books, statistics=statistics or {}, profile_orders=profile_orders)
    config.scan.min_volume = 1.0
    config.scan.min_book_depth = 2
    return Trader(client, config, database), client


def test_plan_undercuts_the_market(config, database):
    trader, _ = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "sell", 130)],
        books={
            "loki_prime_set": book(
                [
                    order(130, "sell", user="Tester"),
                    order(120, "sell", user="rival"),
                    order(124, "sell", user="rival2"),
                ],
                item="loki_prime_set",
            )
        },
        statistics={"loki_prime_set": stats(prices=[125, 125, 125])},
    )
    plan = trader.plan()
    assert len(plan.changes) == 1
    decision = plan.changes[0]
    assert decision.current == 130 and decision.target == 119
    assert decision.delta == -11
    assert "rival" in decision.reason


def test_plan_leaves_a_correct_price_alone(config, database):
    trader, _ = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "sell", 119)],
        books={
            "loki_prime_set": book(
                [order(119, "sell", user="Tester"), order(120, "sell", user="rival"),
                 order(124, "sell", user="rival2")],
                item="loki_prime_set",
            )
        },
        statistics={"loki_prime_set": stats(prices=[125, 125, 125])},
    )
    plan = trader.plan()
    assert plan.changes == []
    assert len(plan.decisions) == 1


def test_plan_respects_the_per_order_cooldown(config, database):
    config.trade.min_seconds_between_updates = 3600
    trader, _ = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "sell", 130)],
        books={
            "loki_prime_set": book(
                [order(120, "sell", user="rival"), order(124, "sell", user="rival2")],
                item="loki_prime_set",
            )
        },
        statistics={"loki_prime_set": stats(prices=[125, 125, 125])},
    )
    database.record_action("reprice", live=True, order_id="o1", result="ok")
    plan = trader.plan()
    assert plan.changes == []
    assert any("cooldown" in why for _, why in plan.skipped)


def test_plan_ignores_sub_threshold_moves(config, database):
    config.trade.min_change = 5
    trader, _ = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "sell", 121)],
        books={
            "loki_prime_set": book(
                [order(120, "sell", user="rival"), order(124, "sell", user="rival2")],
                item="loki_prime_set",
            )
        },
        statistics={"loki_prime_set": stats(prices=[125, 125, 125])},
    )
    plan = trader.plan()
    assert plan.changes == []
    assert any("min_change" in why for _, why in plan.skipped)


def test_plan_caps_updates_per_cycle(config, database):
    config.trade.max_updates_per_cycle = 1
    books = {
        f"item_{index}": book(
            [order(100, "sell", user="rival"), order(104, "sell", user="rival2")],
            item=f"item_{index}",
        )
        for index in range(3)
    }
    trader, _ = make_trader(
        config,
        database,
        profile_orders=[my_order(f"o{index}", f"item_{index}", "sell", 200) for index in range(3)],
        books=books,
        statistics={name: stats(prices=[105, 105, 105]) for name in books},
    )
    plan = trader.plan()
    assert len(plan.changes) == 1
    assert sum(1 for _, why in plan.skipped if "max_updates_per_cycle" in why) == 2


def test_plan_respects_the_buy_order_budget(config, database):
    config.trade.max_plat_in_buy_orders = 92  # already 90p committed
    trader, _ = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "buy", 90, quantity=1)],
        books={
            "loki_prime_set": book(
                [order(95, "buy", user="rival"), order(80, "buy", user="rival2")],
                item="loki_prime_set",
            )
        },
        statistics={"loki_prime_set": stats(prices=[200, 200, 200])},
    )
    plan = trader.plan()
    assert plan.changes == []
    assert any("buy-order cap" in why for _, why in plan.skipped)


def test_dry_run_never_calls_the_api(config, database):
    trader, client = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "sell", 130)],
        books={
            "loki_prime_set": book(
                [order(120, "sell", user="rival"), order(124, "sell", user="rival2")],
                item="loki_prime_set",
            )
        },
        statistics={"loki_prime_set": stats(prices=[125, 125, 125])},
    )
    plan = trader.plan()
    results = trader.apply(plan, live=False)
    assert client.updates == []
    assert all(result.ok for result in results)
    logged = database.recent_actions(10)
    assert logged and logged[0]["result"] == "planned" and logged[0]["live"] == 0


def test_live_requires_the_config_switch(config, database):
    trader, client = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "sell", 130)],
        books={
            "loki_prime_set": book(
                [order(120, "sell", user="rival"), order(124, "sell", user="rival2")],
                item="loki_prime_set",
            )
        },
        statistics={"loki_prime_set": stats(prices=[125, 125, 125])},
    )
    plan = trader.plan()
    with pytest.raises(WFMError, match="refusing to trade live"):
        trader.apply(plan, live=True)
    assert client.updates == []


def test_live_applies_and_audits(config, database):
    config.trade.live = True
    trader, client = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "sell", 130)],
        books={
            "loki_prime_set": book(
                [order(120, "sell", user="rival"), order(124, "sell", user="rival2")],
                item="loki_prime_set",
            )
        },
        statistics={"loki_prime_set": stats(prices=[125, 125, 125])},
    )
    results = trader.apply(trader.plan(), live=True)
    assert [result.ok for result in results] == [True]
    assert client.updates == [
        {"id": "o1", "platinum": 119, "quantity": 1, "visible": True, "rank": None, "subtype": None}
    ]
    logged = database.recent_actions(10)[0]
    assert logged["result"] == "ok" and logged["live"] == 1 and logged["new_price"] == 119
    assert database.last_change("o1") is not None


def test_live_failure_is_recorded_and_does_not_raise(config, database):
    config.trade.live = True
    trader, client = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "sell", 130)],
        books={
            "loki_prime_set": book(
                [order(120, "sell", user="rival"), order(124, "sell", user="rival2")],
                item="loki_prime_set",
            )
        },
        statistics={"loki_prime_set": stats(prices=[125, 125, 125])},
    )
    client.failures["o1"] = WFMError("HTTP 400")
    results = trader.apply(trader.plan(), live=True)
    assert results and not results[0].ok
    assert database.recent_actions(1)[0]["result"] == "error"


def test_unpriceable_item_is_skipped_not_fatal(config, database):
    trader, client = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "broken_item", "sell", 130)],
        books={"broken_item": book([], item="broken_item")},
    )
    client.failures["broken_item"] = WFMError("boom")
    plan = trader.plan()
    assert plan.changes == []
    assert plan.skipped and "market data unavailable" in plan.skipped[0][1]


def test_ranked_mods_are_priced_against_their_own_rank(config, database):
    market = book(
        [
            order(20, "sell", user="rank0guy", mod_rank=0),
            order(22, "sell", user="rank0guy2", mod_rank=0),
            order(150, "sell", user="maxedguy", mod_rank=10),
            order(155, "sell", user="maxedguy2", mod_rank=10),
        ],
        item="primed_mod",
    )
    trader, _ = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "primed_mod", "sell", 200, mod_rank=10)],
        books={"primed_mod": market},
        statistics={"primed_mod": stats(prices=[160, 160, 160])},
    )
    decision = trader.plan().changes[0]
    # Must undercut the other maxed copy, not the rank-0 one.
    assert decision.target == 149


def test_ingame_name_is_required(config, database):
    config.trade.ingame_name = ""
    client = FakeClient(books={}, profile_orders=[])
    client.user_name = ""
    trader = Trader(client, config, database)
    with pytest.raises(WFMError, match="in-game name"):
        trader.my_orders()


def test_my_order_parsing():
    parsed = MyOrder.from_api(my_order("o1", "loki_prime_set", "sell", 130, quantity=3))
    assert parsed.item_url == "loki_prime_set"
    assert parsed.item_name == "Loki Prime Set"
    assert parsed.quantity == 3
    assert parsed.item_id == "item-loki_prime_set"


def test_set_visibility_dry_run(config, database):
    trader, client = make_trader(
        config,
        database,
        profile_orders=[my_order("o1", "loki_prime_set", "sell", 130)],
        books={"loki_prime_set": book([], item="loki_prime_set")},
    )
    assert trader.set_visibility(False, live=False) == 1
    assert client.updates == []
    assert database.recent_actions(1)[0]["action"] == "visibility"
