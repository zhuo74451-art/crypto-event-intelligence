"""Public cross-asset data provider (Yahoo Finance, public indices).

Sources (free/public):
- ^GSPC  → SP500 (S&P 500 Index)
- ^IXIC  → NASDAQ Composite
- GC=F   → Gold Futures
- DX-Y.NYB → US Dollar Index (DXY)
- ^VIX   → CBOE Volatility Index
- SI=F   → Silver Futures
- CL=F   → WTI Crude Oil Futures
"""

from __future__ import annotations

import json
import time
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


# US Treasury yields via Yahoo (proxy for FRED DGS series)
# ^TNX = CBOE 10-Year Treasury Yield (proxy for DGS10)
# ^FVX = CBOE 5-Year Treasury Yield (proxy for DGS5)
# ^TYX = CBOE 30-Year Treasury Yield (proxy for DGS30)
# ^VIX = CBOE Volatility Index

YAHOO_INSTRUMENTS = {
    "^GSPC": {
        "symbol": "SP500",
        "instrument_id": "yahoo_sp500_index",
        "canonical_name": "S&P 500 Index",
        "venue": "yahoo_finance",
        "asset_class": "equities",
        "instrument_type": "index",
        "currency": "USD",
        "start_date": "1950-01-01",
    },
    "^IXIC": {
        "symbol": "NASDAQ",
        "instrument_id": "yahoo_nasdaq_composite",
        "canonical_name": "NASDAQ Composite Index",
        "venue": "yahoo_finance",
        "asset_class": "equities",
        "instrument_type": "index",
        "currency": "USD",
        "start_date": "1971-02-05",
    },
    "GC=F": {
        "symbol": "GOLD",
        "instrument_id": "yahoo_gold_futures",
        "canonical_name": "Gold Futures",
        "venue": "yahoo_finance",
        "asset_class": "commodities",
        "instrument_type": "commodity_future",
        "currency": "USD",
        "start_date": "1975-01-01",
    },
    "DX-Y.NYB": {
        "symbol": "DXY",
        "instrument_id": "yahoo_us_dollar_index",
        "canonical_name": "US Dollar Index (DXY)",
        "venue": "yahoo_finance",
        "asset_class": "fx",
        "instrument_type": "index",
        "currency": "USD",
        "start_date": "1973-03-01",
    },
    "SI=F": {
        "symbol": "SILVER",
        "instrument_id": "yahoo_silver_futures",
        "canonical_name": "Silver Futures",
        "venue": "yahoo_finance",
        "asset_class": "commodities",
        "instrument_type": "commodity_future",
        "currency": "USD",
        "start_date": "1986-01-01",
    },
    "^TNX": {
        "symbol": "US10Y",
        "instrument_id": "yahoo_us10y_yield",
        "canonical_name": "CBOE 10-Year Treasury Yield",
        "venue": "yahoo_finance",
        "asset_class": "rates",
        "instrument_type": "yield",
        "currency": "USD",
        "start_date": "2000-01-01",
    },
    "^FVX": {
        "symbol": "US5Y",
        "instrument_id": "yahoo_us5y_yield",
        "canonical_name": "CBOE 5-Year Treasury Yield",
        "venue": "yahoo_finance",
        "asset_class": "rates",
        "instrument_type": "yield",
        "currency": "USD",
        "start_date": "2000-01-01",
    },
    "^TYX": {
        "symbol": "US30Y",
        "instrument_id": "yahoo_us30y_yield",
        "canonical_name": "CBOE 30-Year Treasury Yield",
        "venue": "yahoo_finance",
        "asset_class": "rates",
        "instrument_type": "yield",
        "currency": "USD",
        "start_date": "2000-01-01",
    },
    "^VIX": {
        "symbol": "VIX",
        "instrument_id": "yahoo_vix_index",
        "canonical_name": "CBOE Volatility Index (VIX)",
        "venue": "yahoo_finance",
        "asset_class": "macro",
        "instrument_type": "index",
        "currency": "USD",
        "start_date": "2004-01-01",
    },
    "CL=F": {
        "symbol": "WTI",
        "instrument_id": "yahoo_wti_crude",
        "canonical_name": "WTI Crude Oil Futures",
        "venue": "yahoo_finance",
        "asset_class": "commodities",
        "instrument_type": "commodity_future",
        "currency": "USD",
        "start_date": "1983-01-01",
    },
}


