"""
Legacy Market Reader — Adapter for existing market data readers.

Wraps legacy market-data components (order-book snapshots, funding-rate
feeds, volume trackers) under a unified interface that the macro-scheduled
strategy can consume.  In stub mode the adapter returns synthetic values.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Protocol


# ---------------------------------------------------------------------------
# Protocols for legacy dependencies
# ---------------------------------------------------------------------------
class OpenInterestProvider(Protocol):
    def get_open_interest(self, symbol: str, timestamp: datetime) -> Decimal:
        ...


class FundingRateProvider(Protocol):
    def get_funding_rate(self, symbol: str, timestamp: datetime) -> Decimal:
        ...


class SpotVolumeProvider(Protocol):
    def get_spot_volume(
        self, symbol: str, start: datetime, end: datetime
    ) -> Decimal:
        ...


# ---------------------------------------------------------------------------
# Concrete adapter
# ---------------------------------------------------------------------------
class LegacyMarketReader:
    """Adapter wrapping legacy market-data readers for macro use.

    Each method first attempts to delegate to the injected legacy
    provider.  If the provider is ``None`` (or the method is called
    in stub mode), synthetic fallback values are returned.

    Args:
        oi_provider:   Legacy open-interest provider.
        fr_provider:   Legacy funding-rate provider.
        vol_provider:  Legacy spot-volume provider.
    """

    # Default synthetic values
    _STUB_OI: Decimal = Decimal("1_250_000_000")   # ~$1.25B
    _STUB_FR: Decimal = Decimal("0.00012")          # 0.12 bps
    _STUB_VOL: Decimal = Decimal("850_000_000")     # ~$850M

    def __init__(
        self,
        oi_provider: Optional[OpenInterestProvider] = None,
        fr_provider: Optional[FundingRateProvider] = None,
        vol_provider: Optional[SpotVolumeProvider] = None,
    ) -> None:
        self._oi = oi_provider
        self._fr = fr_provider
        self._vol = vol_provider

    # ------------------------------------------------------------------
    # Open interest
    # ------------------------------------------------------------------
    def get_open_interest(
        self,
        symbol: str,
        timestamp: Optional[datetime] = None,
        *,
        strict: bool = False,
    ) -> Decimal:
        """Fetch open interest for *symbol* as of *timestamp*.

        Args:
            symbol:    Trading pair, e.g. "BTCUSDT".
            timestamp: Point-in-time (default: now UTC).
            strict:    Raise if the provider is unavailable.

        Returns:
            Open interest as a Decimal (in quote-currency units).
        """
        ts = timestamp or datetime.utcnow()

        if self._oi is not None:
            return self._oi.get_open_interest(symbol, ts)

        if strict:
            raise RuntimeError(
                f"LegacyMarketReader: no OI provider for {symbol}"
            )

        return self._STUB_OI

    # ------------------------------------------------------------------
    # Funding rate
    # ------------------------------------------------------------------
    def get_funding_rate(
        self,
        symbol: str,
        timestamp: Optional[datetime] = None,
        *,
        strict: bool = False,
    ) -> Decimal:
        """Fetch the 8-hour funding rate for *symbol* at *timestamp*.

        Args:
            symbol:    Trading pair, e.g. "BTCUSDT".
            timestamp: Point-in-time.
            strict:    Raise if the provider is unavailable.

        Returns:
            Funding rate as a Decimal (e.g. 0.0001 = 1 bp).
        """
        ts = timestamp or datetime.utcnow()

        if self._fr is not None:
            return self._fr.get_funding_rate(symbol, ts)

        if strict:
            raise RuntimeError(
                f"LegacyMarketReader: no FR provider for {symbol}"
            )

        return self._STUB_FR

    # ------------------------------------------------------------------
    # Spot volume
    # ------------------------------------------------------------------
    def get_spot_volume(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        *,
        strict: bool = False,
    ) -> Decimal:
        """Fetch cumulative spot volume for *symbol* over a window.

        Args:
            symbol: Trading pair, e.g. "BTCUSDT".
            start:  Window start (default: 1 hour ago).
            end:    Window end (default: now UTC).
            strict: Raise if the provider is unavailable.

        Returns:
            Cumulative volume (in quote-currency units).
        """
        now = datetime.utcnow()
        start = start or (now.replace(microsecond=0) - __import__(
            "datetime"
        ).timedelta(hours=1))
        end = end or now

        if self._vol is not None:
            return self._vol.get_spot_volume(symbol, start, end)

        if strict:
            raise RuntimeError(
                f"LegacyMarketReader: no volume provider for {symbol}"
            )

        return self._STUB_VOL

    # ------------------------------------------------------------------
    # Batch convenience
    # ------------------------------------------------------------------
    def get_market_snapshot(
        self,
        symbol: str,
        timestamp: Optional[datetime] = None,
    ) -> dict[str, Decimal]:
        """Return a dict containing OI, funding rate, and volume at once."""
        ts = timestamp or datetime.utcnow()
        return {
            "open_interest": self.get_open_interest(symbol, ts),
            "funding_rate": self.get_funding_rate(symbol, ts),
            "spot_volume": self.get_spot_volume(
                symbol, start=ts, end=ts  # approximate
            ),
        }
