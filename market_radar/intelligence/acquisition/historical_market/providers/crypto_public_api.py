"""Provider for crypto public REST API data (funding rates, OI, etc).

Uses Binance public futures API (no key required for public endpoints).
Endpoints used:
- GET /fapi/v1/fundingRate?symbol=BTCUSDT&startTime=X&endTime=Y&limit=1000
- GET /fapi/v1/openInterest?symbol=BTCUSDT
- GET /fapi/v1/ticker/bookTicker?symbol=BTCUSDT
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

from ..contracts import (
    DerivativeSnapshotV1,
    MarketBarV1,
    DataQuality,
    AssetClass,
    InstrumentType,
    Interval,
    make_snapshot_id,
)
from .base import BaseProvider, ProviderResult


BINANCE_FUTURES_BASE = "https://fapi.binance.com"

FUTURES_INSTRUMENTS = {
    "BTCUSDT": {
        "symbol": "BTCUSDT",
        "instrument_id": "binance_futures_btcusdt_perp",
        "canonical_name": "Binance BTC/USDT Perpetual",
        "venue": "binance",
        "asset_class": "crypto",
        "instrument_type": "perp_future",
        "currency": "USDT",
        "available_intervals": ["1h", "4h", "1d"],
    },
    "ETHUSDT": {
        "symbol": "ETHUSDT",
        "instrument_id": "binance_futures_ethusdt_perp",
        "canonical_name": "Binance ETH/USDT Perpetual",
        "venue": "binance",
        "asset_class": "crypto",
        "instrument_type": "perp_future",
        "currency": "USDT",
        "available_intervals": ["1h", "4h", "1d"],
    },
}


class CryptoPublicApiProvider(BaseProvider):
    """Fetches derivative data from Binance public futures API."""

    def __init__(self, cache_dir: str | Path, output_dir: str | Path):
        super().__init__(cache_dir, output_dir, "binance_public_api")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def list_instruments(self) -> list[dict[str, Any]]:
        return list(FUTURES_INSTRUMENTS.values())

    def fetch_derivative_snapshots(
        self,
        symbol: str,
        interval: str = "1h",
        start_date: str = "2019-01-01",
        end_date: str = "",
        force: bool = False,
    ) -> ProviderResult:
        """Fetch funding rate history from Binance."""
        inst = FUTURES_INSTRUMENTS.get(symbol)
        if not inst:
            return ProviderResult(success=False, error_message=f"Unknown symbol: {symbol}")

        cache_path = self.cache_dir / f"funding_{symbol}_{interval}.jsonl"

        if not force and cache_path.exists():
            cached = self._load_cache(cache_path)
            if cached:
                snaps = [self._dict_to_snapshot(d, inst) for d in cached]
                return ProviderResult(success=True, record_count=len(snaps), derivatives=snaps)

        # Convert dates to milliseconds
        def _to_ms(date_str: str) -> int:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return int(dt.timestamp() * 1000)

        start_ms = _to_ms(start_date)
        end_ms = _to_ms(end_date) if end_date else int(datetime.now().timestamp() * 1000)

        all_snapshots: list[DerivativeSnapshotV1] = []
        current_start = start_ms

        while current_start < end_ms:
            limit = 1000
            url = f"{BINANCE_FUTURES_BASE}/fapi/v1/fundingRate"
            params = {
                "symbol": symbol,
                "startTime": current_start,
                "endTime": min(current_start + 800 * 3600 * 1000, end_ms),
                "limit": limit,
            }

            try:
                resp = self.session.get(url, params=params, timeout=30)
                if resp.status_code != 200:
                    break
                rows = resp.json()
                if not rows:
                    # No data in this range - advance by 30 days and retry
                    current_start += 30 * 24 * 3600 * 1000
                    if current_start >= end_ms:
                        break
                    continue

                for row in rows:
                    snap = self._funding_row_to_snapshot(row, inst)
                    if snap:
                        all_snapshots.append(snap)

                # Advance past last row
                last_time = rows[-1].get("fundingTime", 0)
                if last_time <= current_start:
                    break
                current_start = last_time + 1

                self._rate_limit(0.2)
            except (requests.RequestException, json.JSONDecodeError) as e:
                break

        cache_data = [s.to_json() for s in all_snapshots]
        self._save_cache(cache_path, cache_data)

        return ProviderResult(success=True, record_count=len(all_snapshots), derivatives=all_snapshots)

    def _funding_row_to_snapshot(self, row: dict, inst: dict) -> Optional[DerivativeSnapshotV1]:
        """Convert Binance funding rate row to DerivativeSnapshotV1."""
        try:
            funding_time_ms = int(row["fundingTime"])
            funding_rate = float(row["fundingRate"])

            dt = datetime.fromtimestamp(funding_time_ms / 1000, tz=timezone.utc)
            observed_at = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Funding is paid every 8h on Binance
            next_funding_ms = funding_time_ms + 8 * 3600 * 1000
            next_funding_dt = datetime.fromtimestamp(next_funding_ms / 1000, tz=timezone.utc)
            next_funding_at = next_funding_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            snap = DerivativeSnapshotV1(
                instrument_id=inst["instrument_id"],
                symbol=inst["symbol"],
                venue=inst["venue"],
                observed_at_utc=observed_at,
                interval="8h",
                funding_rate=funding_rate,
                next_funding_at_utc=next_funding_at,
                source_provider=self.provider_name,
                retrieved_at_utc=self._utc_now_str(),
                data_quality=DataQuality.EXACT_PUBLIC_API.value,
            )
            snap.snapshot_id = make_snapshot_id(
                snap.instrument_id, snap.observed_at_utc, self.provider_name
            )
            return snap
        except (ValueError, KeyError, TypeError):
            return None

    def _dict_to_snapshot(self, d: dict, inst: dict) -> DerivativeSnapshotV1:
        snap = DerivativeSnapshotV1.from_json(d)
        snap.instrument_id = inst["instrument_id"]
        return snap

    def fetch_bars(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        force: bool = False,
    ) -> ProviderResult:
        # Public API is for derivatives, not bars. Bars come from archive.
        return ProviderResult(success=True, record_count=0)
