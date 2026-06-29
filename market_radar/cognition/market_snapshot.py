"""Point-in-time market snapshot adapter."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from market_radar.cognition.contracts import MarketSnapshot, utc_now, sha256_id

class MarketSnapshotProvider:
    def __init__(self):
        self.provider_name = "hyperliquid_binance"
    
    def fetch_snapshot(self, asset: str, as_of: str) -> MarketSnapshot:
        """Fetch point-in-time price snapshot."""
        from market_radar.shared.price_provider_protocol import EventPriceBackfill, map_symbol
        backfill = EventPriceBackfill()
        try:
            result = backfill.get_price_snapshot(map_symbol(asset), as_of)
            snap = MarketSnapshot(
                snapshot_id=sha256_id(["snap", asset, as_of]),
                event_id="", as_of=as_of,
                provider=self.provider_name, asset=asset,
                price=result.get("price") if result else None,
                missing_metrics=[] if result else ["all_metrics"],
            )
            return snap
        except Exception as e:
            return MarketSnapshot(
                snapshot_id=sha256_id(["snap", asset, as_of]),
                provider=self.provider_name, asset=asset, as_of=as_of,
                missing_metrics=["all_metrics"],
            )
