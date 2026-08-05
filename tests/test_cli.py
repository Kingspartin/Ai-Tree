import pytest

from wfbot.analysis import Opportunity
from wfbot.cli import OPPORTUNITY_COLUMNS, build_parser, opportunity_rows, table
from wfbot.notify import Notifier, whisper
from wfbot.config import NotifyConfig


def test_parser_requires_a_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_reprice_is_dry_by_default():
    args = build_parser().parse_args(["reprice"])
    assert args.live is False
    assert args.func.__name__ == "cmd_reprice"


def test_autopilot_is_dry_by_default():
    args = build_parser().parse_args(["autopilot"])
    assert args.live is False


def test_scan_arguments():
    args = build_parser().parse_args(["--platform", "ps4", "scan", "--budget", "300", "--json"])
    assert args.platform == "ps4"
    assert args.budget == 300
    assert args.json is True


def test_table_renders_and_handles_empty():
    rows = [{"a": 1, "b": None}, {"a": 22, "b": "x"}]
    rendered = table(rows, [("a", "A"), ("b", "BEE")])
    lines = rendered.splitlines()
    assert lines[0].split() == ["A", "BEE"]
    assert "-" in lines[1]
    assert lines[2].startswith("1 ")
    assert lines[3].startswith("22")
    assert "(nothing to show)" in table([], [("a", "A")])


def test_opportunity_rows_are_renderable():
    opportunity = Opportunity(
        kind="flip", item_url="loki_prime_set", item_name="Loki Prime Set",
        buy_at=60, sell_at=99, units=2, volume_per_day=10.0, confidence=0.9, fair=100.0,
        buy_from="Seller",
    )
    rendered = table(opportunity_rows([opportunity]), OPPORTUNITY_COLUMNS)
    assert "Loki Prime Set" in rendered
    assert "+39p" in rendered
    assert "65%" in rendered  # margin


def test_whisper_matches_the_site_format():
    text = whisper("BulletJumper", "Loki Prime Set", 96)
    assert text == (
        '/w BulletJumper Hi! I want to buy: "Loki Prime Set" for 96 platinum. (warframe.market)'
    )
    ranked = whisper("Tenno", "Primed Flow", 150, side="sell", rank=10)
    assert 'I want to sell: "Primed Flow" (rank 10) for 150 platinum.' in ranked


def test_notifier_respects_the_cooldown(database, capsys):
    config = NotifyConfig(desktop=False, clipboard=False, cooldown_seconds=3600)
    notifier = Notifier(config, database)
    notifier.send("title", "first", key="k")
    notifier.send("title", "second", key="k")
    output = capsys.readouterr().out
    assert "first" in output
    assert "second" not in output


def test_notifier_skips_low_scores(database, capsys):
    config = NotifyConfig(desktop=False, clipboard=False, min_score=1000)
    notifier = Notifier(config, database)
    notifier.opportunity(
        Opportunity(
            kind="flip", item_url="x", item_name="X", buy_at=10, sell_at=11, units=1,
            volume_per_day=1.0, confidence=0.5, fair=11.0,
        )
    )
    assert capsys.readouterr().out == ""
