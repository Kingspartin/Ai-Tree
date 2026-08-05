import json

from wfbot.analysis import Opportunity


def test_snapshot_and_history(database):
    database.record_snapshot(
        {"item": "loki_prime_set", "ask": 100, "bid": 90, "fair": 95.0,
         "volume_per_day": 12.0, "sellers": 5, "buyers": 3}
    )
    database.record_snapshot({"item": "loki_prime_set", "ask": 80, "fair": 95.0})
    rows = database.price_history("loki_prime_set", days=1)
    assert [row["ask"] for row in rows] == [100, 80]
    assert database.lowest_seen("loki_prime_set", days=1) == 80
    assert database.lowest_seen("other_item", days=1) is None


def test_opportunities_are_recorded(database):
    opportunity = Opportunity(
        kind="flip", item_url="loki_prime_set", item_name="Loki Prime Set",
        buy_at=60, sell_at=99, units=2, volume_per_day=10.0, confidence=0.9, fair=100.0,
    )
    database.record_opportunity(opportunity)
    rows = database._read("SELECT * FROM opportunities")
    assert len(rows) == 1
    assert rows[0]["profit"] == 39
    assert json.loads(rows[0]["payload"])["item_name"] == "Loki Prime Set"


def test_actions_are_audited_to_sqlite_and_jsonl(database, tmp_path):
    database.record_action(
        "reprice", live=True, order_id="o1", item="loki_prime_set", order_type="sell",
        old_price=130, new_price=119, result="ok", detail="undercutting rival",
    )
    row = database.recent_actions(1)[0]
    assert row["new_price"] == 119 and row["live"] == 1

    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    entry = json.loads(lines[-1])
    assert entry["order_id"] == "o1" and entry["result"] == "ok"


def test_last_change_only_counts_successful_live_writes(database):
    database.record_action("reprice", live=False, order_id="o1", result="planned")
    assert database.last_change("o1") is None
    database.record_action("reprice", live=True, order_id="o1", result="error")
    assert database.last_change("o1") is None
    database.record_action("reprice", live=True, order_id="o1", result="ok")
    assert database.last_change("o1") is not None


def test_universe_upsert_and_ranking(database):
    database.save_universe(
        [
            {"item": "a", "name": "A", "liquidity": 10.0, "price": 5, "volume_per_day": 2},
            {"item": "b", "name": "B", "liquidity": 99.0, "price": 50, "volume_per_day": 2},
        ]
    )
    database.save_universe(
        [{"item": "a", "name": "A", "liquidity": 500.0, "price": 5, "volume_per_day": 100}]
    )
    rows = database.top_universe(10)
    assert [row["item"] for row in rows] == ["a", "b"]
    assert rows[0]["liquidity"] == 500.0
    assert database.top_universe(10, max_age_hours=0) == []


def test_notification_cooldown(database):
    assert database.should_notify("opp:x", cooldown=60) is True
    assert database.should_notify("opp:x", cooldown=60) is False
    assert database.should_notify("opp:y", cooldown=60) is True
    assert database.should_notify("opp:x", cooldown=0) is True
