"""Command line interface."""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import sys
import threading
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any, Sequence

from . import __version__
from .analysis import Opportunity, summarise
from .api import AuthError, NotFound, WarframeMarketClient, WFMError
from .config import Config, load as load_config
from .logwatch import LogEvent, LogWatcher, describe_paths
from .notify import Notifier, copy_to_clipboard, whisper
from .scanner import Scanner, resolve_items
from .storage import Database
from .trader import Trader

log = logging.getLogger("wfbot")

BANNER = """wfbot automates market research and your own warframe.market listings.
It never controls the Warframe client - trades still happen in-game, by hand."""


# --------------------------------------------------------------------- plumbing


class Context:
    """Lazily-built shared objects, so `--help` costs nothing."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.config: Config = load_config(args.config)
        if args.platform:
            self.config.api.platform = args.platform
        if getattr(args, "budget", None):
            self.config.scan.budget = args.budget
        self._client: WarframeMarketClient | None = None
        self._db: Database | None = None

    @property
    def client(self) -> WarframeMarketClient:
        if self._client is None:
            self._client = WarframeMarketClient(
                self.config.api,
                cache_dir=self.config.cache_dir,
                token_path=self.config.token_path,
            )
        return self._client

    @property
    def db(self) -> Database:
        if self._db is None:
            self._db = Database(self.config.db_path, self.config.audit_path)
        return self._db

    @property
    def notifier(self) -> Notifier:
        return Notifier(self.config.notify, self.db)

    def scanner(self) -> Scanner:
        return Scanner(self.client, self.config, self.db, on_progress=self.progress)

    def trader(self) -> Trader:
        return Trader(self.client, self.config, self.db)

    def progress(self, stage: str, done: int, total: int) -> None:
        if self.args.quiet or not sys.stderr.isatty():
            return
        width = 28
        filled = int(width * done / total) if total else width
        bar = "#" * filled + "." * (width - filled)
        print(f"\r  {stage:<7} [{bar}] {done}/{total}", end="", file=sys.stderr, flush=True)
        if done >= total:
            print(file=sys.stderr)


def table(rows: Sequence[dict[str, Any]], columns: Sequence[tuple[str, str]]) -> str:
    """Render rows as an aligned text table. `columns` is (key, header)."""
    if not rows:
        return "  (nothing to show)"
    widths = {}
    for key, header in columns:
        widths[key] = max(len(header), *(len(_cell(row.get(key))) for row in rows))
    head = "  ".join(header.ljust(widths[key]) for key, header in columns)
    rule = "  ".join("-" * widths[key] for key, _ in columns)
    lines = [head, rule]
    for row in rows:
        lines.append("  ".join(_cell(row.get(key)).ljust(widths[key]) for key, _ in columns))
    return "\n".join(lines)


def _cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, list):
        return ", ".join(str(entry) for entry in value) if value else "-"
    return str(value)


def opportunity_rows(opportunities: Sequence[Opportunity]) -> list[dict[str, Any]]:
    rows = []
    for opportunity in opportunities:
        rows.append(
            {
                "item": opportunity.item_name or opportunity.item_url,
                "kind": opportunity.kind,
                "buy": f"{opportunity.buy_at}p",
                "sell": f"{opportunity.sell_at}p",
                "each": f"+{opportunity.profit}p",
                "margin": f"{opportunity.margin:.0%}",
                "qty": opportunity.units,
                "total": f"{opportunity.total_profit}p",
                "vol/day": round(opportunity.volume_per_day, 1),
                "conf": f"{opportunity.confidence:.0%}",
                "score": opportunity.score,
                "from": opportunity.buy_from or "-",
                "risks": "; ".join(opportunity.risks) or "-",
            }
        )
    return rows


OPPORTUNITY_COLUMNS = [
    ("item", "ITEM"),
    ("kind", "KIND"),
    ("buy", "BUY"),
    ("sell", "SELL"),
    ("each", "EACH"),
    ("margin", "MARGIN"),
    ("qty", "QTY"),
    ("total", "TOTAL"),
    ("vol/day", "VOL/DAY"),
    ("conf", "CONF"),
    ("score", "SCORE"),
    ("from", "SELLER"),
]


def emit_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, default=str))


# --------------------------------------------------------------------- commands


def cmd_login(context: Context, args: argparse.Namespace) -> int:
    client = context.client
    if args.token:
        token = args.token
        if token == "-":
            token = sys.stdin.readline().strip()
        client.set_token(token, args.ingame_name or context.config.trade.ingame_name or None)
        print(f"Token stored in {context.config.token_path}")
        return 0

    email = args.email or os.environ.get("WFM_EMAIL") or input("warframe.market email: ").strip()
    password = os.environ.get("WFM_PASSWORD") or getpass.getpass("password: ")
    try:
        client.signin(email, password)
    except AuthError as exc:
        print(f"Sign-in failed: {exc}", file=sys.stderr)
        print(
            "\nIf the site is asking for a captcha, open warframe.market in a browser, "
            "copy the value of the 'JWT' cookie, and run:\n"
            "  wfbot login --token '<jwt>' --ingame-name '<YourName>'",
            file=sys.stderr,
        )
        return 2
    print(f"Signed in as {client.user_name or 'unknown user'}; token cached at {context.config.token_path}")
    if client.user_name and not context.config.trade.ingame_name:
        print("Add this to your config so the trader knows who you are:")
        print(f'  [trade]\n  ingame_name = "{client.user_name}"')
    return 0


def cmd_scan(context: Context, args: argparse.Namespace) -> int:
    scanner = context.scanner()
    items = None
    if args.items:
        items = resolve_items(context.client, args.items)
    elif args.refresh_universe:
        items = scanner.rank_candidates(scanner.universe(), args.candidates or context.config.scan.candidate_limit)

    result = scanner.scan(items, limit=args.candidates, use_cached_triage=not args.refresh_universe)
    best = result.best(args.limit)

    if args.json:
        emit_json(
            {
                "scanned": result.scanned,
                "elapsed": round(result.elapsed, 1),
                "opportunities": [asdict(opportunity) | {"score": opportunity.score} for opportunity in best],
            }
        )
        return 0

    print(f"\nScanned {result.scanned} items in {result.elapsed:.0f}s "
          f"(budget {context.config.scan.budget}p, min margin {context.config.scan.min_margin:.0%})")
    if result.errors:
        print(f"{len(result.errors)} items could not be fetched (see --verbose)")
        for url, error in result.errors[:5]:
            log.debug("scan error for %s: %s", url, error)
    print()
    print(table(opportunity_rows(best), OPPORTUNITY_COLUMNS))
    if best:
        print(f"\nTop pick: {best[0].describe()}")
        risky = [opportunity for opportunity in best if opportunity.risks]
        if risky:
            print("\nRisk notes:")
            for opportunity in risky[:5]:
                print(f"  {opportunity.item_name}: {'; '.join(opportunity.risks)}")
        print("\nEvery trade still happens in-game: whisper the seller, meet them, trade by hand.")
    if args.notify:
        for opportunity in best:
            context.notifier.opportunity(opportunity)
    return 0


def cmd_item(context: Context, args: argparse.Namespace) -> int:
    scanner = context.scanner()
    items = resolve_items(context.client, [args.name])
    url_name = items[0].url_name
    try:
        results = scanner.inspect(url_name)
    except NotFound:
        print(f"No such item: {args.name}", file=sys.stderr)
        return 2

    if args.json:
        emit_json(
            [
                {
                    "valuation": summarise(valuation),
                    "opportunities": [asdict(o) | {"score": o.score} for o in opportunities],
                }
                for valuation, opportunities in results
            ]
        )
        return 0

    for valuation, opportunities in results:
        variant = []
        if valuation.mod_rank is not None:
            variant.append(f"rank {valuation.mod_rank}")
        if valuation.subtype:
            variant.append(valuation.subtype)
        label = f" [{', '.join(variant)}]" if variant else ""
        print(f"\n{valuation.item_name}{label}  ({valuation.item_url})")
        print(f"  lowest live sell : {_p(valuation.ask)}")
        print(f"  highest live buy : {_p(valuation.bid)}")
        print(f"  fair value       : {_p(valuation.fair)}"
              f"   (history {_p(valuation.hist_ref)}, book {_p(valuation.book_ref)})")
        print(f"  live depth       : {valuation.depth_sell} sellers / {valuation.depth_buy} buyers")
        print(f"  volume           : {valuation.volume_per_day:.1f} trades/day")
        if valuation.risks:
            print(f"  risks            : {'; '.join(valuation.risks)}")
        if opportunities:
            print()
            print(table(opportunity_rows(opportunities), OPPORTUNITY_COLUMNS))
        else:
            print("  no opportunity at your current budget and margin settings")

        if args.whisper and valuation.best_ask:
            text = whisper(
                valuation.best_ask.user_name,
                valuation.item_name,
                valuation.best_ask.platinum,
                side="buy",
                rank=valuation.mod_rank,
            )
            copied = copy_to_clipboard(text)
            print(f"\n  {'copied: ' if copied else ''}{text}")
    return 0


def _p(value: Any) -> str:
    if value is None:
        return "-"
    return f"{value:.0f}p" if isinstance(value, float) else f"{value}p"


def cmd_orders(context: Context, args: argparse.Namespace) -> int:
    trader = context.trader()
    plan = trader.plan()
    rows = []
    for decision in plan.decisions:
        valuation = plan.valuations.get(decision.order_id)
        rows.append(
            {
                "item": decision.item_name,
                "side": decision.order_type,
                "qty": decision.quantity,
                "yours": f"{decision.current}p",
                "target": f"{decision.target}p",
                "delta": f"{decision.delta:+}p" if decision.changed else "-",
                "fair": _p(valuation.fair) if valuation and valuation.fair else "-",
                "best": _p(valuation.ask if decision.order_type == "sell" else valuation.bid)
                if valuation
                else "-",
                "why": decision.reason,
            }
        )
    if args.json:
        emit_json(rows)
        return 0
    print()
    print(
        table(
            rows,
            [
                ("item", "ITEM"),
                ("side", "SIDE"),
                ("qty", "QTY"),
                ("yours", "YOURS"),
                ("target", "TARGET"),
                ("delta", "DELTA"),
                ("fair", "FAIR"),
                ("best", "MARKET"),
                ("why", "REASON"),
            ],
        )
    )
    for label, why in plan.skipped:
        print(f"  skipped {label}: {why}")
    return 0


def cmd_reprice(context: Context, args: argparse.Namespace) -> int:
    trader = context.trader()
    plan = trader.plan()
    changes = plan.changes
    if not changes:
        print("Every listing is already priced correctly.")
        for label, why in plan.skipped:
            print(f"  skipped {label}: {why}")
        return 0

    print(f"\n{len(changes)} listing(s) to reprice:")
    for decision in changes:
        print(
            f"  {decision.item_name:<34} {decision.order_type:<4} "
            f"{decision.current}p -> {decision.target}p  ({decision.delta:+}p)  {decision.reason}"
        )
    for label, why in plan.skipped:
        print(f"  skipped {label}: {why}")

    if not args.live:
        print("\nDry run - nothing was changed. Re-run with --live to apply.")
        trader.apply(plan, live=False)
        return 0

    if not args.yes:
        answer = input(f"\nApply {len(changes)} price change(s) to your live listings? [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 1

    results = trader.apply(plan, live=True)
    ok = sum(1 for result in results if result.ok)
    print(f"\nUpdated {ok}/{len(results)} listing(s).")
    for result in results:
        if not result.ok:
            print(f"  failed: {result.decision.item_name} - {result.detail}")
    return 0 if ok == len(results) else 1


def cmd_watch(context: Context, args: argparse.Namespace) -> int:
    scanner = context.scanner()
    notifier = context.notifier
    interval = max(60, args.interval)
    print(f"Watching the market every {interval}s. Ctrl-C to stop.")
    try:
        while True:
            result = scanner.scan(limit=args.candidates)
            best = result.best(args.limit)
            stamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{stamp}] {len(result.opportunities)} opportunities across {result.scanned} items")
            if best:
                print(table(opportunity_rows(best), OPPORTUNITY_COLUMNS))
                for opportunity in best:
                    notifier.opportunity(opportunity)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def cmd_autopilot(context: Context, args: argparse.Namespace) -> int:
    """Reprice your listings and hunt for deals on a loop."""
    scanner = context.scanner()
    trader = context.trader()
    notifier = context.notifier
    interval = max(120, args.interval)
    stop = threading.Event()

    watcher: LogWatcher | None = None
    if context.config.logwatch.enabled:
        watcher = LogWatcher(context.config.logwatch)
        if watcher.available():
            def handle(event: LogEvent) -> None:
                if event.kind == "whisper":
                    notifier.send("Warframe", f"{event.user or 'someone'} wants to trade", key=None)
                elif event.kind in ("game_start", "game_stop") and context.config.trade.hide_orders_when_offline:
                    visible = event.kind == "game_start"
                    changed = trader.set_visibility(visible, live=args.live)
                    if changed:
                        print(f"  set {changed} listing(s) visible={visible}")

            watcher.run_in_background(handle, stop)
            print(f"Watching {watcher.path}")
        else:
            print(f"EE.log not found ({describe_paths()}); log watching disabled")

    mode = "LIVE" if args.live else "dry run"
    print(f"Autopilot running in {mode}, every {interval}s. Ctrl-C to stop.")
    try:
        while True:
            cycle_started = time.time()
            try:
                plan = trader.plan()
                results = trader.apply(plan, live=args.live)
                if results:
                    applied = sum(1 for result in results if result.ok)
                    print(f"  repriced {applied}/{len(results)} listing(s)")
            except WFMError as exc:
                print(f"  reprice skipped: {exc}")

            try:
                result = scanner.scan(limit=args.candidates)
                for opportunity in result.best(args.limit):
                    notifier.opportunity(opportunity)
                print(f"  scanned {result.scanned} items, {len(result.opportunities)} opportunities")
            except WFMError as exc:
                print(f"  scan failed: {exc}")

            elapsed = time.time() - cycle_started
            time.sleep(max(5.0, interval - elapsed))
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        stop.set()
    return 0


def cmd_whisper(context: Context, args: argparse.Namespace) -> int:
    scanner = context.scanner()
    items = resolve_items(context.client, [args.name])
    results = scanner.inspect(items[0].url_name)
    if not results:
        print("No market data for that item.", file=sys.stderr)
        return 2
    valuation = results[0][0]
    order = valuation.best_bid if args.sell else valuation.best_ask
    if not order:
        side = "buyer" if args.sell else "seller"
        print(f"No live {side} for {valuation.item_name} right now.", file=sys.stderr)
        return 1
    text = whisper(
        order.user_name,
        valuation.item_name,
        order.platinum,
        side="sell" if args.sell else "buy",
        rank=valuation.mod_rank,
    )
    copied = copy_to_clipboard(text)
    print(text)
    if copied:
        print("(copied to clipboard)")
    return 0


def cmd_logwatch(context: Context, args: argparse.Namespace) -> int:
    watcher = LogWatcher(context.config.logwatch)
    print(f"EE.log: {watcher.path or describe_paths()}")
    if not watcher.available():
        print("Log file not found. Set logwatch.path in your config.", file=sys.stderr)
        return 2
    print("Tailing. Ctrl-C to stop.")
    stop = threading.Event()
    try:
        for event in watcher.follow(stop):
            stamp = event.at.astimezone().strftime("%H:%M:%S")
            who = f" [{event.user}]" if event.user else ""
            print(f"{stamp} {event.kind}{who}: {event.line[:140]}")
    except KeyboardInterrupt:
        stop.set()
        print("\nStopped.")
    return 0


def cmd_history(context: Context, args: argparse.Namespace) -> int:
    items = resolve_items(context.client, [args.name])
    rows = context.db.price_history(items[0].url_name, days=args.days)
    if not rows:
        print("No local history yet - run a few scans first.")
        return 0
    formatted = [
        {
            "when": datetime.fromtimestamp(row["ts"]).strftime("%Y-%m-%d %H:%M"),
            "ask": _p(row["ask"]),
            "bid": _p(row["bid"]),
            "fair": _p(row["fair"]),
        }
        for row in rows
    ]
    print(table(formatted, [("when", "WHEN"), ("ask", "ASK"), ("bid", "BID"), ("fair", "FAIR")]))
    low = context.db.lowest_seen(items[0].url_name, days=args.days)
    if low:
        print(f"\nLowest ask seen in {args.days:.0f} days: {low}p")
    return 0


def cmd_actions(context: Context, args: argparse.Namespace) -> int:
    rows = context.db.recent_actions(args.limit)
    formatted = [
        {
            "when": datetime.fromtimestamp(row["ts"]).strftime("%Y-%m-%d %H:%M"),
            "action": row["action"],
            "item": row["item"],
            "side": row["order_type"],
            "change": f"{row['old_price']}p -> {row['new_price']}p"
            if row["new_price"] is not None
            else "-",
            "live": "live" if row["live"] else "dry",
            "result": row["result"],
        }
        for row in rows
    ]
    print(
        table(
            formatted,
            [
                ("when", "WHEN"),
                ("action", "ACTION"),
                ("item", "ITEM"),
                ("side", "SIDE"),
                ("change", "CHANGE"),
                ("live", "MODE"),
                ("result", "RESULT"),
            ],
        )
    )
    return 0


def cmd_config(context: Context, args: argparse.Namespace) -> int:
    config = context.config
    print(f"config file : {config.source_path or '(defaults, no file found)'}")
    print(f"state dir   : {config.state_dir}")
    print(f"database    : {config.db_path}")
    print(f"audit log   : {config.audit_path}")
    print(f"platform    : {config.api.platform}")
    print(f"signed in   : {'yes' if context.client.authenticated else 'no'}")
    print(f"ingame name : {config.trade.ingame_name or context.client.user_name or '(unset)'}")
    print(f"live trading: {'ENABLED' if config.trade.live else 'disabled'}")
    print(f"EE.log      : {describe_paths()}")
    if args.json:
        emit_json(
            {
                "api": asdict(config.api),
                "scan": asdict(config.scan),
                "trade": asdict(config.trade),
                "notify": asdict(config.notify),
                "logwatch": asdict(config.logwatch),
            }
        )
    return 0


def cmd_cache(context: Context, args: argparse.Namespace) -> int:
    if args.clear:
        client = context.client
        removed = client.cache.clear() if client.cache else 0
        print(f"Removed {removed} cached response(s).")
    else:
        files = list(context.config.cache_dir.glob("*.json"))
        size = sum(path.stat().st_size for path in files) / 1024
        print(f"{len(files)} cached response(s), {size:.0f} KiB in {context.config.cache_dir}")
    return 0


# ----------------------------------------------------------------------- parser


class _Parser(argparse.ArgumentParser):
    """Argument parser that tolerates global flags on either side of the command.

    The flags use SUPPRESS so a subparser cannot reset a value given before the
    command name, which means absent flags need their defaults filled in here.
    `set_defaults` cannot do it: parents share action objects, so it would put
    the default back on the subparsers too.
    """

    GLOBAL_DEFAULTS = {
        "config": None,
        "platform": None,
        "verbose": False,
        "quiet": False,
        "json": False,
    }

    def parse_args(self, args=None, namespace=None):  # type: ignore[override]
        parsed = super().parse_args(args, namespace)
        for name, value in self.GLOBAL_DEFAULTS.items():
            if not hasattr(parsed, name):
                setattr(parsed, name, value)
        return parsed


def build_parser() -> argparse.ArgumentParser:
    # Global flags are accepted both before and after the subcommand, because
    # `wfbot scan --json` is what everyone types. SUPPRESS stops a subparser
    # from overwriting a value that was given earlier on the line.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-c", "--config", help="path to a wfbot.toml", default=argparse.SUPPRESS)
    common.add_argument(
        "--platform", choices=["pc", "ps4", "xbox", "switch"], default=argparse.SUPPRESS
    )
    common.add_argument("-v", "--verbose", action="store_true", default=argparse.SUPPRESS)
    common.add_argument(
        "-q", "--quiet", action="store_true", help="no progress bars", default=argparse.SUPPRESS
    )
    common.add_argument(
        "--json", action="store_true", help="machine readable output", default=argparse.SUPPRESS
    )

    parser = _Parser(
        prog="wfbot",
        description=BANNER,
        parents=[common],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"wfbot {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def sub_parser(name: str, **kwargs: Any) -> argparse.ArgumentParser:
        return subparsers.add_parser(name, parents=[common], **kwargs)

    sub = argparse.Namespace(add_parser=sub_parser)

    login = sub.add_parser("login", help="authenticate for listing management")
    login.add_argument("--email")
    login.add_argument("--token", help="paste a JWT instead of signing in ('-' reads stdin)")
    login.add_argument("--ingame-name")
    login.set_defaults(func=cmd_login)

    scan = sub.add_parser("scan", help="find profitable trades")
    scan.add_argument("--items", nargs="*", help="only these items, by name or url_name")
    scan.add_argument("--budget", type=int, help="platinum you can spend")
    scan.add_argument("--limit", type=int, default=20, help="rows to display")
    scan.add_argument("--candidates", type=int, help="items to pull order books for")
    scan.add_argument("--refresh-universe", action="store_true", help="redo the triage pass")
    scan.add_argument("--notify", action="store_true", help="also send desktop notifications")
    scan.set_defaults(func=cmd_scan)

    item = sub.add_parser("item", help="detailed view of one item")
    item.add_argument("name")
    item.add_argument("--budget", type=int)
    item.add_argument("--whisper", action="store_true", help="copy a whisper for the cheapest seller")
    item.set_defaults(func=cmd_item)

    orders = sub.add_parser("orders", help="your listings versus the market")
    orders.set_defaults(func=cmd_orders)

    reprice = sub.add_parser("reprice", help="re-price your listings (dry run by default)")
    reprice.add_argument("--live", action="store_true", help="actually change prices")
    reprice.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    reprice.set_defaults(func=cmd_reprice)

    watch = sub.add_parser("watch", help="rescan on a loop and notify")
    watch.add_argument("--interval", type=int, default=600)
    watch.add_argument("--limit", type=int, default=10)
    watch.add_argument("--candidates", type=int)
    watch.add_argument("--budget", type=int)
    watch.set_defaults(func=cmd_watch)

    autopilot = sub.add_parser("autopilot", help="reprice + hunt, continuously")
    autopilot.add_argument("--interval", type=int, default=900)
    autopilot.add_argument("--limit", type=int, default=10)
    autopilot.add_argument("--candidates", type=int)
    autopilot.add_argument("--budget", type=int)
    autopilot.add_argument("--live", action="store_true", help="allow real price changes")
    autopilot.set_defaults(func=cmd_autopilot)

    whisper_cmd = sub.add_parser("whisper", help="build the in-game trade message")
    whisper_cmd.add_argument("name")
    whisper_cmd.add_argument("--sell", action="store_true", help="target the best buyer instead")
    whisper_cmd.set_defaults(func=cmd_whisper)

    logwatch = sub.add_parser("logwatch", help="tail EE.log for trade activity")
    logwatch.set_defaults(func=cmd_logwatch)

    history = sub.add_parser("history", help="locally recorded price history")
    history.add_argument("name")
    history.add_argument("--days", type=float, default=30.0)
    history.set_defaults(func=cmd_history)

    actions = sub.add_parser("actions", help="audit log of everything the bot did")
    actions.add_argument("--limit", type=int, default=25)
    actions.set_defaults(func=cmd_actions)

    config_cmd = sub.add_parser("config", help="show the resolved configuration")
    config_cmd.set_defaults(func=cmd_config)

    cache = sub.add_parser("cache", help="inspect or clear the response cache")
    cache.add_argument("--clear", action="store_true")
    cache.set_defaults(func=cmd_cache)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        context = Context(args)
        return int(args.func(context, args) or 0)
    except AuthError as exc:
        print(f"Authentication error: {exc}", file=sys.stderr)
        return 2
    except WFMError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
