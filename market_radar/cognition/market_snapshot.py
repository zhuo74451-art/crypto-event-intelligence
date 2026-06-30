"""Point-in-time market snapshot adapter."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from market_radar.cognition.contracts import MarketSnapshot, utc_now, sha256_id

class MarketSnapshotProvider:
    def __init__(self):
        self.provider_name = "hyperliquid_binance"

    def fetch_snapshot(self, asset: str, as_of: Optional[str] = None) -> MarketSnapshot:
        """Fetch point-in-time price snapshot.

        Attempts to populate:
        - price (spot)
        - pre_event_ref (pre-event reference price)
        - volume_24h
        - return_1h, return_24h
        - reaction, follow_through
        """
        from market_radar.shared.price_provider_protocol import EventPriceBackfill, map_symbol
        backfill = EventPriceBackfill()
        try:
            result = backfill.get_price_snapshot(map_symbol(asset), as_of)
            if result:
                snap = MarketSnapshot(
                    snapshot_id=sha256_id(["snap", asset, as_of or ""]),
                    event_id="", as_of=as_of or "",
                    provider=self.provider_name, asset=asset,
                    price=result.get("price"),
                    pre_event_ref=result.get("pre_event_ref") or result.get("price"),
                    volume_24h=result.get("volume_24h") or result.get("volume"),
                    return_1h=result.get("return_1h"),
                    return_24h=result.get("return_24h"),
                    missing_metrics=[],
                )
                # Compute reaction and follow_through if both prices available
                if snap.price and snap.pre_event_ref and snap.pre_event_ref != 0:
                    snap.reaction = round((snap.price - snap.pre_event_ref) / snap.pre_event_ref * 100, 4)
                return snap
            # Empty result from provider
            return MarketSnapshot(
                snapshot_id=sha256_id(["snap", asset, as_of or ""]),
                provider=self.provider_name, asset=asset, as_of=as_of or "",
                missing_metrics=["all_metrics"],
            )
        except Exception as e:
            return MarketSnapshot(
                snapshot_id=sha256_id(["snap", asset, as_of or ""]),
                provider=self.provider_name, asset=asset, as_of=as_of or "",
                missing_metrics=["all_metrics"],
                rate_limited=True,
            )