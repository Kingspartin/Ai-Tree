"""Configuration loading: TOML file + environment overrides."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_NAMES = ("wfbot.toml", "config.toml")


def default_state_dir() -> Path:
    """Per-user writable directory for cache, database and tokens."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "wfbot"
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "wfbot"
    return Path.home() / ".local" / "share" / "wfbot"


def default_ee_log() -> Path | None:
    """Best-effort location of Warframe's EE.log for the current platform."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "Warframe" / "EE.log"
        return None
    # Proton / Wine layouts used by the Linux and Steam Deck community.
    candidates = [
        Path.home() / ".steam/steam/steamapps/compatdata/230410/pfx/drive_c/users/steamuser/AppData/Local/Warframe/EE.log",
        Path.home() / ".local/share/Steam/steamapps/compatdata/230410/pfx/drive_c/users/steamuser/AppData/Local/Warframe/EE.log",
        Path.home() / ".wine/drive_c/users" / os.environ.get("USER", "user") / "AppData/Local/Warframe/EE.log",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


@dataclass
class ApiConfig:
    base_url: str = "https://api.warframe.market/v1"
    platform: str = "pc"  # pc | ps4 | xbox | switch
    language: str = "en"
    requests_per_second: float = 2.5  # warframe.market asks for <= 3/s
    max_workers: int = 3
    timeout: float = 20.0
    max_retries: int = 4
    orders_cache_ttl: int = 180  # seconds; the order book moves fast
    statistics_cache_ttl: int = 21600  # 6h; price history barely moves
    items_cache_ttl: int = 604800  # 7 days; the item list is near-static


@dataclass
class ScanConfig:
    budget: int = 500  # platinum you are willing to tie up
    min_margin: float = 0.25  # 25% over the buy price
    min_profit: int = 10  # absolute platinum per unit
    min_volume: float = 6.0  # trades per day over the last 48h
    max_price: int = 0  # 0 = no cap; otherwise skip items dearer than this
    min_book_depth: int = 3  # competing sell orders needed for a confident exit
    candidate_limit: int = 250  # items promoted from stage 1 to the order-book pass
    include_patterns: list[str] = field(default_factory=lambda: ["*"])
    exclude_patterns: list[str] = field(
        # Rivens are priced per roll, Kuva/Tenet weapons carry a bonus percentage,
        # and relic/set naming makes their books non-comparable. Statistical
        # pricing does not apply to any of them.
        default_factory=lambda: ["*riven*", "*kuva_*", "*tenet_*", "*_relic", "*veiled*"]
    )
    stale_order_days: float = 3.0  # listings older than this are treated as unreliable


@dataclass
class TradeConfig:
    live: bool = False  # must be true AND --live passed before anything mutates
    ingame_name: str = ""
    undercut_by: int = 1  # platinum below the best competing sell
    outbid_by: int = 1  # platinum above the best competing buy
    min_change: int = 1  # skip repricing when the delta is smaller than this
    max_updates_per_cycle: int = 25
    min_seconds_between_updates: int = 900  # per order, avoids price-war thrash
    sell_floor_ratio: float = 0.60  # never sell under 60% of fair value
    buy_ceiling_ratio: float = 0.75  # never bid over 75% of fair value
    max_plat_in_buy_orders: int = 0  # 0 = unlimited
    hide_orders_when_offline: bool = False  # needs logwatch to know game state


@dataclass
class NotifyConfig:
    desktop: bool = True
    console: bool = True
    clipboard: bool = True
    min_score: float = 0.0  # suppress notifications below this opportunity score
    cooldown_seconds: int = 1800  # per item, so a watch loop cannot spam you


@dataclass
class LogWatchConfig:
    enabled: bool = False
    path: str = ""  # empty = auto-detect
    poll_interval: float = 1.0
    encoding: str = "utf-8"
    # EE.log markers change between game updates, so these are configuration
    # rather than constants. Add your own after grepping your own log.
    whisper_patterns: list[str] = field(
        default_factory=lambda: [
            r"Dialog\.lua.*?(?P<user>\S+)\s+wants to trade",
            r"whisper from (?P<user>\S+)",
        ]
    )
    trade_patterns: list[str] = field(
        default_factory=lambda: [
            r"Script \[Info\]: Trading\.lua.*",
            r"Sys \[Info\]: Set the trade",
        ]
    )
    game_start_patterns: list[str] = field(
        default_factory=lambda: [r"Sys \[Diag\]: Current time:", r"Main game loop"]
    )
    game_stop_patterns: list[str] = field(
        default_factory=lambda: [r"Game/Client shutdown", r"Sys \[Info\]: Shutdown"]
    )


@dataclass
class Config:
    api: ApiConfig = field(default_factory=ApiConfig)
    scan: ScanConfig = field(default_factory=ScanConfig)
    trade: TradeConfig = field(default_factory=TradeConfig)
    notify: NotifyConfig = field(default_factory=NotifyConfig)
    logwatch: LogWatchConfig = field(default_factory=LogWatchConfig)
    state_dir: Path = field(default_factory=default_state_dir)

    # Filled in by load(); useful in error messages.
    source_path: Path | None = None

    @property
    def cache_dir(self) -> Path:
        return self.state_dir / "cache"

    @property
    def db_path(self) -> Path:
        return self.state_dir / "wfbot.sqlite3"

    @property
    def token_path(self) -> Path:
        return self.state_dir / "token.json"

    @property
    def audit_path(self) -> Path:
        return self.state_dir / "actions.jsonl"


_SCALARS: dict[str, Any] = {"int": int, "float": float, "str": str, "bool": bool}


def _coerce(annotation: Any, value: Any) -> Any:
    # `from __future__ import annotations` makes dataclass field types strings,
    # so match on the name rather than the type object.
    name = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
    if name == "Path":
        return Path(str(value)).expanduser()
    if name == "float" and isinstance(value, int):
        return float(value)
    if name in _SCALARS and isinstance(value, (int, float, str, bool)):
        return _SCALARS[name](value)
    return value


def _apply(section: Any, values: dict[str, Any], where: str) -> None:
    known = {f.name: f for f in fields(section)}
    for key, value in values.items():
        if key not in known:
            raise ValueError(f"unknown option '{where}.{key}'")
        setattr(section, key, _coerce(known[key].type, value))


def find_config(explicit: str | os.PathLike[str] | None = None) -> Path | None:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"config file not found: {path}")
        return path
    env = os.environ.get("WFBOT_CONFIG")
    if env:
        return Path(env).expanduser()
    for directory in (Path.cwd(), default_state_dir(), Path.home() / ".config" / "wfbot"):
        for name in DEFAULT_CONFIG_NAMES:
            candidate = directory / name
            if candidate.exists():
                return candidate
    return None


def load(explicit: str | os.PathLike[str] | None = None) -> Config:
    """Load configuration from TOML, then apply environment overrides."""
    config = Config()
    path = find_config(explicit)
    if path and path.exists():
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
        config.source_path = path
        for key, value in data.items():
            if key == "state_dir":
                config.state_dir = Path(str(value)).expanduser()
                continue
            section = getattr(config, key, None)
            if section is None or not is_dataclass(section):
                raise ValueError(f"unknown config section '[{key}]' in {path}")
            if not isinstance(value, dict):
                raise ValueError(f"'[{key}]' must be a table in {path}")
            _apply(section, value, key)

    # Environment always wins, so scripts and CI can override a checked-in file.
    if os.environ.get("WFBOT_PLATFORM"):
        config.api.platform = os.environ["WFBOT_PLATFORM"]
    if os.environ.get("WFBOT_STATE_DIR"):
        config.state_dir = Path(os.environ["WFBOT_STATE_DIR"]).expanduser()
    if os.environ.get("WFM_INGAME_NAME"):
        config.trade.ingame_name = os.environ["WFM_INGAME_NAME"]

    config.state_dir.mkdir(parents=True, exist_ok=True)
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    return config
