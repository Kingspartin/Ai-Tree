"""Valuation and opportunity ranking.

Everything here is a pure function of an order book plus its trade history, so
the decision logic is testable offline against fixtures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .config import ScanConfig, TradeConfig
from .models import BUY, SELL, ItemStats, Order, OrderBook, median, weighted_median

# How far the historical price and the current book may disagree before the
# valuation is treated as unreliable.
DISAGREEMENT_LIMIT = 0.35


@dataclass
class Valuation:
    """What one item is worth right now, and how much to trust that number."""

    item_url: str
    item_name: str
    mod_rank: int | None = None
    subtype: str | None = None
    fair: float | None = None
    book_ref: float | None = None
    hist_ref: float | None = None
    best_ask: Order | None = None
    best_bid: Order | None = None
    depth_sell: int = 0
    depth_buy: int = 0
    volume_per_day: float = 0.0
    dispersion: float = 0.0
    risks: list[str] = field(default_factory=list)

    @property
    def ask(self) -> int | None:
        return self.best_ask.platinum if self.best_ask else None

    @property
    def bid(self) -> int | None:
        return self.best_bid.platinum if self.best_bid else None

    @property
    def spread(self) -> int | None:
        if self.best_ask is None or self.best_bid is None:
            return None
        return self.best_ask.platinum - self.best_bid.platinum


@dataclass
class Opportunity:
    """A concrete, actionable trade with its expected profit."""

    kind: str  # "crossed" | "flip" | "spread"
    item_url: str
    item_name: str
    buy_at: int
    sell_at: int
    units: int
    volume_per_day: float
    confidence: float
    fair: float
    mod_rank: int | None = None
    subtype: str | None = None
    buy_from: str = ""
    sell_to: str = ""
    risks: list[str] = field(default_factory=list)

    @property
    def profit(self) -> int:
        return self.sell_at - self.buy_at

    @property
    def margin(self) -> float:
        return self.profit / self.buy_at if self.buy_at > 0 else 0.0

    @property
    def total_profit(self) -> int:
        return self.profit * self.units

    @property
    def score(self) -> float:
        """Expected platinum from acting on this, discounted by confidence."""
        return round(self.total_profit * self.confidence, 2)

    def describe(self) -> str:
        where = f"buy from {self.buy_from}" if self.buy_from else "buy"
        target = f"sell to {self.sell_to}" if self.sell_to else f"list at {self.sell_at}p"
        return f"{self.item_name}: {where} at {self.buy_at}p, {target} (+{self.profit}p/ea)"


def _price_dispersion(prices: list[int]) -> float:
    """Interquartile spread over the median: how disorderly the book is."""
    if len(prices) < 4:
        return 0.0
    ordered = sorted(prices)
    low = ordered[len(ordered) // 4]
    high = ordered[(3 * len(ordered)) // 4]
    mid = median(ordered) or 0
    return (high - low) / mid if mid else 0.0


def historical_price(
    stats: ItemStats, *, mod_rank: int | None = None, subtype: str | None = None
) -> float | None:
    """Volume-weighted median of recent closed sales."""
    for window, days in (("48hours", None), ("90days", 14.0), ("90days", 90.0)):
        points = stats.points(
            window=window, order_type=SELL, mod_rank=mod_rank, subtype=subtype, days=days
        )
        if not points:
            continue
        value = weighted_median(
            [point.wa_price or point.median for point in points],
            [point.volume for point in points],
        )
        if value:
            return value
    return None


def book_price(sells: list[Order]) -> float | None:
    """What the market is currently asking, ignoring the single cheapest listing.

    The cheapest listing is often the one you are about to buy, or a mistake.
    The next few are what you will actually compete with when you resell.
    """
    if not sells:
        return None
    prices = [order.platinum for order in sells[:6]]
    if len(prices) >= 3:
        return median(prices[1:4])
    return median(prices)


def evaluate(
    item_url: str,
    item_name: str,
    book: OrderBook,
    stats: ItemStats,
    config: ScanConfig | None = None,
    *,
    mod_rank: int | None = None,
    subtype: str | None = None,
) -> Valuation:
    """Price one tradable variant of one item."""
    config = config or ScanConfig()
    view = book.filtered(mod_rank=mod_rank, subtype=subtype)

    live_sells = view.sells(actionable_only=True, max_age_days=config.stale_order_days)
    live_buys = view.buys(actionable_only=True, max_age_days=config.stale_order_days)
    all_sells = view.sells(actionable_only=False)

    valuation = Valuation(
        item_url=item_url,
        item_name=item_name,
        mod_rank=mod_rank,
        subtype=subtype,
        best_ask=live_sells[0] if live_sells else None,
        best_bid=live_buys[0] if live_buys else None,
        depth_sell=len(live_sells),
        depth_buy=len(live_buys),
        volume_per_day=stats.volume_per_day(
            window="48hours", order_type=SELL, mod_rank=mod_rank, subtype=subtype
        ),
        dispersion=_price_dispersion([order.platinum for order in all_sells[:10]]),
    )
    valuation.hist_ref = historical_price(stats, mod_rank=mod_rank, subtype=subtype)
    valuation.book_ref = book_price(all_sells)

    if valuation.hist_ref and valuation.book_ref:
        gap = abs(valuation.hist_ref - valuation.book_ref) / max(
            valuation.hist_ref, valuation.book_ref
        )
        if gap > DISAGREEMENT_LIMIT:
            valuation.risks.append(f"history and book disagree by {gap:.0%}")
        # Conservative on purpose: an inflated reference price turns into a
        # phantom profit and a bag you cannot sell.
        valuation.fair = min(valuation.hist_ref, valuation.book_ref)
    else:
        valuation.fair = valuation.hist_ref or valuation.book_ref
        if valuation.hist_ref is None:
            valuation.risks.append("no recent trade history")

    if valuation.depth_sell < config.min_book_depth:
        valuation.risks.append(f"thin book ({valuation.depth_sell} live sellers)")
    if valuation.volume_per_day < config.min_volume:
        valuation.risks.append(f"low volume ({valuation.volume_per_day:.1f}/day)")
    if valuation.dispersion > 0.6:
        valuation.risks.append(f"wide price spread ({valuation.dispersion:.0%})")
    sellers = {order.user_name for order in live_sells}
    if live_sells and len(sellers) == 1:
        valuation.risks.append("one seller controls the book")
    return valuation


def _confidence(valuation: Valuation, config: ScanConfig, *, counterparties: list[Order]) -> float:
    """0..1 estimate that the modelled profit survives contact with reality."""
    volume_factor = min(1.0, valuation.volume_per_day / max(config.min_volume, 0.1))
    depth_factor = min(1.0, valuation.depth_sell / max(config.min_book_depth, 1))
    dispersion_factor = max(0.2, 1.0 - valuation.dispersion)

    freshness = 1.0
    for order in counterparties:
        age = order.age_days()
        if math.isinf(age):
            freshness = min(freshness, 0.5)
        elif age <= 1:
            freshness = min(freshness, 1.0)
        elif age <= config.stale_order_days:
            freshness = min(freshness, 0.75)
        else:
            freshness = min(freshness, 0.4)

    agreement = 1.0
    if valuation.hist_ref and valuation.book_ref:
        gap = abs(valuation.hist_ref - valuation.book_ref) / max(
            valuation.hist_ref, valuation.book_ref
        )
        agreement = max(0.3, 1.0 - gap)
    elif not valuation.hist_ref:
        agreement = 0.5

    factors = [volume_factor, depth_factor, dispersion_factor, freshness, agreement]
    # Geometric mean: one bad factor should drag the whole thing down.
    product = 1.0
    for factor in factors:
        product *= max(factor, 0.05)
    return round(product ** (1 / len(factors)), 3)


def _sellable_units(volume_per_day: float, available: int, affordable: int) -> int:
    """Cap size by what the item actually trades, not by what you can afford."""
    throughput = max(1, math.ceil(volume_per_day * 0.5))
    return max(0, min(available, affordable, throughput))


def find_opportunities(
    valuation: Valuation, book: OrderBook, config: ScanConfig | None = None
) -> list[Opportunity]:
    """Turn a valuation into the concrete trades worth making."""
    config = config or ScanConfig()
    found: list[Opportunity] = []
    if not valuation.best_ask or valuation.fair is None:
        return found

    view = book.filtered(mod_rank=valuation.mod_rank, subtype=valuation.subtype)
    ask_order = valuation.best_ask
    ask = ask_order.platinum
    if ask <= 0:
        return found
    if config.max_price and ask > config.max_price:
        return found
    affordable = config.budget // ask if ask else 0
    if affordable <= 0:
        return found

    # 1. Crossed book: somebody is bidding more than somebody else is asking.
    #    This is the only kind that does not depend on a price model.
    bid_order = valuation.best_bid
    if bid_order and bid_order.platinum > ask:
        units = _sellable_units(
            max(valuation.volume_per_day, 2.0),  # a standing bid is its own demand
            min(ask_order.quantity, bid_order.quantity),
            affordable,
        )
        if units > 0 and bid_order.platinum - ask >= config.min_profit:
            found.append(
                Opportunity(
                    kind="crossed",
                    item_url=valuation.item_url,
                    item_name=valuation.item_name,
                    mod_rank=valuation.mod_rank,
                    subtype=valuation.subtype,
                    buy_at=ask,
                    sell_at=bid_order.platinum,
                    units=units,
                    volume_per_day=valuation.volume_per_day,
                    confidence=_confidence(
                        valuation, config, counterparties=[ask_order, bid_order]
                    ),
                    fair=valuation.fair,
                    buy_from=ask_order.user_name,
                    sell_to=bid_order.user_name,
                    risks=list(valuation.risks),
                )
            )

    # 2. Flip: buy the underpriced listing, relist just under the next one.
    competitors = [
        order
        for order in view.sells(actionable_only=False)
        if order.id != ask_order.id and order.platinum > ask
    ]
    exit_ref = median([order.platinum for order in competitors[:3]]) if competitors else None
    candidates = [value for value in (valuation.fair, exit_ref) if value]
    if candidates:
        exit_at = int(min(candidates)) - 1
        exit_at = max(exit_at, ask + 1)
        profit = exit_at - ask
        margin = profit / ask
        if profit >= config.min_profit and margin >= config.min_margin:
            units = _sellable_units(valuation.volume_per_day, ask_order.quantity, affordable)
            if units > 0:
                risks = list(valuation.risks)
                if not competitors:
                    risks.append("no competing listing to price against")
                found.append(
                    Opportunity(
                        kind="flip",
                        item_url=valuation.item_url,
                        item_name=valuation.item_name,
                        mod_rank=valuation.mod_rank,
                        subtype=valuation.subtype,
                        buy_at=ask,
                        sell_at=exit_at,
                        units=units,
                        volume_per_day=valuation.volume_per_day,
                        confidence=_confidence(valuation, config, counterparties=[ask_order]),
                        fair=valuation.fair,
                        buy_from=ask_order.user_name,
                        risks=risks,
                    )
                )
    return found


@dataclass
class PriceDecision:
    """A proposed change to one of your own listings."""

    order_id: str
    item_url: str
    item_name: str
    order_type: str
    current: int
    target: int
    quantity: int
    reason: str
    mod_rank: int | None = None
    subtype: str | None = None
    visible: bool = True

    @property
    def delta(self) -> int:
        return self.target - self.current

    @property
    def changed(self) -> bool:
        return self.target != self.current


def suggest_price(
    order_type: str,
    current: int,
    book: OrderBook,
    valuation: Valuation,
    trade: TradeConfig,
    *,
    me: str,
) -> tuple[int, str]:
    """Where one of your own orders should sit, and why.

    Sells undercut the cheapest live competitor down to a floor; buys outbid the
    richest live competitor up to a ceiling. Both floors are derived from fair
    value so a price war cannot walk you into a loss.
    """
    if valuation.fair is None:
        return current, "no fair value available, leaving price alone"

    view = book.filtered(mod_rank=valuation.mod_rank, subtype=valuation.subtype)
    if order_type == SELL:
        competitors = view.sells(actionable_only=True, exclude_user=me)
        if not competitors:
            competitors = view.sells(actionable_only=False, exclude_user=me)
        floor = max(1, int(round(valuation.fair * trade.sell_floor_ratio)))
        if not competitors:
            target = max(floor, int(round(valuation.fair)))
            return target, "no competition, pricing at fair value"
        best = competitors[0].platinum
        target = best - trade.undercut_by
        if target < floor:
            return floor, f"floor {floor}p reached, refusing to chase {best}p"
        if target > current:
            return target, f"cheapest rival at {best}p, raising to just under"
        return target, f"undercutting {competitors[0].user_name} at {best}p"

    if order_type == BUY:
        competitors = view.buys(actionable_only=True, exclude_user=me)
        if not competitors:
            competitors = view.buys(actionable_only=False, exclude_user=me)
        ceiling = max(1, int(round(valuation.fair * trade.buy_ceiling_ratio)))
        if not competitors:
            target = min(ceiling, current if current > 0 else ceiling)
            return target, "no competing buyers, holding at ceiling"
        best = competitors[0].platinum
        target = best + trade.outbid_by
        if target > ceiling:
            return ceiling, f"ceiling {ceiling}p reached, refusing to outbid {best}p"
        return target, f"outbidding {competitors[0].user_name} at {best}p"

    return current, f"unknown order type {order_type!r}"


def summarise(valuation: Valuation) -> dict[str, Any]:
    """Flat dict for tables, JSON output and the price-history table."""
    return {
        "item": valuation.item_url,
        "name": valuation.item_name,
        "rank": valuation.mod_rank,
        "subtype": valuation.subtype,
        "ask": valuation.ask,
        "bid": valuation.bid,
        "spread": valuation.spread,
        "fair": round(valuation.fair, 1) if valuation.fair else None,
        "volume_per_day": round(valuation.volume_per_day, 2),
        "sellers": valuation.depth_sell,
        "buyers": valuation.depth_buy,
        "risks": valuation.risks,
    }