class YahooFinanceProvider(BaseProvider):
    """Fetches daily OHLC data from Yahoo Finance."""

    CRUMB_URL = "https://fc.yahoo.com/ws/../v1/test/crumb"
    CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    def __init__(self, cache_dir: str | Path, output_dir: str | Path):
        super().__init__(cache_dir, output_dir, "yahoo_finance")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def list_instruments(self) -> list[dict[str, Any]]:
        return list(YAHOO_INSTRUMENTS.values())

    def fetch_bars(
        self,
        yahoo_symbol: str,
        interval: str = "1d",
        start_date: str = "2010-01-01",
        end_date: str = "",
        force: bool = False,
    ) -> ProviderResult:
        """Fetch daily bars from Yahoo Finance chart API."""
        if interval not in ("1d",):
            return ProviderResult(
                success=False,
                error_message=f"YahooFinance only supports 1d interval, got {interval}",
            )

        instrument_info = YAHOO_INSTRUMENTS.get(yahoo_symbol)
        if not instrument_info:
            return ProviderResult(success=False, error_message=f"Unknown symbol: {yahoo_symbol}")

        cache_path = self.cache_dir / f"{yahoo_symbol.replace('^', '').replace('=', '')}_daily.jsonl"

        if not force and cache_path.exists():
            cached = self._load_cache(cache_path)
            if cached:
                bars = [self._dict_to_bar(d, instrument_info) for d in cached]
                return ProviderResult(success=True, record_count=len(bars), bars=bars)

        # Convert dates to timestamps
        start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.now().timestamp()) if not end_date else int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

        url = f"{self.CHART_URL.format(symbol=yahoo_symbol)}?period1={start_ts}&period2={end_ts}&interval=1d&events=history"
        url += "&includePrePost=false"

        try:
            resp = self.session.get(url, timeout=60)
            if resp.status_code != 200:
                return ProviderResult(
                    success=False,
                    error_message=f"HTTP {resp.status_code} for {yahoo_symbol}",
                )
            data = resp.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            return ProviderResult(success=False, error_message=str(e))

        bars = self._parse_yahoo_chart(data, instrument_info)

        cache_data = [b.to_json() for b in bars]
        self._save_cache(cache_path, cache_data)

        self._rate_limit(0.3)
        return ProviderResult(success=True, record_count=len(bars), bars=bars)

    def _parse_yahoo_chart(self, data: dict, instrument_info: dict) -> list[MarketBarV1]:
        """Parse Yahoo Finance chart API response into bars."""
        bars: list[MarketBarV1] = []
        try:
            result = data["chart"]["result"][0]
            timestamps = result.get("timestamp", [])
            quotes = result.get("indicators", {}).get("quote", [{}])[0]
            adjclose_list = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])

            opens = quotes.get("open", [])
            highs = quotes.get("high", [])
            lows = quotes.get("low", [])
            closes = quotes.get("close", [])
            volumes = quotes.get("volume", [])
        except (KeyError, IndexError, TypeError):
            return bars

        for i, ts in enumerate(timestamps):
            if i >= len(opens) or opens[i] is None:
                continue
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            date_str = dt.strftime("%Y-%m-%d")

            bar = MarketBarV1(
                instrument_id=instrument_info["instrument_id"],
                symbol=instrument_info["symbol"],
                venue=instrument_info["venue"],
                asset_class=instrument_info["asset_class"],
                instrument_type=instrument_info["instrument_type"],
                quote_currency=instrument_info["currency"],
                interval="1d",
                open_time_utc=f"{date_str}T00:00:00Z",
                close_time_utc=f"{date_str}T23:59:59Z",
                open=float(opens[i]) if opens[i] else 0.0,
                high=float(highs[i]) if i < len(highs) and highs[i] else 0.0,
                low=float(lows[i]) if i < len(lows) and lows[i] else 0.0,
                close=float(closes[i]) if i < len(closes) and closes[i] else 0.0,
                volume=float(volumes[i]) if i < len(volumes) and volumes[i] else 0.0,
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
            "source": "Yahoo Finance public chart API",
            "license_note": "Public web data. Respect Yahoo Finance terms of service.",
        }
   
