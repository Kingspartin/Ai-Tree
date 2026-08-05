"""Two-stage market scan.

Stage 1 is cheap and wide: one statistics call per item (cached for hours) to
find what is liquid and affordable. Stage 2 is expensive and narrow: order books
for the best candidates only. Scanning every item's book on every run would take
half an hour at the API's rate limit and tell you nothing new about dead items.
"""

from __future__ import annotations

import fnmatch
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Sequence

from .analysis import (
    Opportunity,
    Valuation,
    evaluate,
    find_opportunities,
    historical_price,
    summarise,
)
from .api import WarframeMarketClient, WFMError
from .config import Config
from .models import Item, ItemStats, OrderBook
from .storage import Database

log = logging.getLogger(__name__)

Progress = Callable[[str, int, int], None]


@dataclass
class ScanResult:
    opportunities: list[Opportunity] = field(default_factory=list)
    valuations: list[Valuation] = field(default_factory=list)
    scanned: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)
    elapsed: float = 0.0

    def best(self, limit: int = 20) -> list[Opportunity]:
        return sorted(self.opportunities, key=lambda o: o.score, reverse=True)[:limit]


def matches(url_name: str, include: Sequence[str], exclude: Sequence[str]) -> bool:
    name = url_name.lower()
    if include and not any(fnmatch.fnmatch(name, pattern.lower()) for pattern in include):
        return False
    return not any(fnmatch.fnmatch(name, pattern.lower()) for pattern in exclude)


def variants_to_evaluate(book: OrderBook, limit: int = 3) -> list[tuple[int | None, str | None]]:
    """Which (rank, subtype) markets are worth pricing separately.

    Rank 0 and maxed copies of the same mod trade at wildly different prices, so
    they must never share a valuation.
    """
    counts: dict[tuple[int | None, str | None], int] = {}
    for order in book.orders:
        if not order.visible:
            continue
        key = (order.mod_rank, order.subtype)
        counts[key] = counts.get(key, 0) + 1
    if len(counts) <= 1:
        return [next(iter(counts), (None, None))]
    ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    return [key for key, count in ranked[:limit] if count >= 2] or [ranked[0][0]]


