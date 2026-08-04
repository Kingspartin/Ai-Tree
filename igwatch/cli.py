"""Command line entry point."""

from __future__ import annotations

import argparse
import logging
import os
import re
import signal
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from . import __version__
from .checker import AvailabilityChecker, InvalidUsername, normalize_username
from .http import HttpClient
from .models import Availability
from .notifiers import (
    CommandNotifier,
    ConsoleNotifier,
    DesktopNotifier,
    EmailNotifier,
    NotifierGroup,
    NtfyNotifier,
    WebhookNotifier,
)
from .state import StateStore, default_state_path
from .watcher import Watcher, WatchConfig

EXIT_AVAILABLE = 0
EXIT_TAKEN = 1
EXIT_UNKNOWN = 2
EXIT_USAGE = 3
EXIT_INTERRUPTED = 130

_DURATION_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)(?P<unit>[smhd]?)", re.IGNORECASE)
_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "": 1}


def parse_duration(text: str) -> float:
    """``90`` / ``90s`` / ``5m`` / ``1h30m`` -> seconds."""

    raw = str(text).strip().lower()
    if not raw:
        raise argparse.ArgumentTypeError("empty duration")
    total = 0.0
    position = 0
    for match in _DURATION_RE.finditer(raw):
        if match.start() != position:
            break
        total += float(match.group("value")) * _UNITS[match.group("unit")]
        position = match.end()
    if position != len(raw) or total <= 0:
        raise argparse.ArgumentTypeError(f"could not parse duration: {text!r}")
    return total


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="igwatch",
        description=(
            "Watch one or more Instagram usernames and shout the moment one "
            "looks available."
        ),
        epilog=(
            "examples:\n"
            "  igwatch kingspartin --desktop\n"
            "  igwatch kingspartin --once\n"
            "  igwatch name_a name_b --interval 10m --ntfy my-secret-topic\n"
            "  igwatch name --webhook https://hooks.slack.com/services/...\n"
            "  igwatch --test-notify --desktop --ntfy my-secret-topic\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("usernames", nargs="*", help="username, @username, or profile URL")
    parser.add_argument("--version", action="version", version=f"igwatch {__version__}")

    schedule = parser.add_argument_group("schedule")
    schedule.add_argument(
        "--interval",
        type=parse_duration,
        default="5m",
        help="time between checks, e.g. 90s, 5m, 1h (default: 5m, floor: 60s)",
    )
    schedule.add_argument(
        "--jitter",
        type=float,
        default=0.2,
        help="randomise each wait by +/- this fraction (default: 0.2)",
    )
    schedule.add_argument(
        "--once",
        action="store_true",
        help="check once and exit (0=available, 1=taken, 2=unknown); good for cron",
    )
    schedule.add_argument(
        "--confirmations",
        type=int,
        default=2,
        help="consecutive 'available' answers required before alerting (default: 2)",
    )
    schedule.add_argument(
        "--confirm-delay",
        type=parse_duration,
        default="15s",
        help="pause between confirmation checks (default: 15s)",
    )
    schedule.add_argument(
        "--max-backoff",
        type=parse_duration,
        default="1h",
        help="longest wait after repeated inconclusive checks (default: 1h)",
    )
    schedule.add_argument(
        "--keep-watching",
        action="store_true",
        help="keep polling after an alert instead of exiting",
    )
    schedule.add_argument(
        "--repeat-alert",
        action="store_true",
        help="alert on every check while the name stays free (default: alert once)",
    )

    lookup = parser.add_argument_group("lookup")
    lookup.add_argument(
        "--strategy",
        choices=("auto", "api", "page"),
        default="auto",
        help="how to ask Instagram (default: auto = api, falling back to page)",
    )
    lookup.add_argument(
        "--session-id",
        default=os.environ.get("IGWATCH_SESSIONID"),
        help="Instagram sessionid cookie; improves reliability (env: IGWATCH_SESSIONID)",
    )
    lookup.add_argument(
        "--timeout", type=parse_duration, default="20s", help="per-request timeout (default: 20s)"
    )

    alerts = parser.add_argument_group("alerts")
    alerts.add_argument("--desktop", action="store_true", help="desktop notification")
    alerts.add_argument(
        "--webhook", action="append", default=[], metavar="URL",
        help="POST JSON to a URL (Slack and Discord formats auto-detected); repeatable",
    )
    alerts.add_argument(
        "--ntfy", action="append", default=[], metavar="TOPIC",
        help="push via ntfy.sh topic or full server URL; repeatable",
    )
    alerts.add_argument("--email", metavar="ADDRESS", help="send mail (needs IGWATCH_SMTP_* env)")
    alerts.add_argument(
        "--exec", action="append", default=[], metavar="CMD", dest="exec_",
        help="run a command; {username} {url} {status} {title} {body} are substituted",
    )
    alerts.add_argument("--no-console", action="store_true", help="suppress the console banner")
    alerts.add_argument(
        "--test-notify", action="store_true", help="send a test alert through every channel and exit"
    )

    misc = parser.add_argument_group("misc")
    misc.add_argument(
        "--state-file", type=Path, default=None,
        help=f"where to persist progress (default: {default_state_path()})",
    )
    misc.add_argument("--no-state", action="store_true", help="do not read or write a state file")
    misc.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    misc.add_argument("-q", "--quiet", action="store_true", help="warnings and errors only")
    return parser


def build_notifiers(args: argparse.Namespace) -> NotifierGroup:
    notifiers: List = []
    if not args.no_console:
        notifiers.append(ConsoleNotifier())
    if args.desktop:
        notifiers.append(DesktopNotifier())
    shared = HttpClient(timeout=args.timeout)
    for url in args.webhook:
        notifiers.append(WebhookNotifier(url, client=shared))
    for topic in args.ntfy:
        notifiers.append(NtfyNotifier(topic, client=shared))
    if args.email:
        notifiers.append(EmailNotifier(args.email))
    for command in args.exec_:
        notifiers.append(CommandNotifier(command))
    return NotifierGroup(notifiers)


def configure_logging(args: argparse.Namespace) -> None:
    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args)
    log = logging.getLogger("igwatch")

    try:
        notifiers = build_notifiers(args)
    except ValueError as exc:
        parser.error(str(exc))
        return EXIT_USAGE

    if args.test_notify:
        delivered = notifiers.send(
            "igwatch test alert",
            "If you can read this, igwatch can reach you when a username frees up.",
        )
        print(f"delivered to {delivered}/{len(notifiers)} channel(s): {', '.join(notifiers.names)}")
        return EXIT_AVAILABLE if delivered else EXIT_UNKNOWN

    if not args.usernames:
        parser.error("give at least one username (or use --test-notify)")
        return EXIT_USAGE

    try:
        usernames = [normalize_username(name) for name in args.usernames]
    except InvalidUsername as exc:
        parser.error(str(exc))
        return EXIT_USAGE

    if len(notifiers) == 0:
        log.warning("no alert channels configured - results will only be logged")

    checker = AvailabilityChecker(
        client=HttpClient(timeout=args.timeout),
        strategy=args.strategy,
        session_id=args.session_id,
    )
    state = None if args.no_state else StateStore(args.state_file)

    config = WatchConfig(
        interval=args.interval,
        jitter=args.jitter,
        confirmations=args.confirmations,
        confirm_delay=args.confirm_delay,
        max_backoff=args.max_backoff,
        stop_after_alert=not args.keep_watching,
        repeat_alert=args.repeat_alert,
    )
    watcher = Watcher(usernames, checker, notifiers, config=config, state=state)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, lambda *_: watcher.stop())
        except (ValueError, OSError):  # not on the main thread / unsupported
            pass

    if args.once:
        return _run_once(watcher, usernames, state, log)

    try:
        watcher.run()
    finally:
        if state is not None:
            state.save()

    if watcher.stopped:
        log.info("stopped")
        return EXIT_INTERRUPTED
    return EXIT_AVAILABLE


def _run_once(watcher: Watcher, usernames: Sequence[str], state, log) -> int:
    statuses = []
    for username in usernames:
        result = watcher.check_once(username)
        if state is not None:
            state.record_check(username, result.status.value)
        print(f"{result}")
        if result.status is Availability.AVAILABLE:
            already = state.already_notified(username) if state else False
            if not already or watcher.config.repeat_alert:
                watcher.alert(result)
        statuses.append(result.status)
    if state is not None:
        state.save()

    if any(s is Availability.AVAILABLE for s in statuses):
        return EXIT_AVAILABLE
    if all(s is Availability.TAKEN for s in statuses):
        return EXIT_TAKEN
    return EXIT_UNKNOWN


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
