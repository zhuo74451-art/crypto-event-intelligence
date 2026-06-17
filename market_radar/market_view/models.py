"""Market view models — per-asset snapshot with full metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class Venue(str, Enum):
    BINANCE_SPOT = "binance_spot"
    HYPERLIQUID_PERP = "hyperliquid_perp"
    UNKNOWN = "unknown"


class Freshness(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass
class MarketHealth:
    """Health status for a single market data source."""
    venue: Venue
    asset: str
    status: str  # "ok" | "degraded" | "failed"
    message: str = ""


@dataclass
class MarketSnapshot:
    """Single asset market snapshot with full context.

    No network provider implementation — data is injected via fixtures.
    """
    symbol: str                         # BTC / ETH / SOL / HYPE
    price: float                        # USD
    change_1h_pct: Optional[float] = None
    change_24h_pct: Optional[float] = None
    volume_24h: Optional[float] = None  # USD
    open_interest: Optional[float] = None  # USD
    funding_rate: Optional[float] = None
    mark_price: Optional[float] = None
    oracle_price: Optional[float] = None
    venue: Venue = Venue.UNKNOWN
    observed_at: Optional[str] = None   # UTC ISO 8601
    freshness: Freshness = Freshness.UNKNOWN

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "change_1h_pct": self.change_1h_pct,
            "change_24h_pct": self.change_24h_pct,
            "volume_24h": self.volume_24h,
            "open_interest": self.open_interest,
            "funding_rate": self.funding_rate,
            "mark_price": self.mark_price,
            "oracle_price": self.oracle_price,
            "venue": self.venue.value,
            "observed_at": self.observed_at,
            "freshness": self.freshness.value,
        }
