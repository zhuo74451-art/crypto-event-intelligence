"""
Point-in-Time Snapshot — Immutable market state at a specific timestamp.

The ``PointInTimeSnapshot`` freezes all observable market data (prices,
open interest, funding rate, volume) as they existed at an exact moment
in time.  This guarantees that replays and backtests never leak future
information into the decision pipeline.

Snapshots are immutable once created and can be safely cached or
serialised for debugging / audit trails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from ..adapters.legacy_market_reader import LegacyMarketReader
from ..adapters.legacy_price_reader import LegacyPriceReader


# ---------------------------------------------------------------------------
# Snapshot class
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PointInTimeSnapshot:
    """Immutable market state as of a specific moment.

    Attributes:
        timestamp:      The exact UTC time this snapshot represents.
        btc_price:      BTC price in USDT (Decimal).
        eth_price:      ETH price in USDT (Decimal).
        open_interest:  Open interest for BTCUSDT (Decimal).
        funding_rate:   Funding rate for BTCUSDT (Decimal).
        spot_volume:    Cumulative spot volume for BTCUSDT (Decimal).
        extra:          Optional extra fields captured ad-hoc.
    """

    timestamp: datetime
    btc_price: Decimal = Decimal("0")
    eth_price: Decimal = Decimal("0")
    open_interest: Decimal = Decimal("0")
    funding_rate: Decimal = Decimal("0")
    spot_volume: Decimal = Decimal("0")
    extra: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def capture(
        cls,
        at: datetime,
        prices: LegacyPriceReader,
        market: LegacyMarketReader,
        *,
        symbol: str = "BTCUSDT",
    ) -> "PointInTimeSnapshot":
        """Produce a snapshot by querying the provided readers.

        All reads are performed at the single moment *at*.  Because the
        readers may have internal latency, the snapshot records the
        logical *at* time, *not* the system-clock time of each read.

        Args:
            at:      The logical timestamp for the snapshot.
            prices:  Price adapter (BTC / ETH).
            market:  Market-data adapter (OI, funding rate, volume).
            symbol:  Trading pair for market data (default BTCUSDT).

        Returns:
            A fully populated ``PointInTimeSnapshot``.
        """
        # Normalise to UTC-aware datetime
        ts = at if at.tzinfo else at.replace(tzinfo=timezone.utc)

        btc_price = prices.get_btc_price_at(ts)
        eth_price = prices.get_eth_price_at(ts)

        oi = market.get_open_interest(symbol, ts)
        fr = market.get_funding_rate(symbol, ts)
        vol = market.get_spot_volume(
            symbol,
            start=ts,
            end=ts,  # approximate instantaneous volume
        )

        return cls(
            timestamp=ts,
            btc_price=btc_price,
            eth_price=eth_price,
            open_interest=oi,
            funding_rate=fr,
            spot_volume=vol,
        )

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------
    def btc_usd(self) -> Decimal:
        """Alias for ``btc_price``."""
        return self.btc_price

    def eth_usd(self) -> Decimal:
        """Alias for ``eth_price``."""
        return self.eth_price

    def as_dict(self) -> dict[str, Any]:
        """Return a plain dict representation (JSON-safe)."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "btc_price": float(self.btc_price),
            "eth_price": float(self.eth_price),
            "open_interest": float(self.open_interest),
            "funding_rate": float(self.funding_rate),
            "spot_volume": float(self.spot_volume),
            "extra": self.extra,
        }

    # ------------------------------------------------------------------
    # Point-in-time guard
    # ------------------------------------------------------------------
    def assert_before(self, dt: datetime) -> None:
        """Assert that this snapshot is strictly before *dt*.

        Useful in regression tests to confirm no future leakage.
        """
        if self.timestamp >= dt:
            raise RuntimeError(
                f"PointInTimeSnapshot @ {self.timestamp} is not before {dt}"
            )

    def assert_after(self, dt: datetime) -> None:
        """Assert that this snapshot is strictly after *dt*."""
        if self.timestamp <= dt:
            raise RuntimeError(
                f"PointInTimeSnapshot @ {self.timestamp} is not after {dt}"
            )
