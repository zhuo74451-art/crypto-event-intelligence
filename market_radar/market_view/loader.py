"""Market view loader — loads from injected fixture data, no network calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .models import MarketSnapshot, MarketHealth, Venue, Freshness


@dataclass
class MarketViewResult:
    snapshots: list[MarketSnapshot] = field(default_factory=list)
    health: list[MarketHealth] = field(default_factory=list)
    live_sources: int = 0
    degraded_sources: int = 0

    def as_dict(self) -> dict:
        return {
            "snapshot_count": len(self.snapshots),
            "snapshots": [s.as_dict() for s in self.snapshots],
            "health": [{"venue": h.venue.value, "asset": h.asset, "status": h.status,
                         "message": h.message} for h in self.health],
            "live_sources": self.live_sources,
            "degraded_sources": self.degraded_sources,
        }


FIXTURE_SNAPSHOTS: list[dict] = [
    {
        "symbol": "BTC",
        "price": 65720.00,
        "change_1h_pct": -0.15,
        "change_24h_pct": -1.03,
        "volume_24h": 28_500_000_000.0,
        "open_interest": 12_000_000_000.0,
        "funding_rate": 0.000105,
        "mark_price": 65720.00,
        "oracle_price": 65718.50,
        "venue": "binance_spot",
        "observed_at": "2026-06-17T10:00:00Z",
        "freshness": "fresh",
    },
    {
        "symbol": "ETH",
        "price": 1789.64,
        "change_1h_pct": -0.08,
        "change_24h_pct": -0.36,
        "volume_24h": 12_000_000_000.0,
        "open_interest": 5_000_000_000.0,
        "funding_rate": 0.000052,
        "mark_price": 1789.64,
        "oracle_price": 1788.90,
        "venue": "binance_spot",
        "observed_at": "2026-06-17T10:00:00Z",
        "freshness": "fresh",
    },
    {
        "symbol": "SOL",
        "price": 73.58,
        "change_1h_pct": 0.22,
        "change_24h_pct": -0.84,
        "volume_24h": 3_500_000_000.0,
        "open_interest": 1_200_000_000.0,
        "funding_rate": -0.000020,
        "mark_price": 73.58,
        "oracle_price": 73.55,
        "venue": "binance_spot",
        "observed_at": "2026-06-17T10:00:00Z",
        "freshness": "fresh",
    },
    {
        "symbol": "HYPE",
        "price": 74.05,
        "change_1h_pct": 1.52,
        "change_24h_pct": 9.78,
        "volume_24h": 850_000_000.0,
        "open_interest": 1_490_000_000.0,
        "funding_rate": 0.0000125,
        "mark_price": 74.05,
        "oracle_price": 74.01,
        "venue": "hyperliquid_perp",
        "observed_at": "2026-06-17T10:00:00Z",
        "freshness": "fresh",
    },
]


def _make_snapshot(raw: dict) -> MarketSnapshot:
    venue_str = raw.get("venue", "unknown")
    venue = Venue.BINANCE_SPOT if venue_str == "binance_spot" else \
            Venue.HYPERLIQUID_PERP if venue_str == "hyperliquid_perp" else Venue.UNKNOWN
    freshness_str = raw.get("freshness", "unknown")
    freshe = Freshness.FRESH if freshness_str == "fresh" else \
             Freshness.STALE if freshness_str == "stale" else Freshness.UNKNOWN
    return MarketSnapshot(
        symbol=raw["symbol"],
        price=raw["price"],
        change_1h_pct=raw.get("change_1h_pct"),
        change_24h_pct=raw.get("change_24h_pct"),
        volume_24h=raw.get("volume_24h"),
        open_interest=raw.get("open_interest"),
        funding_rate=raw.get("funding_rate"),
        mark_price=raw.get("mark_price"),
        oracle_price=raw.get("oracle_price"),
        venue=venue,
        observed_at=raw.get("observed_at"),
        freshness=freshe,
    )


def load_market_view() -> MarketViewResult:
    """Load market snapshots from fixture data. No network calls."""
    snapshots = [_make_snapshot(raw) for raw in FIXTURE_SNAPSHOTS]
    health = []

    for snap in snapshots:
        h = MarketHealth(venue=snap.venue, asset=snap.symbol, status="ok")
        # Simulate degraded if stale or missing price
        if snap.price <= 0:
            h.status = "degraded"
            h.message = "Price is zero or negative"
        health.append(h)

    live = sum(1 for h in health if h.status == "ok")
    degraded = sum(1 for h in health if h.status != "ok")

    return MarketViewResult(
        snapshots=snapshots,
        health=health,
        live_sources=live,
        degraded_sources=degraded,
    )
