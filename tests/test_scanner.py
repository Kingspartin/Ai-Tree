import pytest

from conftest import FakeClient, book, order, stats
from wfbot.api import WFMError
from wfbot.scanner import Scanner, matches, resolve_items, variants_to_evaluate


def test_include_and_exclude_globs():
    assert matches("loki_prime_set", ["*"], [])
    assert matches("loki_prime_set", ["*_prime_set"], [])
    assert not matches("loki_prime_blueprint", ["*_prime_set"], [])
    # Rivens and Kuva weapons are excluded by default: their prices depend on
    # rolls and bonus percentages, not on an order book.
    assert not matches("rubico_riven_mod", ["*"], ["*riven*"])
    assert not matches("kuva_bramma", ["*"], ["*kuva_*"])
    assert matches("KUVA_BRAMMA".lower(), ["*"], ["*kuva_*"]) is False


def test_variants_split_ranked_mods():
    market = book(
        [
            order(20, "sell", user="a", mod_rank=0),
            order(21, "sell", user="b", mod_rank=0),
            order(150, "sell", user="c", mod_rank=10),
            order(155, "sell", user="d", mod_rank=10),
        ]
    )
    assert set(variants_to_evaluate(market)) == {(0, None), (10, None)}


def test_variants_of_a_plain_item():
    market = book([order(100, "sell", user="a"), order(110, "sell", user="b")])
    assert variants_to_evaluate(market) == [(None, None)]


def test_scan_ranks_by_expected_profit(config, database):
    config.scan.min_volume = 1.0
    config.scan.min_book_depth = 2
    config.scan.min_margin = 0.2
    config.scan.min_profit = 5
    config.scan.budget = 1000

    books = {
        "small_win": book(
            [order(20, "sell", user="a"), order(40, "sell", user="b"),
             order(42, "sell", user="c"), order(44, "sell", user="d")],
            item="small_win",
        ),
        "big_win": book(
            [order(100, "sell", user="a"), order(300, "sell", user="b"),
             order(310, "sell", user="c"), order(320, "sell", user="d")],
            item="big_win",
        ),
        "no_win": book(
            [order(100, "sell", user="a"), order(101, "sell", user="b"),
             order(102, "sell", user="c")],
            item="no_win",
        ),
    }
    statistics = {
        "small_win": stats(prices=[42, 42, 42]),
        "big_win": stats(prices=[305, 305, 305]),
        "no_win": stats(prices=[101, 101, 101]),
    }
    client = FakeClient(books=books, statistics=statistics)
    scanner = Scanner(client, config, database)

    from wfbot.models import Item

    items = [Item(url_name=name, name=name) for name in books]
    result = scanner.scan(items)

    assert result.scanned == 3
    names = [opportunity.item_url for opportunity in result.opportunities]
    assert "no_win" not in names
    assert result.opportunities[0].item_url == "big_win"  # ranked by score
    # Snapshots are persisted for the history command.
    assert database.price_history("big_win", days=1)


def test_scan_survives_a_failing_item(config, database):
    config.scan.min_volume = 1.0
    books = {"good": book([order(100, "sell", user="a")], item="good"), "bad": book([], item="bad")}
    client = FakeClient(books=books, statistics={"good": stats(prices=[100])})
    client.failures["bad"] = WFMError("500")
    scanner = Scanner(client, config, database)

    from wfbot.models import Item

    result = scanner.scan([Item(url_name=name, name=name) for name in books])
    assert result.scanned == 1
    assert [url for url, _ in result.errors] == ["bad"]


def test_triage_keeps_liquid_affordable_items(config, database):
    config.scan.budget = 200
    books = {name: book([], item=name) for name in ("cheap_liquid", "dear", "dead")}
    statistics = {
        "cheap_liquid": stats(prices=[50, 50, 50], volume=20),
        "dear": stats(prices=[900, 900, 900], volume=20),  # over budget
        "dead": stats(prices=[50, 50, 50], volume=0.0),  # never trades
    }
    client = FakeClient(books=books, statistics=statistics)
    scanner = Scanner(client, config, database)

    from wfbot.models import Item

    candidates = scanner.rank_candidates([Item(url_name=n, name=n) for n in books], limit=10)
    assert [item.url_name for item in candidates] == ["cheap_liquid"]
    # And the triage result is cached for the next run.
    assert [row["item"] for row in database.top_universe(10)] == ["cheap_liquid"]
    assert [item.url_name for item in scanner.cached_candidates(10)] == ["cheap_liquid"]


def test_resolve_items_by_name_and_slug():
    client = FakeClient(books={"loki_prime_set": book([]), "mirage_prime_set": book([])})
    assert resolve_items(client, ["loki_prime_set"])[0].url_name == "loki_prime_set"
    assert resolve_items(client, ["Loki Prime Set"])[0].url_name == "loki_prime_set"
    with pytest.raises(WFMError, match="no item matches"):
        resolve_items(client, ["Not A Real Item"])


def test_inspect_returns_valuation_and_opportunities(config, database):
    config.scan.min_volume = 1.0
    config.scan.min_book_depth = 2
    config.scan.min_margin = 0.2
    market = book(
        [order(60, "sell", user="cheap"), order(100, "sell", user="a"),
         order(102, "sell", user="b"), order(104, "sell", user="c")],
        item="loki_prime_set",
    )
    client = FakeClient(
        books={"loki_prime_set": market}, statistics={"loki_prime_set": stats(prices=[100, 100, 100])}
    )
    scanner = Scanner(client, config, database)
    results = scanner.inspect("loki_prime_set")
    assert len(results) == 1
    valuation, opportunities = results[0]
    assert valuation.ask == 60
    assert opportunities and opportunities[0].kind == "flip"
