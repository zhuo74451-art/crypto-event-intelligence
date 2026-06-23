"""Provider for crypto exchange public archives (Binance)."""

from __future__ import annotations

import gzip
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

from ..contracts import (
    MarketBarV1,
    DataQuality,
    Interval,
    make_bar_id,
)
from .base import BaseProvider, ProviderResult


BINANCE_BASE = "https://data.binance.vision/data/spot/monthly/klines"

INSTRUMENTS: list[dict[str, Any]] = [
    {
        "symbol": "BTCUSDT",
        "instrument_id": "binance_spot_btcusdt",
        "venue": "binance",
        "asset_class": "crypto",
        "instrument_type": "spot",
        "currency": "USDT",
        "available_intervals": ["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        "first_archive_date": "2017-08-17",
    },
    {
        "symbol": "ETHUSDT",
        "instrument_id": "binance_spot_ethusdt",
        "venue": "binance",
        "asset_class": "crypto",
        "instrument_type": "spot",
        "currency": "USDT",
        "available_intervals": ["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
        "first_archive_date": "2017-08-17",
    },
]


def _parse_binance_kline(raw: list, symbol: str, interval: str) -> Optional[dict]:
    """Parse a Binance archive kline row into a dict."""
    if not raw or len(raw) < 11:
        return None
    try:
        open_time_ms = int(raw[0])
        close_time_ms = int(raw[6])
        open_p = float(raw[1])
        high_p = float(raw[2])
        low_p = float(raw[3])
        close_p = float(raw[4])
        volume = float(raw[5])
        quote_vol = float(raw[7])
        trade_count = int(raw[8])

        def ms_to_utc(ms: int) -> str:
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return {
            "symbol": symbol,
            "open_time_utc": ms_to_utc(open_time_ms),
            "close_time_utc": ms_to_utc(close_time_ms),
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": volume,
            "quote_volume": quote_vol,
            "trade_count": trade_count,
        }
    except (ValueError, IndexError, TypeError):
        return None


def _build_archive_url(symbol: str, interval: str, year: int, month: int) -> str:
    return f"{BINANCE_BASE}/{symbol}/{interval}/{symbol}-{interval}-{year}-{month:02d}.zip"


class CryptoArchiveProvider(BaseProvider):
    """Fetches historical OHLCV data from Binance public archives."""

    def __init__(self, cache_dir: str | Path, output_dir: str | Path):
        super().__init__(cache_dir, output_dir, "binance_public_archive")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def list_instruments(self) -> list[dict[str, Any]]:
        return INSTRUMENTS

    def fetch_bars(
        self,
        symbol: str,
        interval: str,
        start_date: str,
        end_date: str,
        force: bool = False,
    ) -> ProviderResult:
        """Fetch monthly archive data from Binance public data."""
        # Generate month range
        start_parts = start_date.split("-")
        end_parts = end_date.split("-")
        start_year, start_month = int(start_parts[0]), int(start_parts[1])
        end_year, end_month = int(end_parts[0]), int(end_parts[1])

        all_bars: list[MarketBarV1] = []
        current_year, current_month = start_year, start_month

        while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
            url = _build_archive_url(symbol, interval, current_year, current_month)
            cache_name = f"{symbol}_{interval}_{current_year}_{current_month:02d}.jsonl"
            cache_path = self.cache_dir / cache_name

            month_bars = self._fetch_month_archive(
                url, symbol, interval, cache_path, force
            )
            all_bars.extend(month_bars)

            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        result = ProviderResult(success=True, record_count=len(all_bars))
        result.bars = all_bars
        return result

    def _fetch_month_archive(
        self,
        url: str,
        symbol: str,
        interval: str,
        cache_path: Path,
        force: bool,
    ) -> list[MarketBarV1]:
        """Fetch and parse a single monthly archive."""
        if not force and cache_path.exists():
            cached = self._load_cache(cache_path)
            if cached:
                return [self._dict_to_bar(d, symbol) for d in cached]

        try:
            resp = self.session.get(url, timeout=120, stream=True)
            if resp.status_code != 200:
                return []
            raw = resp.content
        except requests.RequestException:
            return []

        bars: list[MarketBarV1] = []
        try:
            import zipfile
            import io
            with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                for name in zf.namelist():
                    if name.endswith(".csv"):
                        text = zf.read(name).decode("utf-8")
                        for line in text.strip().split("\n"):
                            if not line.strip():
                                continue
                            parts = line.split(",")
                            parsed = _parse_binance_kline(parts, symbol, interval)
                            if parsed:
                                bar = self._dict_to_bar(parsed, symbol, interval)
                                bars.append(bar)
        except Exception:
            return []

        # Save cache
        cache_data = [b.to_json() for b in bars]
        self._save_cache(cache_path, cache_data)
        return bars

    def _dict_to_bar(self, d: dict, symbol: str, interval: str) -> MarketBarV1:
        instrument_id = "binance_spot_btcusdt" if "BTC" in symbol.upper() else "binance_spot_ethusdt"
        bar = MarketBarV1(
            instrument_id=instrument_id,
            symbol=symbol,
            venue="binance",
            asset_class="crypto",
            instrument_type="spot",
            quote_currency="USDT",
            interval=interval,
            open_time_utc=d["open_time_utc"],
            close_time_utc=d["close_time_utc"],
            open=d["open"],
            high=d["high"],
            low=d["low"],
            close=d["close"],
            volume=d["volume"],
            quote_volume=d.get("quote_volume", 0),
            trade_count=d.get("trade_count", 0),
            source_provider=self.provider_name,
            first_seen_at_utc=self._utc_now_str(),
            retrieved_at_utc=self._utc_now_str(),
            data_quality=DataQuality.EXACT_ARCHIVED.value,
        )
        bar.bar_id = make_bar_id(
            bar.instrument_id, bar.interval, bar.open_time_utc, self.provider_name
        )
        return bar
