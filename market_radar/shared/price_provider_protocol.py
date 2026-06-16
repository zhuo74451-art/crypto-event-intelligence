"""Week 1 — Price Data Provider Protocol & Implementations.

PriceDataProvider protocol: uniform interface for getting a price snapshot
at a specific time from any data source (Binance, Hyperliquid, etc.).

Providers:
  - BinanceProvider: wraps EventPriceBackfill for 1m candles (BTC/ETH)
  - HyperliquidCandleProvider: standalone POST to HL Info API for 15m candles (HYPE)
  - ProviderRouter: selects provider by asset symbol

Design:
  - All providers return PriceSnapshot (reused from event_price_backfill)
  - No key required for any provider
  - Network failure -> unavailable — NO fixture fallback
  - Single asset failure never blocks batch
  - No trading decisions. No buy/sell/long/short.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Protocol
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from market_radar.shared.event_price_backfill import (
    PriceSnapshot,
    PriceBackfillResult,
    WindowReturn,
    EventPriceBackfill,
    BackfillMode,
    map_symbol,
    is_self_benchmark,
    ms_to_iso,
    iso_to_ms,
    OBSERVATION_WINDOWS,
    WINDOW_DELTA_MS,
    utc_now,
)

# ── Hyperliquid Constants ──────────────────────────────────────────────────

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
HL_USER_AGENT = "SignalSpineIO-v1/1.0 (hl-candle-provider; no-key)"
HL_MAX_LAG_SECONDS = 120

# ── Provider Protocol ──────────────────────────────────────────────────────


class PriceDataProvider(Protocol):
    """Protocol for a price data provider."""

    provider_name: str
    default_interval: str

    def get_snapshot(
        self,
        symbol: str,
        requested_time_iso: str,
        interval: str = "",
        max_lag_seconds: int = 120,
    ) -> PriceSnapshot:
        ...


# ── Binance Provider ──────────────────────────────────────────────────────


class BinanceProvider:
    """Price provider wrapping EventPriceBackfill for Binance 1m candles."""

    provider_name: str = "binance"
    default_interval: str = "1m"

    def __init__(self):
        self._backfill = EventPriceBackfill(mode=BackfillMode.NETWORK)

    def get_snapshot(
        self,
        symbol: str,
        requested_time_iso: str,
        interval: str = "1m",
        max_lag_seconds: int = 120,
    ) -> PriceSnapshot:
        mapped, supported = map_symbol(symbol)
        if not supported:
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time_iso,
                source=self.provider_name,
                error_reason=f"unsupported_symbol: '{symbol}' cannot be mapped",
            )
        event_ms = iso_to_ms(requested_time_iso)
        if event_ms is None:
            return PriceSnapshot(
                symbol=mapped, status="unavailable",
                requested_time=requested_time_iso,
                source=self.provider_name,
                error_reason=f"invalid_time: cannot parse '{requested_time_iso}'",
            )
        kline, source, net_err, sel_err = self._backfill._fetch_target_kline(
            mapped, event_ms, "snapshot",
        )
        return self._snapshot_from_kline(
            symbol=mapped, kline=kline,
            requested_time=requested_time_iso,
            source=source if source != "network_error" else self.provider_name,
            target_time_ms=event_ms, max_lag=max_lag_seconds,
            select_error=sel_err, network_error=net_err,
        )

    def _snapshot_from_kline(
        self, symbol: str, kline, requested_time: str, source: str,
        target_time_ms: int, max_lag: int = 120,
        select_error=None, network_error=None,
    ) -> PriceSnapshot:
        if network_error:
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time, source=source,
                error_reason=network_error,
            )
        if kline is None:
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time, source=source,
                error_reason="no_kline_available",
            )
        if select_error and "too_far_from_target" in select_error:
            actual_open = ms_to_iso(int(kline[0]))
            lag_s = abs(int((int(kline[0]) - target_time_ms) / 1000))
            return PriceSnapshot(
                symbol=symbol, status="max_lag_exceeded",
                requested_time=requested_time,
                actual_kline_open_time=actual_open,
                lag_seconds=lag_s, source=source,
                error_reason=select_error,
            )
        price = float(kline[1]) if len(kline) >= 2 and kline[1] else None
        actual_open = int(kline[0])
        lag_s = abs(int((actual_open - target_time_ms) / 1000))
        if price is None:
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time,
                lag_seconds=lag_s, source=source,
                error_reason="cannot_extract_price",
            )
        return PriceSnapshot(
            symbol=symbol, price=price, status="completed",
            requested_time=requested_time,
            actual_kline_open_time=ms_to_iso(actual_open),
            lag_seconds=lag_s, source=source,
        )


# ── Hyperliquid Candle Provider ────────────────────────────────────────────


def _hl_post(payload: dict, timeout: int = 15):
    """POST JSON to Hyperliquid Info API."""
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        HYPERLIQUID_INFO_URL, data=body,
        headers={"User-Agent": HL_USER_AGENT, "Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data)
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None


def get_hl_candle_fixture() -> list:
    """Deterministic HYPE candle fixture for offline testing.

    Mirrors a snapshot around 2026-05-25T13:00:00Z for HYPE.
    HL candle format: [time, open, high, low, close, volume]
    """
    base = 1779714000000  # 2026-05-25T13:00:00Z (verified)
    return [
        [base,           "12.50", "12.80", "12.30", "12.65", "500000"],
        [base + 900000,  "12.65", "12.90", "12.40", "12.75", "450000"],
        [base + 1800000, "12.75", "13.10", "12.60", "12.95", "520000"],
    ]


class HyperliquidCandleProvider:
    """Read-only Hyperliquid candle provider for 15m history.

    Uses Hyperliquid public Info API (candleSnapshot endpoint).
    Fixed interval: 15m (900s precision). No API key required.
    Network failure -> unavailable, NOT fixture.
    """

    provider_name: str = "hyperliquid"
    default_interval: str = "15m"
    precision_seconds: int = 900

    def __init__(self, use_fixture: bool = False):
        self._use_fixture = use_fixture
        self._source = "hyperliquid_fixture" if use_fixture else "hyperliquid_public_api"

    def get_snapshot(
        self,
        symbol: str,
        requested_time_iso: str,
        interval: str = "15m",
        max_lag_seconds: int = 120,
    ) -> PriceSnapshot:
        req_ms = iso_to_ms(requested_time_iso)
        if req_ms is None:
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time_iso, source=self.provider_name,
                error_reason=f"invalid_time: '{requested_time_iso}'",
            )
        candles = self._fetch_candles(symbol, req_ms)
        if candles is None:
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time_iso, source=self.provider_name,
                error_reason=f"hl_api_failed: no data for {symbol} at {requested_time_iso}",
            )
        if not candles:
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time_iso, source=self.provider_name,
                error_reason="hl_api_empty: no candles returned",
            )

        # Find first candle at or after target
        best, lag_s, err = self._select_candle(candles, req_ms, max_lag_seconds)
        if best is None:
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time_iso, source=self._source,
                error_reason=err or "no_candle_for_target",
            )
        if err:
            # Candle exists but exceeds max lag
            actual_open = ms_to_iso(int(best[0]))
            return PriceSnapshot(
                symbol=symbol, status="max_lag_exceeded",
                requested_time=requested_time_iso,
                actual_kline_open_time=actual_open,
                lag_seconds=lag_s, source=self._source,
                error_reason=f"lag {lag_s}s exceeds max {max_lag_seconds}s: {err}",
            )
        try:
            price = float(best[1])
        except (ValueError, TypeError, IndexError):
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time_iso, source=self._source,
                error_reason="cannot_extract_price_from_hl_candle",
            )
        return PriceSnapshot(
            symbol=symbol, price=price, status="completed",
            requested_time=requested_time_iso,
            actual_kline_open_time=ms_to_iso(int(best[0])),
            lag_seconds=lag_s, source=self._source,
        )

    def _select_candle(self, candles: list, target_ms: int, max_lag: int):
        """Select first candle at/after target within max_lag."""
        for c in candles:
            if isinstance(c, list) and len(c) >= 2:
                open_ms = int(c[0])
                lag = open_ms - target_ms
                if lag >= 0:
                    if lag > max_lag * 1000:
                        return c, int(lag / 1000), f"lag {lag/1000}s > max {max_lag}s"
                    return c, int(lag / 1000), None
        # All candles before target
        last = candles[-1] if candles else None
        if last and isinstance(last, list) and len(last) >= 2:
            last_ms = int(last[0])
            lag_s = abs(int((last_ms - target_ms) / 1000))
            return None, lag_s, f"no_candle_after_target: last at {ms_to_iso(last_ms)}"
        return None, 0, "empty_candle_list"

    def _fetch_candles(self, symbol: str, start_time_ms: int):
        """Fetch candles from HL Info API or fixture."""
        if self._use_fixture:
            return get_hl_candle_fixture()
        end_ms = start_time_ms + 3600000
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": symbol, "interval": "15m",
                "startTime": start_time_ms, "endTime": end_ms,
            },
        }
        result = _hl_post(payload)
        return result if isinstance(result, list) else None


# ── Provider Router ────────────────────────────────────────────────────────


class ProviderRouter:
    """Routes price requests to the correct provider by asset.

    Rules:
      - HYPE -> HyperliquidCandleProvider (15m)
      - BTC / ETH / mapped -> BinanceProvider (1m)
      - unknown -> None
    """

    def __init__(self, binance_provider=None, hyperliquid_provider=None):
        self.binance = binance_provider or BinanceProvider()
        self.hyperliquid = hyperliquid_provider or HyperliquidCandleProvider()

    def get_provider(self, asset: str):
        upper = asset.strip().upper()
        if upper == "HYPE":
            return self.hyperliquid, "hyperliquid", "15m"
        mapped, supported = map_symbol(upper)
        if supported:
            return self.binance, "binance", "1m"
        return None, "unsupported", ""

    def get_snapshot(self, asset: str, requested_time_iso: str):
        provider, pname, interval = self.get_provider(asset)
        if provider is None:
            return (
                PriceSnapshot(
                    symbol=asset, status="unavailable",
                    requested_time=requested_time_iso, source="router",
                    error_reason=f"unsupported_asset: no provider for '{asset}'",
                ),
                "unsupported", "", "unsupported_asset",
            )
        try:
            snapshot = provider.get_snapshot(asset, requested_time_iso, interval)
            return snapshot, pname, interval, ""
        except Exception as e:
            return (
                PriceSnapshot(
                    symbol=asset, status="unavailable",
                    requested_time=requested_time_iso, source=pname,
                    error_reason=f"provider_exception: {type(e).__name__}: {e}",
                ),
                pname, interval, str(e),
            )


# ── Week 1 Sample Result ───────────────────────────────────────────────────


@dataclass
class Week1SampleResult:
    """Raw price backfill result for one Week 1 sample.

    Contains raw price returns but NO attribution, confidence, or trading advice.
    """
    sample_id: str
    subject_asset: str
    observed_asset: str
    t0_basis: str
    broadcast_time: str
    provider: str
    interval: str
    precision_seconds: Optional[int] = None
    t0_snapshot: Optional[PriceSnapshot] = None
    return_1h: Optional[WindowReturn] = None
    return_4h: Optional[WindowReturn] = None
    return_24h: Optional[WindowReturn] = None
    btc_benchmark: Optional[PriceSnapshot] = None
    eth_benchmark: Optional[PriceSnapshot] = None
    btc_abnormal_return: Optional[float] = None
    eth_abnormal_return: Optional[float] = None
    data_origin: str = "network"
    network_error: Optional[str] = None
    calculation_version: str = "v1.18-week1"
    calculated_at: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        for field in ["t0_snapshot", "return_1h", "return_4h", "return_24h",
                       "btc_benchmark", "eth_benchmark"]:
            val = getattr(self, field)
            d[field] = val.as_dict() if val else None
        return d


# ── Week 1 Samples ─────────────────────────────────────────────────────────


WEEK1_SAMPLES = [
    {"sample_id": "W1-001-HYPE",    "subject_asset": "HYPE", "observed_asset": "HYPE",
     "broadcast_time": "2026-05-25T13:02:00Z"},
    {"sample_id": "W1-002-ETH",     "subject_asset": "ETH",  "observed_asset": "ETH",
     "broadcast_time": "2026-05-25T15:19:00Z"},
    {"sample_id": "W1-003-BTC",     "subject_asset": "BTC",  "observed_asset": "BTC",
     "broadcast_time": "2026-05-25T16:12:00Z"},
    {"sample_id": "W1-004-BTC-DUP", "subject_asset": "BTC",  "observed_asset": "BTC",
     "broadcast_time": "2026-05-25T16:12:00Z"},
    {"sample_id": "W1-005-MACRO-WTI",  "subject_asset": "WTI", "observed_asset": "BTC",
     "broadcast_time": "2026-05-25T11:34:00Z"},
    {"sample_id": "W1-005-MACRO-WTI-ETH", "subject_asset": "WTI", "observed_asset": "ETH",
     "broadcast_time": "2026-05-25T11:34:00Z"},
]


def run_week1_samples(router=None, now_for_maturity=None) -> list[Week1SampleResult]:
    """Run all Week 1 price backfill samples.

    Args:
        router: ProviderRouter (default: fresh router)
        now_for_maturity: Override clock for maturity check (default: now)

    Returns:
        List of Week1SampleResult.
    """
    if router is None:
        router = ProviderRouter()
    now = now_for_maturity or datetime.now(timezone.utc)
    results: list[Week1SampleResult] = []

    for sample in WEEK1_SAMPLES:
        sid = sample["sample_id"]
        subject = sample["subject_asset"]
        observed = sample["observed_asset"]
        bt = sample["broadcast_time"]
        bt_ms = iso_to_ms(bt)

        # Get t0 snapshot
        snapshot, pname, interval, err = router.get_snapshot(observed, bt)
        precision = 900 if pname == "hyperliquid" else 60 if pname == "binance" else None

        # Get benchmarks
        btc_snap, _, _, _ = router.get_snapshot("BTC", bt)
        eth_snap, _, _, _ = router.get_snapshot("ETH", bt)

        # Build window returns
        windows = _build_windows(observed, bt, bt_ms, now, router)

        result = Week1SampleResult(
            sample_id=sid, subject_asset=subject, observed_asset=observed,
            t0_basis=bt, broadcast_time=bt, provider=pname,
            interval=interval, precision_seconds=precision,
            t0_snapshot=snapshot,
            return_1h=windows["1h"], return_4h=windows["4h"], return_24h=windows["24h"],
            btc_benchmark=btc_snap, eth_benchmark=eth_snap,
            data_origin="network",
            network_error=err if err else None,
            calculated_at=utc_now(),
        )
        results.append(result)

    return results


def _build_windows(asset: str, bt_iso: str, bt_ms: int,
                   now: datetime, router: ProviderRouter) -> dict:
    """Build 1h/4h/24h WindowReturn objects."""
    windows: dict[str, Optional[WindowReturn]] = {"1h": None, "4h": None, "24h": None}
    if bt_ms is None:
        return windows

    for wname in ["1h", "4h", "24h"]:
        delta_ms = {"1h": 3600000, "4h": 14400000, "24h": 86400000}[wname]
        target_ms = bt_ms + delta_ms
        deadline = datetime.fromtimestamp(target_ms / 1000.0, tz=timezone.utc)

        if deadline > now:
            windows[wname] = WindowReturn(
                window=wname, status="pending",
                target_price_snapshot=PriceSnapshot(symbol=asset, status="pending"),
            )
            continue

        win_snap, _, _, _ = router.get_snapshot(asset, ms_to_iso(target_ms))
        if win_snap.status != "completed" or win_snap.price is None:
            windows[wname] = WindowReturn(
                window=wname, target_price_snapshot=win_snap, status=win_snap.status,
            )
            continue

        # Get t0 price
        t0_snap, _, _, _ = router.get_snapshot(asset, bt_iso)
        if t0_snap.status != "completed" or t0_snap.price is None:
            windows[wname] = WindowReturn(
                window=wname, status="unavailable",
                target_price_snapshot=win_snap,
            )
            continue

        r_dec = (win_snap.price / t0_snap.price) - 1.0
        wr = WindowReturn(
            window=wname, target_price_snapshot=win_snap, status="completed",
            return_decimal=round(r_dec, 6), return_percent=round(r_dec * 100.0, 4),
        )

        # Benchmark and abnormal returns
        btc_ret = _benchmark_return_at(router, "BTC", bt_iso, bt_ms, wname)
        eth_ret = _benchmark_return_at(router, "ETH", bt_iso, bt_ms, wname)

        wr.btc_return_decimal = round(btc_ret, 6) if btc_ret is not None else None
        wr.btc_return_percent = round(btc_ret * 100.0, 4) if btc_ret is not None else None
        wr.eth_return_decimal = round(eth_ret, 6) if eth_ret is not None else None
        wr.eth_return_percent = round(eth_ret * 100.0, 4) if eth_ret is not None else None

        if is_self_benchmark(asset, "BTCUSDT"):
            wr.btc_abnormal_return_decimal = None
            wr.btc_abnormal_return_percent = None
        elif btc_ret is not None:
            v = r_dec - btc_ret
            wr.btc_abnormal_return_decimal = round(v, 6)
            wr.btc_abnormal_return_percent = round(v * 100.0, 4)

        if is_self_benchmark(asset, "ETHUSDT"):
            wr.eth_abnormal_return_decimal = None
            wr.eth_abnormal_return_percent = None
        elif eth_ret is not None:
            v = r_dec - eth_ret
            wr.eth_abnormal_return_decimal = round(v, 6)
            wr.eth_abnormal_return_percent = round(v * 100.0, 4)

        windows[wname] = wr

    return windows


def _benchmark_return_at(router: ProviderRouter, asset: str,
                         bt_iso: str, bt_ms: int, wname: str) -> Optional[float]:
    """Calculate benchmark return for a given window."""
    delta_ms = {"1h": 3600000, "4h": 14400000, "24h": 86400000}[wname]
    target_ms = bt_ms + delta_ms
    target_iso = ms_to_iso(target_ms)

    t0_snap, _, _, _ = router.get_snapshot(asset, bt_iso)
    if t0_snap.status != "completed" or t0_snap.price is None:
        return None
    win_snap, _, _, _ = router.get_snapshot(asset, target_iso)
    if win_snap.status != "completed" or win_snap.price is None:
        return None
    return (win_snap.price / t0_snap.price) - 1.0
