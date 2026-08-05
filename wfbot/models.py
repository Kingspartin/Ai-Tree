"""Typed views over the warframe.market JSON payloads."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

SELL = "sell"
BUY = "buy"
TRADABLE_STATUSES = ("ingame",)


def parse_dt(value: Any) -> datetime | None:
    """Parse the ISO-8601 timestamps the API returns, tolerating variants."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        # Some endpoints emit more than 6 fractional digits, which fromisoformat
        # rejected before 3.11 and still rejects for odd lengths.
        head, _, tail = text.partition(".")
        if not tail:
            return None
        digits = "".join(ch for ch in tail if ch.isdigit())[:6]
        offset = tail[len(digits):].lstrip("0123456789")
        try:
            parsed = datetime.fromisoformat(f"{head}.{digits or '0'}{offset}")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Order:
    """A single listing on warframe.market."""

    id: str
    order_type: str
    platinum: int
    quantity: int
    user_name: str
    user_status: str
    reputation: int = 0
    visible: bool = True
    mod_rank: int | None = None
    subtype: str | None = None
    platform: str = "pc"
    region: str = "en"
    creation_date: datetime | None = None
    last_update: datetime | None = None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "Order":
        user = raw.get("user") or {}
        return cls(
            id=str(raw.get("id", "")),
            order_type=str(raw.get("order_type", "")),
            platinum=int(raw.get("platinum") or 0),
            quantity=int(raw.get("quantity") or 0),
            user_name=str(user.get("ingame_name") or raw.get("ingame_name") or ""),
            user_status=str(user.get("status") or raw.get("status") or "offline"),
            reputation=int(user.get("reputation") or 0),
            visible=bool(raw.get("visible", True)),
            mod_rank=raw.get("mod_rank"),
            subtype=raw.get("subtype"),
            platform=str(raw.get("platform") or user.get("platform") or "pc"),
            region=str(raw.get("region") or user.get("region") or "en"),
            creation_date=parse_dt(raw.get("creation_date")),
            last_update=parse_dt(raw.get("last_update")),
        )

    @property
    def is_sell(self) -> bool:
        return self.order_type == SELL

    @property
    def is_buy(self) -> bool:
        return self.order_type == BUY

    def actionable(self) -> bool:
        """True when this counterparty could trade with you right now."""
        return self.visible and self.quantity > 0 and self.user_status in TRADABLE_STATUSES

    def age_days(self, reference: datetime | None = None) -> float:
        stamp = self.last_update or self.creation_date
        if stamp is None:
            return math.inf
        return ((reference or now()) - stamp).total_seconds() / 86400.0


@dataclass
class OrderBook:
    """Both sides of the book for one item (optionally one rank/subtype)."""

    item_url: str
    orders: list[Order] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=now)

    @classmethod
    def from_api(cls, item_url: str, payload: dict[str, Any]) -> "OrderBook":
        raw = (payload.get("payload") or {}).get("orders") or []
        return cls(item_url=item_url, orders=[Order.from_api(entry) for entry in raw])

    def filtered(
        self,
        *,
        platform: str | None = None,
        mod_rank: int | None = None,
        subtype: str | None = None,
    ) -> "OrderBook":
        """Narrow to a single tradable variant.

        A rank-0 mod and a maxed mod are different markets; mixing them produces
        nonsense prices, so ranked items must always be split before analysis.
        """
        selected = []
        for order in self.orders:
            if platform and order.platform != platform:
                continue
            if mod_rank is not None and order.mod_rank is not None and order.mod_rank != mod_rank:
                continue
            if subtype is not None and order.subtype is not None and order.subtype != subtype:
                continue
            selected.append(order)
        return OrderBook(item_url=self.item_url, orders=selected, fetched_at=self.fetched_at)

    def side(
        self,
        order_type: str,
        *,
        actionable_only: bool = True,
        exclude_user: str | None = None,
        max_age_days: float | None = None,
    ) -> list[Order]:
        """Sells ascending (cheapest first), buys descending (richest first)."""
        reference = now()
        chosen: list[Order] = []
        for order in self.orders:
            if order.order_type != order_type:
                continue
            if actionable_only and not order.actionable():
                continue
            if exclude_user and order.user_name.lower() == exclude_user.lower():
                continue
            if max_age_days is not None and order.age_days(reference) > max_age_days:
                continue
            chosen.append(order)
        return sorted(chosen, key=lambda o: o.platinum, reverse=(order_type == BUY))

    def sells(self, **kwargs: Any) -> list[Order]:
        return self.side(SELL, **kwargs)

    def buys(self, **kwargs: Any) -> list[Order]:
        return self.side(BUY, **kwargs)

    def best_sell(self, **kwargs: Any) -> Order | None:
        found = self.sells(**kwargs)
        return found[0] if found else None

    def best_buy(self, **kwargs: Any) -> Order | None:
        found = self.buys(**kwargs)
        return found[0] if found else None

    def variants(self) -> list[tuple[int | None, str | None]]:
        """Distinct (mod_rank, subtype) combinations present in the book."""
        seen: list[tuple[int | None, str | None]] = []
        for order in self.orders:
            key = (order.mod_rank, order.subtype)
            if key not in seen:
                seen.append(key)
        return seen


