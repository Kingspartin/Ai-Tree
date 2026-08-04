"""Core value types shared across igwatch."""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Optional


class Availability(enum.Enum):
    """Outcome of a single availability check."""

    AVAILABLE = "available"
    TAKEN = "taken"
    #: The check completed but the answer could not be trusted (login wall,
    #: unexpected payload, network error).
    UNKNOWN = "unknown"
    #: Instagram is throttling us. Same as UNKNOWN for decision making, but it
    #: earns a longer backoff.
    RATE_LIMITED = "rate_limited"

    @property
    def is_conclusive(self) -> bool:
        return self in (Availability.AVAILABLE, Availability.TAKEN)


@dataclass(frozen=True)
class CheckResult:
    """What one strategy learned about one username."""

    username: str
    status: Availability
    strategy: str
    http_status: Optional[int] = None
    detail: str = ""
    checked_at: float = field(default_factory=time.time)

    @property
    def profile_url(self) -> str:
        return f"https://www.instagram.com/{self.username}/"

    def __str__(self) -> str:
        bits = [f"@{self.username}", self.status.value, f"via {self.strategy}"]
        if self.http_status is not None:
            bits.append(f"HTTP {self.http_status}")
        if self.detail:
            bits.append(self.detail)
        return " | ".join(bits)
