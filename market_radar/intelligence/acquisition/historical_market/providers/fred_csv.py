"""Provider for FRED (Federal Reserve Economic Data) public CSV downloads.

Sources:
- US 10Y Yield: https://fred.stlouisfed.org/data/DGS10.txt
- US 2Y Yield: https://fred.stlouisfed.org/data/DGS2.txt
- US 30Y Yield: https://fred.stlouisfed.org/data/DGS30.txt
- US 5Y Yield: https://fred.stlouisfed.org/data/DGS5.txt
- DXY (trade-weighted USD): via ICE data - use proxy
- VIX: https://fred.stlouisfed.org/data/VIXCLS.txt
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

from ..contracts import (
    MarketBarV1,
    DataQuality,
    AssetClass,
    InstrumentType,
    Interval,
    make_bar_id,
)
from .base import BaseProvider, ProviderResult


FRED_SERIES = {
    "DGS10": {
        "symbol": "US10Y",
        "instrument_id": "fred_us10y_yield",
        "canonical_name": "US 10-Year Treasury Yield",
        "venue": "fred",
        "asset_class": "rates",
        "instrument_type": "yield",
        "currency": "USD",
        "start_date": "1962-01-02",
    },
    "DGS2": {
        "symbol": "US2Y",
        "instrument_id": "fred_us2y_yield",
        "canonical_name": "US 2-Year Treasury Yield",
        "venue": "fred",
        "asset_class": "rates",
        "instrument_type": "yield",
        "currency": "USD",
        "start_date": "1976-06-01",
    },
    "DGS30": {
        "symbol": "US30Y",
        "instrument_id": "fred_us30y_yield",
        "canonical_name": "US 30-Year Treasury Yield",
        "venue": "fred",
        "asset_class": "rates",
        "instrument_type": "yield",
        "currency": "USD",
        "start_date": "1977-02-15",
    },
    "DGS5": {
        "symbol": "US5Y",
        "instrument_id": "fred_us5y_yield",
        "canonical_name": "US 5-Year Treasury Yield",
        "venue": "fred",
        "asset_class": "rates",
        "instrument_type": "yield",
        "currency": "USD",
        "start_date": "1976-06-01",
    },
    "VIXCLS": {
        "symbol": "VIX",
        "instrument_id": "fred_vix",
        "canonical_name": "CBOE Volatility Index (VIX)",
        "venue": "fred",
        "asset_class": "macro",
        "instrument_type": "index",
        "currency": "USD",
        "start_date": "1990-01-02",
    },
}


class FredCsvProvider(BaseProvider):
    """Fetches daily yield and index data from FRED."""

    FRED_BASE = "https://fred.stlouisfed.org/data"

    def __init__(self, cache_dir: str | Path, output_dir: str | Path):
        super().__init__(cache_dir, output_dir, "fred_csv")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def list_instruments(self) -> list[dict[str, Any]]:
        return list(FRED_SERIES.values())

    def fetch_bars(
        self,
        series_id: str,
        interval: str = "1d",
        start_date: str = "2010-01-01",
        end_date: str = "",
        force: bool = False,
    ) -> ProviderResult:
        """Fetch daily data from FRED for a series ID."""
        if interval not in ("1d",):
            return ProviderResult(success=False, error_message=f"FRED only supports 1d interval, got {interval}")

        series_info = FRED_SERIES.get(series_id)
        if not series_info:
            return ProviderResult(success=False, error_message=f"Unknown FRED series: {series_id}")

        url = f"{self.FRED_BASE}/{series_id}.txt"
        cache_path = self.cache_dir / f"{series_id}_daily.jsonl"

        if not force and cache_path.exists():
            cached = self._load_cache(cache_path)
            if cached:
                bars = [self._dict_to_bar(d, series_info) for d in cached]
                return ProviderResult(success=True, record_count=len(bars), bars=bars)

        try:
            resp = self.session.get(url, timeout=60)
            if resp.status_code != 200:
                return ProviderResult(
                    success=False, error_message=f"HTTP {resp.status_code} for {url}"
                )
            text = resp.text
        except requests.RequestException as e:
            return ProviderResult(success=False, error_message=str(e))

        bars = self._parse_fred_text(text, series_info)
        cache_data = [b.to_json() for b in bars]
        self._save_cache(cache_path, cache_data)

        return ProviderResult(success=True, record_count=len(bars), bars=bars)

    def _parse_fred_text(self, text: str, series_info: dict) -> list[MarketBarV1]:
        """Parse FRED text format."""
        bars: list[MarketBarV1] = []
        in_data = False

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("DATE") and "VALUE" in line:
                in_data = True
                continue
            if not in_data:
                continue
            # Skip footnotes
            if line.startswith(" ") or "NOTE" in line.upper():
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            date_str = parts[0]
            value_str = parts[1]

            if value_str in (".", "NA", ""):
                continue

            try:
                value = float(value_str)
            except ValueError:
                continue

            bar = MarketBarV1(
                instrument_id=series_info["instrument_id"],
                symbol=series_info["symbol"],
                venue=series_info["venue"],
                asset_class=series_info["asset_class"],
                instrument_type=series_info["instrument_type"],
                quote_currency=series_info["currency"],
                interval="1d",
                open_time_utc=f"{date_str}T00:00:00Z",
                close_time_utc=f"{date_str}T23:59:59Z",
                open=value,
                high=value,
                low=value,
                close=value,
                volume=0,
                source_provider=self.provider_name,
                first_seen_at_utc=self._utc_now_str(),
                retrieved_at_utc=self._utc_now_str(),
                data_quality=DataQuality.EXACT_PUBLIC_API.value,
            )
            bar.bar_id = make_bar_id(
                bar.instrument_id, bar.interval, bar.open_time_utc, self.provider_name
            )
            bars.append(bar)

        return bars

    def fetch_metadata(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "source": "Federal Reserve Economic Data (FRED)",
            "base_url": self.FRED_BASE,
            "license_note": "Public domain. See https://fred.stlouisfed.org/legal/",
        }