@dataclass(frozen=True)
class StatPoint:
    """One bucket from the statistics endpoint."""

    datetime: datetime | None
    volume: float
    min_price: float
    max_price: float
    avg_price: float
    wa_price: float
    median: float
    moving_avg: float | None = None
    order_type: str | None = None
    mod_rank: int | None = None
    subtype: str | None = None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "StatPoint":
        def number(key: str, fallback: float = 0.0) -> float:
            value = raw.get(key)
            try:
                return float(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return fallback

        median = number("median")
        return cls(
            datetime=parse_dt(raw.get("datetime")),
            volume=number("volume"),
            min_price=number("min_price"),
            max_price=number("max_price"),
            avg_price=number("avg_price", median),
            wa_price=number("wa_price", median),
            median=median,
            moving_avg=number("moving_avg") if raw.get("moving_avg") is not None else None,
            order_type=raw.get("order_type"),
            mod_rank=raw.get("mod_rank"),
            subtype=raw.get("subtype"),
        )


@dataclass
class ItemStats:
    """Closed-trade history for one item."""

    item_url: str
    hourly: list[StatPoint] = field(default_factory=list)  # 48 hour series
    daily: list[StatPoint] = field(default_factory=list)  # 90 day series

    @classmethod
    def from_api(cls, item_url: str, payload: dict[str, Any]) -> "ItemStats":
        closed = (payload.get("payload") or {}).get("statistics_closed") or {}
        hourly = [StatPoint.from_api(entry) for entry in closed.get("48hours") or []]
        daily = [StatPoint.from_api(entry) for entry in closed.get("90days") or []]
        return cls(item_url=item_url, hourly=hourly, daily=daily)

    def points(
        self,
        *,
        window: str = "48hours",
        order_type: str | None = SELL,
        mod_rank: int | None = None,
        subtype: str | None = None,
        days: float | None = None,
    ) -> list[StatPoint]:
        series = self.hourly if window == "48hours" else self.daily
        cutoff = now() - timedelta(days=days) if days else None
        selected = []
        for point in series:
            # order_type is absent on some payloads; treat those as sells, which
            # is what the closed-trade series historically recorded.
            if order_type and point.order_type and point.order_type != order_type:
                continue
            if mod_rank is not None and point.mod_rank is not None and point.mod_rank != mod_rank:
                continue
            if subtype is not None and point.subtype is not None and point.subtype != subtype:
                continue
            if cutoff and point.datetime and point.datetime < cutoff:
                continue
            selected.append(point)
        return selected

    def volume_per_day(self, **kwargs: Any) -> float:
        points = self.points(**kwargs)
        if not points:
            return 0.0
        total = sum(point.volume for point in points)
        stamps = [p.datetime for p in points if p.datetime]
        if len(stamps) >= 2:
            span_days = (max(stamps) - min(stamps)).total_seconds() / 86400.0
            if span_days >= 0.5:
                return total / span_days
        window = kwargs.get("window", "48hours")
        return total / (2.0 if window == "48hours" else 90.0)


def weighted_median(values: Sequence[float], weights: Sequence[float]) -> float | None:
    """Median that respects trade volume, so one quiet hour cannot set the price."""
    pairs = [(v, w) for v, w in zip(values, weights) if w > 0 and v > 0]
    if not pairs:
        clean = [v for v in values if v > 0]
        if not clean:
            return None
        clean.sort()
        return clean[len(clean) // 2]
    pairs.sort(key=lambda pair: pair[0])
    total = sum(weight for _, weight in pairs)
    seen = 0.0
    for value, weight in pairs:
        seen += weight
        if seen >= total / 2:
            return value
    return pairs[-1][0]


def median(values: Iterable[float]) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


@dataclass(frozen=True)
class Item:
    url_name: str
    name: str
    thumb: str = ""
    item_id: str = ""

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "Item":
        return cls(
            url_name=str(raw.get("url_name") or ""),
            name=str(raw.get("item_name") or raw.get("url_name") or ""),
            thumb=str(raw.get("thumb") or ""),
            item_id=str(raw.get("id") or ""),
        )
