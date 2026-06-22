"""
Legacy Price Reader — Adapter around EventPriceBackfill for macro use.

Wraps the existing ``EventPriceBackfill`` (or equivalent legacy module)
so that the macro-scheduled strategy can query historical prices for
BTC and ETH without depending on the full legacy interface.

All public methods return plain Python types suitable for downstream
consumption by the hypothesis / assessment pipeline.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional, Protocol


# ---------------------------------------------------------------------------
# Protocol for the legacy price backfill dependency
# ---------------------------------------------------------------------------
class EventPriceBackfillProtocol(Protocol):
    """Minimal interface expected from the legacy EventPriceBackfill."""

    def get_price(self, asset: str, timestamp: datetime) -> Decimal:
        ...

    def get_price_window(
        self,
        asset: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        ...


# ---------------------------------------------------------------------------
# Concrete adapter
# ---------------------------------------------------------------------------
class LegacyPriceReader:
    """Adapter that wraps an EventPriceBackfill-like object for macro use.

    Provides convenience methods to obtain BTC / ETH prices at a point
    in time or return series over a window.  In tests / replay scenarios
    a synthetic backfill can be injected.

    Args:
        backfill: An object conforming to ``EventPriceBackfillProtocol``.
            If ``None``, the reader operates in stub mode (returns zeros).
    """

    # Supported assets
    ASSETS = ("BTC", "ETH")

    def __init__(
        self,
        backfill: Optional[EventPriceBackfillProtocol] = None,
    ) -> None:
        self._backfill = backfill

    # ------------------------------------------------------------------
    # Point-in-time price
    # ------------------------------------------------------------------
    def get_btc_price_at(
        self,
        timestamp: datetime,
        *,
        strict: bool = False,
    ) -> Decimal:
        """Return the BTC price as of *timestamp*.

        Args:
            timestamp: Point-in-time at which to fetch the price.
            strict: If True, raise if the backfill is not available.
        """
        return self._resolve_price("BTC", timestamp, strict=strict)

    def get_eth_price_at(
        self,
        timestamp: datetime,
        *,
        strict: bool = False,
    ) -> Decimal:
        """Return the ETH price as of *timestamp*."""
        return self._resolve_price("ETH", timestamp, strict=strict)

    # ------------------------------------------------------------------
    # Window returns
    # ------------------------------------------------------------------
    def get_window_returns(
        self,
        asset: str,
        start: datetime,
        end: datetime,
        *,
        strict: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch a price series over ``[start, end)``.

        Each entry in the returned list::

            {"timestamp": datetime, "price": Decimal, "asset": str}

        Args:
            asset:  Asset symbol, e.g. "BTC" or "ETH".
            start:  Window start (inclusive).
            end:    Window end (exclusive).
            strict: If True, raise when backfill is unavailable.
        """
        if self._backfill is not None:
            raw = self._backfill.get_price_window(asset, start, end)
            return [
                {
                    "timestamp": r.get("timestamp", r.get("time", start)),
                    "price": r.get("price", r.get("close", Decimal("0"))),
                    "asset": asset,
                    "source": "legacy_backfill",
                }
                for r in raw
            ]

        if strict:
            raise RuntimeError(
                f"LegacyPriceReader: no backfill available for "
                f"{asset} window [{start} -> {end}]"
            )

        # Stub: return a single flat candle
        return [
            {
                "timestamp": start,
                "price": Decimal("0"),
                "asset": asset,
                "source": "stub",
            }
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_price(
        self,
        asset: str,
        timestamp: datetime,
        *,
        strict: bool,
    ) -> Decimal:
        if self._backfill is not None:
            return self._backfill.get_price(asset, timestamp)

        if strict:
            raise RuntimeError(
                f"LegacyPriceReader: no backfill available for "
                f"{asset} @ {timestamp}"
            )

        # Stub fallback — return zero price
        return Decimal("0")

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def get_asset_price_at(
        self,
        asset: str,
        timestamp: datetime,
        *,
        strict: bool = False,
    ) -> Decimal:
        """Generic dispatcher; delegates to asset-specific methods."""
        asset_upper = asset.upper()
        if asset_upper == "BTC":
            return self.get_btc_price_at(timestamp, strict=strict)
        if asset_upper == "ETH":
            return self.get_eth_price_at(timestamp, strict=strict)
        raise ValueError(f"Unsupported asset: {asset}")
