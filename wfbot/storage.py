"""SQLite history and a tamper-evident audit trail of everything the bot does."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    item TEXT NOT NULL,
    mod_rank INTEGER,
    subtype TEXT,
    ask INTEGER,
    bid INTEGER,
    fair REAL,
    volume_per_day REAL,
    sellers INTEGER,
    buyers INTEGER
);
CREATE INDEX IF NOT EXISTS idx_snapshots_item_ts ON snapshots(item, ts);

CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    item TEXT NOT NULL,
    buy_at INTEGER,
    sell_at INTEGER,
    units INTEGER,
    profit INTEGER,
    confidence REAL,
    score REAL,
    payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_opportunities_ts ON opportunities(ts);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    action TEXT NOT NULL,
    order_id TEXT,
    item TEXT,
    order_type TEXT,
    old_price INTEGER,
    new_price INTEGER,
    live INTEGER NOT NULL DEFAULT 0,
    result TEXT,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_actions_order ON actions(order_id, ts);

CREATE TABLE IF NOT EXISTS universe (
    item TEXT PRIMARY KEY,
    name TEXT,
    liquidity REAL,
    price REAL,
    volume_per_day REAL,
    updated REAL
);

CREATE TABLE IF NOT EXISTS notifications (
    key TEXT PRIMARY KEY,
    ts REAL NOT NULL
);
"""


def _now() -> float:
    return time.time()


class Database:
    """Thin, thread-safe wrapper. One connection, one lock, no ORM."""

    def __init__(self, path: Path | str, audit_path: Path | str | None = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.audit_path = Path(audit_path) if audit_path else None
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self._lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def _write(self, sql: str, params: Iterable[Any] = ()) -> int:
        with self._lock:
            cursor = self.conn.execute(sql, tuple(params))
            self.conn.commit()
            return cursor.lastrowid or 0

    def _read(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self.conn.execute(sql, tuple(params)))

    # ------------------------------------------------------------- price history

    def record_snapshot(self, summary: dict[str, Any]) -> None:
        self._write(
            "INSERT INTO snapshots (ts,item,mod_rank,subtype,ask,bid,fair,volume_per_day,sellers,buyers)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                _now(),
                summary.get("item"),
                summary.get("rank"),
                summary.get("subtype"),
                summary.get("ask"),
                summary.get("bid"),
                summary.get("fair"),
                summary.get("volume_per_day"),
                summary.get("sellers"),
                summary.get("buyers"),
            ),
        )

    def price_history(self, item: str, days: float = 30.0) -> list[sqlite3.Row]:
        cutoff = _now() - days * 86400
        return self._read(
            "SELECT ts, ask, bid, fair FROM snapshots WHERE item=? AND ts>=? ORDER BY ts",
            (item, cutoff),
        )

    def lowest_seen(self, item: str, days: float = 30.0) -> int | None:
        cutoff = _now() - days * 86400
        rows = self._read(
            "SELECT MIN(ask) AS low FROM snapshots WHERE item=? AND ts>=? AND ask IS NOT NULL",
            (item, cutoff),
        )
        return rows[0]["low"] if rows and rows[0]["low"] is not None else None

    # -------------------------------------------------------------- opportunities

    def record_opportunity(self, opportunity: Any) -> None:
        payload = asdict(opportunity) if hasattr(opportunity, "__dataclass_fields__") else dict(opportunity)
        self._write(
            "INSERT INTO opportunities (ts,kind,item,buy_at,sell_at,units,profit,confidence,score,payload)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                _now(),
                payload.get("kind"),
                payload.get("item_url"),
                payload.get("buy_at"),
                payload.get("sell_at"),
                payload.get("units"),
                getattr(opportunity, "profit", None),
                payload.get("confidence"),
                getattr(opportunity, "score", None),
                json.dumps(payload, default=str),
            ),
        )

    # --------------------------------------------------------------------- audit

    def record_action(
        self,
        action: str,
        *,
        live: bool,
        order_id: str | None = None,
        item: str | None = None,
        order_type: str | None = None,
        old_price: int | None = None,
        new_price: int | None = None,
        result: str = "planned",
        detail: str = "",
    ) -> None:
        """Log every mutation, planned or executed. This is the paper trail."""
        self._write(
            "INSERT INTO actions (ts,action,order_id,item,order_type,old_price,new_price,live,result,detail)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                _now(),
                action,
                order_id,
                item,
                order_type,
                old_price,
                new_price,
                1 if live else 0,
                result,
                detail,
            ),
        )
        if self.audit_path:
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "order_id": order_id,
                "item": item,
                "order_type": order_type,
                "old_price": old_price,
                "new_price": new_price,
                "live": live,
                "result": result,
                "detail": detail,
            }
            try:
                self.audit_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.audit_path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry) + "\n")
            except OSError:
                pass

    def last_change(self, order_id: str) -> float | None:
        rows = self._read(
            "SELECT MAX(ts) AS ts FROM actions WHERE order_id=? AND live=1 AND result='ok'",
            (order_id,),
        )
        return rows[0]["ts"] if rows and rows[0]["ts"] is not None else None

    def recent_actions(self, limit: int = 20) -> list[sqlite3.Row]:
        return self._read("SELECT * FROM actions ORDER BY ts DESC LIMIT ?", (limit,))

    # ------------------------------------------------------------------ universe

    def save_universe(self, rows: Iterable[dict[str, Any]]) -> None:
        stamp = _now()
        with self._lock:
            self.conn.executemany(
                "INSERT INTO universe (item,name,liquidity,price,volume_per_day,updated)"
                " VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(item) DO UPDATE SET name=excluded.name, liquidity=excluded.liquidity,"
                " price=excluded.price, volume_per_day=excluded.volume_per_day, updated=excluded.updated",
                [
                    (
                        row["item"],
                        row.get("name"),
                        row.get("liquidity", 0.0),
                        row.get("price"),
                        row.get("volume_per_day"),
                        stamp,
                    )
                    for row in rows
                ],
            )
            self.conn.commit()

    def top_universe(self, limit: int, max_age_hours: float = 168.0) -> list[sqlite3.Row]:
        cutoff = _now() - max_age_hours * 3600
        return self._read(
            "SELECT * FROM universe WHERE updated>=? ORDER BY liquidity DESC LIMIT ?",
            (cutoff, limit),
        )

    # ------------------------------------------------------------- notifications

    def should_notify(self, key: str, cooldown: float) -> bool:
        """True at most once per cooldown window for a given key."""
        rows = self._read("SELECT ts FROM notifications WHERE key=?", (key,))
        if rows and _now() - rows[0]["ts"] < cooldown:
            return False
        self._write(
            "INSERT INTO notifications (key,ts) VALUES (?,?)"
            " ON CONFLICT(key) DO UPDATE SET ts=excluded.ts",
            (key, _now()),
        )
        return True