class Scanner:
    def __init__(
        self,
        client: WarframeMarketClient,
        config: Config,
        database: Database | None = None,
        on_progress: Progress | None = None,
    ) -> None:
        self.client = client
        self.config = config
        self.db = database
        self.on_progress = on_progress or (lambda stage, done, total: None)

    # ------------------------------------------------------------------ stage 1

    def universe(self) -> list[Item]:
        """Every tradable item matching the configured include/exclude globs."""
        items = self.client.items()
        scan = self.config.scan
        return [
            item
            for item in items
            if item.url_name and matches(item.url_name, scan.include_patterns, scan.exclude_patterns)
        ]

    def rank_candidates(self, items: Sequence[Item], limit: int) -> list[Item]:
        """Score items by platinum throughput; return the top `limit`."""
        scan = self.config.scan
        rows: list[dict] = []
        done = 0
        total = len(items)

        def fetch(item: Item) -> ItemStats:
            return self.client.statistics(item.url_name)

        for item, stats, error in self.client.map(fetch, list(items)):
            done += 1
            self.on_progress("triage", done, total)
            if error or stats is None:
                log.debug("statistics failed for %s: %s", item.url_name, error)
                continue
            volume = stats.volume_per_day(window="48hours")
            if volume <= 0:
                volume = stats.volume_per_day(window="90days", days=14.0)
            price = historical_price(stats) or 0.0
            if price <= 0 or volume <= 0:
                continue
            if scan.max_price and price > scan.max_price:
                continue
            if price > scan.budget:
                # You cannot flip what you cannot afford to buy once.
                continue
            rows.append(
                {
                    "item": item.url_name,
                    "name": item.name,
                    "price": price,
                    "volume_per_day": volume,
                    # Throughput in platinum per day: the pool of profit that
                    # exists at all for this item.
                    "liquidity": price * volume,
                }
            )

        if self.db and rows:
            self.db.save_universe(rows)
        rows.sort(key=lambda row: row["liquidity"], reverse=True)
        by_url = {item.url_name: item for item in items}
        return [by_url[row["item"]] for row in rows[:limit] if row["item"] in by_url]

    def cached_candidates(self, limit: int, max_age_hours: float = 24.0) -> list[Item]:
        """Reuse the last triage pass so routine scans start immediately."""
        if not self.db:
            return []
        rows = self.db.top_universe(limit, max_age_hours=max_age_hours)
        return [Item(url_name=row["item"], name=row["name"] or row["item"]) for row in rows]

    # ------------------------------------------------------------------ stage 2

    def scan(
        self,
        items: Sequence[Item] | None = None,
        *,
        limit: int | None = None,
        use_cached_triage: bool = True,
    ) -> ScanResult:
        started = time.monotonic()
        scan_config = self.config.scan
        limit = limit or scan_config.candidate_limit

        if items is None:
            items = self.cached_candidates(limit) if use_cached_triage else []
            if not items:
                items = self.rank_candidates(self.universe(), limit)

        result = ScanResult()
        total = len(items)
        done = 0

        def fetch(item: Item) -> tuple[OrderBook, ItemStats]:
            return self.client.orders(item.url_name), self.client.statistics(item.url_name)

        for item, payload, error in self.client.map(fetch, list(items)):
            done += 1
            self.on_progress("scan", done, total)
            if error or payload is None:
                result.errors.append((item.url_name, str(error)))
                continue
            book, stats = payload
            result.scanned += 1
            for mod_rank, subtype in variants_to_evaluate(book):
                valuation = evaluate(
                    item.url_name,
                    item.name,
                    book,
                    stats,
                    scan_config,
                    mod_rank=mod_rank,
                    subtype=subtype,
                )
                result.valuations.append(valuation)
                for opportunity in find_opportunities(valuation, book, scan_config):
                    result.opportunities.append(opportunity)
                    if self.db:
                        self.db.record_opportunity(opportunity)
                if self.db:
                    self.db.record_snapshot(summarise(valuation))

        result.opportunities.sort(key=lambda o: o.score, reverse=True)
        result.elapsed = time.monotonic() - started
        return result

    def inspect(self, url_name: str) -> list[tuple[Valuation, list[Opportunity]]]:
        """Full detail for a single item, across its tradable variants."""
        book = self.client.orders(url_name)
        stats = self.client.statistics(url_name)
        detail = {}
        try:
            detail = self.client.item_detail(url_name)
        except WFMError:
            pass
        name = url_name.replace("_", " ").title()
        for entry in (detail.get("items_in_set") or []):
            if entry.get("url_name") == url_name:
                name = (entry.get("en") or {}).get("item_name") or name
        results = []
        for mod_rank, subtype in variants_to_evaluate(book, limit=6):
            valuation = evaluate(
                url_name, name, book, stats, self.config.scan, mod_rank=mod_rank, subtype=subtype
            )
            results.append((valuation, find_opportunities(valuation, book, self.config.scan)))
        return results


def resolve_items(client: WarframeMarketClient, names: Iterable[str]) -> list[Item]:
    """Map user-typed names ('Loki Prime Set') onto API url_names."""
    catalogue = client.items()
    by_url = {item.url_name: item for item in catalogue}
    by_name = {item.name.lower(): item for item in catalogue}
    resolved: list[Item] = []
    for raw in names:
        key = raw.strip()
        slug = key.lower().replace(" ", "_").replace("'", "")
        if slug in by_url:
            resolved.append(by_url[slug])
        elif key.lower() in by_name:
            resolved.append(by_name[key.lower()])
        else:
            close = [item for item in catalogue if slug in item.url_name]
            if len(close) == 1:
                resolved.append(close[0])
            else:
                raise WFMError(
                    f"no item matches {raw!r}"
                    + (f" (did you mean: {', '.join(c.url_name for c in close[:5])}?)" if close else "")
                )
    return resolved
