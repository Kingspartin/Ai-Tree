"""Automatic management of your own warframe.market listings.

This is the part that genuinely runs unattended: it keeps your sell orders just
under the cheapest live competitor and your buy orders just over the richest
one, inside floors and ceilings derived from fair value.

Nothing here touches the game. Platinum still changes hands in-game, in person.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Sequence

from .analysis import PriceDecision, Valuation, evaluate, suggest_price
from .api import AuthError, WarframeMarketClient, WFMError
from .config import Config
from .models import BUY, SELL, ItemStats, OrderBook
from .storage import Database

log = logging.getLogger(__name__)


@dataclass
class MyOrder:
    """One of your own listings, as returned by the profile endpoint."""

    id: str
    item_url: str
    item_name: str
    item_id: str
    order_type: str
    platinum: int
    quantity: int
    visible: bool = True
    mod_rank: int | None = None
    subtype: str | None = None

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> "MyOrder":
        item = raw.get("item") or {}
        english = item.get("en") or {}
        return cls(
            id=str(raw.get("id", "")),
            item_url=str(item.get("url_name") or ""),
            item_name=str(english.get("item_name") or item.get("url_name") or ""),
            item_id=str(item.get("id") or ""),
            order_type=str(raw.get("order_type") or ""),
            platinum=int(raw.get("platinum") or 0),
            quantity=int(raw.get("quantity") or 0),
            visible=bool(raw.get("visible", True)),
            mod_rank=raw.get("mod_rank"),
            subtype=raw.get("subtype"),
        )


@dataclass
class ApplyResult:
    decision: PriceDecision
    ok: bool
    detail: str = ""


@dataclass
class Plan:
    decisions: list[PriceDecision] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (order description, why)
    valuations: dict[str, Valuation] = field(default_factory=dict)

    @property
    def changes(self) -> list[PriceDecision]:
        return [decision for decision in self.decisions if decision.changed]


class Trader:
    def __init__(
        self, client: WarframeMarketClient, config: Config, database: Database | None = None
    ) -> None:
        self.client = client
        self.config = config
        self.db = database

    # ------------------------------------------------------------------ reading

    @property
    def ingame_name(self) -> str:
        name = self.config.trade.ingame_name or self.client.user_name or ""
        if not name:
            raise WFMError(
                "your in-game name is unknown - set trade.ingame_name in the config "
                "or sign in with 'wfbot login'"
            )
        return name

    def my_orders(self) -> list[MyOrder]:
        raw = self.client.user_orders(self.ingame_name)
        orders = [MyOrder.from_api(entry) for entry in raw]
        return [order for order in orders if order.item_url and order.order_type in (SELL, BUY)]

    def _market(self, item_urls: Sequence[str]) -> dict[str, tuple[OrderBook, ItemStats]]:
        def fetch(url: str) -> tuple[OrderBook, ItemStats]:
            return self.client.orders(url), self.client.statistics(url)

        market: dict[str, tuple[OrderBook, ItemStats]] = {}
        for url, payload, error in self.client.map(fetch, list(dict.fromkeys(item_urls))):
            if error or payload is None:
                log.warning("could not price %s: %s", url, error)
                continue
            market[url] = payload
        return market

    # ----------------------------------------------------------------- planning

    def plan(self, orders: Sequence[MyOrder] | None = None) -> Plan:
        """Work out what every one of your listings should cost. Never mutates."""
        trade = self.config.trade
        orders = list(orders if orders is not None else self.my_orders())
        plan = Plan()
        if not orders:
            return plan

        market = self._market([order.item_url for order in orders])
        committed = sum(
            order.platinum * order.quantity for order in orders if order.order_type == BUY
        )

        for order in orders:
            label = f"{order.item_name} ({order.order_type})"
            payload = market.get(order.item_url)
            if payload is None:
                plan.skipped.append((label, "market data unavailable"))
                continue
            book, stats = payload
            valuation = evaluate(
                order.item_url,
                order.item_name,
                book,
                stats,
                self.config.scan,
                mod_rank=order.mod_rank,
                subtype=order.subtype,
            )
            plan.valuations[order.id] = valuation

            target, reason = suggest_price(
                order.order_type, order.platinum, book, valuation, trade, me=self.ingame_name
            )
            decision = PriceDecision(
                order_id=order.id,
                item_url=order.item_url,
                item_name=order.item_name,
                order_type=order.order_type,
                current=order.platinum,
                target=int(target),
                quantity=order.quantity,
                reason=reason,
                mod_rank=order.mod_rank,
                subtype=order.subtype,
                visible=order.visible,
            )

            if not decision.changed:
                plan.decisions.append(decision)
                continue
            if abs(decision.delta) < trade.min_change:
                plan.skipped.append((label, f"delta {decision.delta:+}p below min_change"))
                continue
            if self.db:
                last = self.db.last_change(order.id)
                if last and time.time() - last < trade.min_seconds_between_updates:
                    wait = int(trade.min_seconds_between_updates - (time.time() - last))
                    plan.skipped.append((label, f"changed recently, {wait}s cooldown left"))
                    continue
            if order.order_type == BUY and trade.max_plat_in_buy_orders:
                projected = committed + decision.delta * order.quantity
                if projected > trade.max_plat_in_buy_orders:
                    plan.skipped.append(
                        (
                            label,
                            f"would commit {projected}p, over the "
                            f"{trade.max_plat_in_buy_orders}p buy-order cap",
                        )
                    )
                    continue
                committed = projected
            plan.decisions.append(decision)

        # Highest-impact changes first, so a truncated cycle still does the work
        # that matters most.
        plan.decisions.sort(key=lambda d: abs(d.delta) * d.quantity, reverse=True)
        if trade.max_updates_per_cycle:
            keep, drop = [], []
            changes = 0
            for decision in plan.decisions:
                if decision.changed and changes >= trade.max_updates_per_cycle:
                    drop.append(decision)
                    continue
                if decision.changed:
                    changes += 1
                keep.append(decision)
            plan.decisions = keep
            plan.skipped.extend(
                (f"{d.item_name} ({d.order_type})", "over max_updates_per_cycle") for d in drop
            )
        return plan

    # ---------------------------------------------------------------- executing

    def apply(self, plan: Plan, *, live: bool = False) -> list[ApplyResult]:
        """Push the planned prices. Without `live` this only writes the audit log."""
        results: list[ApplyResult] = []
        if live and not self.config.trade.live:
            raise WFMError(
                "refusing to trade live: set live = true under [trade] in your config "
                "as well as passing --live"
            )

        for decision in plan.changes:
            if not live:
                self._audit(decision, live=False, result="planned")
                results.append(ApplyResult(decision, True, "dry run"))
                continue
            try:
                self.client.update_order(
                    decision.order_id,
                    platinum=decision.target,
                    quantity=decision.quantity,
                    visible=decision.visible,
                    rank=decision.mod_rank,
                    subtype=decision.subtype,
                )
            except AuthError:
                self._audit(decision, live=True, result="auth-error")
                results.append(ApplyResult(decision, False, "authentication failed"))
                # Every remaining call would fail the same way.
                break
            except WFMError as exc:
                self._audit(decision, live=True, result="error", detail=str(exc))
                results.append(ApplyResult(decision, False, str(exc)))
                continue
            self._audit(decision, live=True, result="ok")
            results.append(ApplyResult(decision, True, "updated"))
        return results

    def _audit(
        self, decision: PriceDecision, *, live: bool, result: str, detail: str = ""
    ) -> None:
        if not self.db:
            return
        self.db.record_action(
            "reprice",
            live=live,
            order_id=decision.order_id,
            item=decision.item_url,
            order_type=decision.order_type,
            old_price=decision.current,
            new_price=decision.target,
            result=result,
            detail=detail or decision.reason,
        )

    def set_visibility(self, visible: bool, *, live: bool = False) -> int:
        """Hide or show every listing, e.g. while you are not in-game to trade."""
        changed = 0
        for order in self.my_orders():
            if order.visible == visible:
                continue
            if live:
                try:
                    self.client.update_order(
                        order.id,
                        platinum=order.platinum,
                        quantity=order.quantity,
                        visible=visible,
                        rank=order.mod_rank,
                        subtype=order.subtype,
                    )
                except WFMError as exc:
                    log.warning("could not update visibility for %s: %s", order.item_name, exc)
                    continue
            if self.db:
                self.db.record_action(
                    "visibility",
                    live=live,
                    order_id=order.id,
                    item=order.item_url,
                    order_type=order.order_type,
                    result="ok" if live else "planned",
                    detail=f"visible={visible}",
                )
            changed += 1
        return changed
