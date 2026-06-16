"""Signal Spine IO v1 — Event Price Backfill & Abnormal Return Module (RC).

Deterministic post-event price returns across 1h/4h/24h windows using
Binance public 1m klines.

Modes:
  - fixture:     pre-built deterministic data, for test/demo only
  - network:     real Binance API; failure → unavailable/failed, NEVER fixture
  - network_with_cache: real API + local disk cache, NO manual fixture

Design constraints:
  - Read-only — never writes to any database, ledger, or Notion
  - No API key required — Binance public REST
  - Network-optional by mode choice, not by silent fallback
  - Single-asset failure never blocks batch
  - Max 120 s price lag — rejects stale snapshots
  - 24h split into individual window requests (not one large fetch)
  - All timestamps timezone-aware UTC
  - Self-benchmark (BTC->BTC, ETH->ETH) returns null + self_benchmark marker
  - No trading decisions. No buy/sell/long/short advice.

Data integrity every snapshot records:
  requested_time, actual_kline_open_time, lag_seconds, source, symbol, price, status

WindowReturn:
  return_decimal (0.007353) and return_percent (0.7353) both present.
  Abnormal returns similarly: btc_abnormal_return_decimal, eth_abnormal_return_decimal
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CN_TZ = timezone(timedelta(hours=8))

# ── Constants ───────────────────────────────────────────────────────────────

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
USER_AGENT = "SignalSpineIO-v1/1.0 (price-backfill; no-key public data)"

OBSERVATION_WINDOWS = ["1h", "4h", "24h"]
WINDOW_DELTA_MAP: dict[str, timedelta] = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "24h": timedelta(hours=24),
}
WINDOW_DELTA_MS: dict[str, int] = {
    "1h": 3600000,
    "4h": 14400000,
    "24h": 86400000,
}

MAX_PRICE_LAG_SECONDS = 120

SYMBOL_MAP: dict[str, str] = {
    "BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT",
    "BNB": "BNBUSDT", "XRP": "XRPUSDT", "DOGE": "DOGEUSDT",
    "LINK": "LINKUSDT", "ARB": "ARBUSDT", "OP": "OPUSDT",
    "AVAX": "AVAXUSDT", "SUI": "SUIUSDT", "DOT": "DOTUSDT",
    "ATOM": "ATOMUSDT", "UNI": "UNIUSDT", "AAVE": "AAVEUSDT",
    "TRX": "TRXUSDT", "TON": "TONUSDT", "NEAR": "NEARUSDT",
    "INJ": "INJUSDT", "APT": "APTUSDT",
}

CALCULATION_VERSION = "v1.18-rc"


class BackfillMode(str, Enum):
    FIXTURE = "fixture"
    NETWORK = "network"
    NETWORK_WITH_CACHE = "network_with_cache"


# ── Data Structures ─────────────────────────────────────────────────────────


@dataclass
class PriceSnapshot:
    """Single price data point with full provenance."""
    symbol: str
    price: Optional[float] = None
    requested_time: Optional[str] = None
    actual_kline_open_time: Optional[str] = None
    lag_seconds: Optional[int] = None
    source: str = "unknown"
    status: str = "pending"  # completed | pending | unavailable | max_lag_exceeded
    error_reason: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class WindowReturn:
    """Price return for a single observation window.

    Both decimal (0.007353) and percent (0.7353) forms are provided.
    """
    window: str
    target_price_snapshot: PriceSnapshot = field(default_factory=lambda: PriceSnapshot(symbol=""))
    status: str = "pending"
    return_decimal: Optional[float] = None
    return_percent: Optional[float] = None
    btc_return_decimal: Optional[float] = None
    btc_return_percent: Optional[float] = None
    eth_return_decimal: Optional[float] = None
    eth_return_percent: Optional[float] = None
    btc_abnormal_return_decimal: Optional[float] = None
    btc_abnormal_return_percent: Optional[float] = None
    eth_abnormal_return_decimal: Optional[float] = None
    eth_abnormal_return_percent: Optional[float] = None

    def as_dict(self) -> dict:
        d = asdict(self)
        d["target_price_snapshot"] = self.target_price_snapshot.as_dict()
        return d


@dataclass
class PriceBackfillResult:
    """Complete result of backfilling prices for one event on one asset."""
    event_id: str
    event_time: str
    asset: str
    mapped_symbol: str
    t0_snapshot: PriceSnapshot = field(default_factory=lambda: PriceSnapshot(symbol=""))
    windows: list[WindowReturn] = field(default_factory=list)
    backfill_status: str = "pending"
    mode: str = "fixture"
    calculation_version: str = CALCULATION_VERSION
    data_origin: str = "unknown"
    network_error: Optional[str] = None
    error_reason: Optional[str] = None
    fixture_id: Optional[str] = None
    calculated_at: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        d["t0_snapshot"] = self.t0_snapshot.as_dict()
        d["windows"] = [w.as_dict() for w in self.windows]
        return d


# ── HTTP Helper ─────────────────────────────────────────────────────────────


def _http_get_json(url: str, timeout: int = 15) -> list | dict:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
    return json.loads(data)


# ── Symbol Mapping ──────────────────────────────────────────────────────────


def map_symbol(asset: str) -> tuple[str, bool]:
    if not asset:
        return "", False
    upper = asset.strip().upper()
    if upper.endswith("USDT") and len(upper) > 4:
        return upper, True
    if upper in SYMBOL_MAP:
        return SYMBOL_MAP[upper], True
    candidate = f"{upper}USDT"
    if candidate in set(SYMBOL_MAP.values()):
        return candidate, True
    return upper, False


def is_self_benchmark(asset: str, benchmark_symbol: str) -> bool:
    mapped, _ = map_symbol(asset)
    return mapped == benchmark_symbol


# ── Time Helpers ────────────────────────────────────────────────────────────


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_time(iso_str: str) -> Optional[datetime]:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_to_ms(iso_str: str) -> Optional[int]:
    dt = parse_iso_time(iso_str)
    if dt is None:
        return None
    return int(dt.timestamp() * 1000)


# ── Binance Kline Fetching (small window per target) ────────────────────────


def fetch_klines_window(
    symbol: str,
    target_time_ms: int,
    interval: str = "1m",
    window_minutes: int = 5,
    timeout: int = 15,
) -> Optional[list]:
    """Fetch klines around a specific target time (small window).

    Requests klines from target_time - 1m to target_time + window_minutes.
    This avoids fetching the full 24h in one request.

    Args:
        symbol: Binance symbol
        target_time_ms: Target timestamp in ms
        interval: Kline interval (default 1m)
        window_minutes: How many minutes after target to fetch
        timeout: HTTP timeout

    Returns:
        List of klines, or None on failure.
    """
    params = (
        f"symbol={symbol}&interval={interval}"
        f"&startTime={target_time_ms - 60000}"
        f"&limit={window_minutes + 2}"
    )
    url = f"{BINANCE_KLINES_URL}?{params}"
    try:
        data = _http_get_json(url, timeout=timeout)
        return data if isinstance(data, list) else None
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None


# ── Kline Selection with Max Lag ────────────────────────────────────────────


def select_kline_at_time(
    klines: list,
    target_time_ms: int,
    max_lag_s: int = MAX_PRICE_LAG_SECONDS,
) -> tuple[Optional[list], int, Optional[str]]:
    """Select first kline whose open_time >= target_time, within max_lag.

    Binance kline format: [open_time, open, high, low, close, volume, ...]

    Returns:
        (kline_or_None, lag_seconds, error_reason_or_None)
          - lag_seconds: how many seconds after target the kline opens
          - error_reason: if lag exceeds max_lag_s or no kline found
    """
    if not klines:
        return None, 0, "no_klines_available"

    for k in klines:
        if isinstance(k, list) and len(k) >= 5:
            open_time_ms = int(k[0])
            if open_time_ms >= target_time_ms:
                lag_s = int((open_time_ms - target_time_ms) / 1000)
                if lag_s > max_lag_s:
                    return k, lag_s, f"price_snapshot_too_far_from_target: lag={lag_s}s > max={max_lag_s}s"
                return k, lag_s, None

    # All klines are before target_time — pick last one
    last = klines[-1] if klines else None
    if isinstance(last, list) and len(last) >= 5:
        last_open = int(last[0])
        lag_s = int((target_time_ms - last_open) / 1000)  # negative lag = before target
        # If the last kline ended long before target, it's stale
        if lag_s > max_lag_s:
            return last, -lag_s, f"price_snapshot_too_far_from_target: last_kline_at={ms_to_iso(last_open)}, lag={-lag_s}s > max={max_lag_s}s"
        return last, -lag_s, None

    return None, 0, "no_valid_klines_in_response"


def kline_open_price(kline: list) -> Optional[float]:
    if not kline or len(kline) < 5:
        return None
    try:
        return float(kline[1])
    except (ValueError, TypeError, IndexError):
        return None


# ── Fixture: Deterministic Kline Data ───────────────────────────────────────


FIXTURE_REFERENCE_TIME_UTC = "2026-06-15T12:00:00Z"
FIXTURE_REFERENCE_TIME_MS = 1781524800000
"""Verified: datetime.fromtimestamp(1781524800000 / 1000, UTC) → 2026-06-15T12:00:00Z"""


def get_fixture_klines(symbol: str) -> Optional[list]:
    """Pre-built deterministic klines for offline testing.

    All timestamps are relative to FIXTURE_REFERENCE_TIME_MS.
    Format: [open_time, open, high, low, close, volume, close_time]
    """
    ref = FIXTURE_REFERENCE_TIME_MS
    fixtures = {
        "BTCUSDT": [
            [ref,            "68000.00", "68100.00", "67900.00", "68050.00", "100.5", ref + 60000],
            [ref + 60000,    "68050.00", "68150.00", "67950.00", "68100.00", "95.2",  ref + 120000],
            [ref + 3600000,  "68500.00", "68600.00", "68400.00", "68550.00", "110.3", ref + 3660000],
            [ref + 3660000,  "68550.00", "68650.00", "68450.00", "68600.00", "105.8", ref + 3720000],
            [ref + 14400000, "69200.00", "69300.00", "69100.00", "69250.00", "120.1", ref + 14460000],
            [ref + 14460000, "69250.00", "69350.00", "69150.00", "69300.00", "115.4", ref + 14520000],
            [ref + 86400000, "69500.00", "69600.00", "69400.00", "69550.00", "130.7", ref + 86460000],
            [ref + 86460000, "69550.00", "69650.00", "69450.00", "69600.00", "125.9", ref + 86520000],
        ],
        "ETHUSDT": [
            [ref,            "3500.00", "3510.00", "3490.00", "3505.00", "500.2", ref + 60000],
            [ref + 60000,    "3505.00", "3515.00", "3495.00", "3510.00", "480.6", ref + 120000],
            [ref + 3600000,  "3550.00", "3560.00", "3540.00", "3555.00", "510.3", ref + 3660000],
            [ref + 3660000,  "3555.00", "3565.00", "3545.00", "3560.00", "495.8", ref + 3720000],
            [ref + 14400000, "3620.00", "3630.00", "3610.00", "3625.00", "530.1", ref + 14460000],
            [ref + 14460000, "3625.00", "3635.00", "3615.00", "3630.00", "520.4", ref + 14520000],
            [ref + 86400000, "3580.00", "3590.00", "3570.00", "3585.00", "490.7", ref + 86460000],
            [ref + 86460000, "3585.00", "3595.00", "3575.00", "3590.00", "475.9", ref + 86520000],
        ],
        "SOLUSDT": [
            [ref,            "175.00", "176.00", "174.00", "175.50", "2000.5", ref + 60000],
            [ref + 60000,    "175.50", "176.50", "174.50", "176.00", "1900.3", ref + 120000],
            [ref + 3600000,  "180.00", "181.00", "179.00", "180.50", "2100.7", ref + 3660000],
            [ref + 3660000,  "180.50", "181.50", "179.50", "181.00", "2050.2", ref + 3720000],
            [ref + 14400000, "178.00", "179.00", "177.00", "178.50", "1950.6", ref + 14460000],
            [ref + 14460000, "178.50", "179.50", "177.50", "179.00", "1900.1", ref + 14520000],
            [ref + 86400000, "182.00", "183.00", "181.00", "182.50", "2200.4", ref + 86460000],
            [ref + 86460000, "182.50", "183.50", "181.50", "183.00", "2150.8", ref + 86520000],
        ],
    }
    return fixtures.get(symbol)


# ── Fixture: Partial maturity (deterministic clock) ─────────────────────────


FIXTURE_PARTIAL_NOW_UTC = "2026-06-16T12:00:00Z"
FIXTURE_PARTIAL_EVENT_UTC = "2026-06-16T10:30:00Z"
"""Now=2026-06-16T12:00:00Z, event=2026-06-16T10:30:00Z → 1h mature, 4h pending, 24h pending"""


def get_fixture_klines_partial(symbol: str) -> Optional[list]:
    """Fixture where only 1h is mature.

    Event: 2026-06-16T10:30:00Z (90 min before now)
    Now:   2026-06-16T12:00:00Z
    → 1h  mature  (event+1h=11:30 < 12:00)
    → 4h  pending (event+4h=14:30 > 12:00)
    → 24h pending (event+24h=next day > now)
    """
    event_ms = 1781533800000  # 2026-06-16T10:30:00Z
    if symbol == "BTCUSDT":
        return [
            [event_ms,            "69000.00", "69100.00", "68900.00", "69050.00", "100.0", event_ms + 60000],
            [event_ms + 60000,    "69050.00", "69150.00", "68950.00", "69100.00", "95.0",  event_ms + 120000],
            [event_ms + 3600000,  "69500.00", "69600.00", "69400.00", "69550.00", "110.0", event_ms + 3660000],
            [event_ms + 3660000,  "69550.00", "69650.00", "69450.00", "69600.00", "108.0", event_ms + 3720000],
        ]
    return get_fixture_klines(symbol)


# ── Core Backfill ───────────────────────────────────────────────────────────


_NOW_DEFAULT: Callable[[], datetime] = lambda: datetime.now(timezone.utc)


class EventPriceBackfill:
    """Deterministic price backfill for event intelligence.

    Args:
        mode: BackfillMode.FIXTURE, .NETWORK, or .NETWORK_WITH_CACHE
        now_provider: Optional callable returning current UTC datetime.
                      Inject for deterministic tests. Default: datetime.now(UTC)
        max_price_lag_seconds: Max allowed lag between target time and kline
                               open time. Default 120 s.
    """

    def __init__(
        self,
        mode: str | BackfillMode = BackfillMode.FIXTURE,
        now_provider: Optional[Callable[[], datetime]] = None,
        max_price_lag_seconds: int = MAX_PRICE_LAG_SECONDS,
    ):
        self.mode = BackfillMode(mode) if isinstance(mode, str) else mode
        self._now_provider = now_provider or _NOW_DEFAULT
        self._max_lag = max_price_lag_seconds

    # ── Public API ────────────────────────────────────────────────────────

    def backfill(
        self,
        event_id: str,
        event_time: str,
        assets: list[str],
        fixture_id: Optional[str] = None,
    ) -> list[PriceBackfillResult]:
        """Backfill prices for a single event across multiple assets.

        Args:
            event_id: Unique event identifier
            event_time: ISO-8601 UTC event timestamp
            assets: List of asset names
            fixture_id: Optional fixture ID (recorded when mode=fixture)

        Returns:
            List of PriceBackfillResult, one per asset.
        """
        now_utc = self._now_provider()
        results: list[PriceBackfillResult] = []

        for asset in assets:
            result = self._backfill_single(asset, event_id, event_time, now_utc, fixture_id)
            results.append(result)

        return results

    # ── Single Asset ──────────────────────────────────────────────────────

    def _backfill_single(
        self,
        asset: str,
        event_id: str,
        event_time: str,
        now_utc: datetime,
        fixture_id: Optional[str] = None,
    ) -> PriceBackfillResult:
        mapped_symbol, supported = map_symbol(asset)

        if not supported:
            return PriceBackfillResult(
                event_id=event_id, event_time=event_time,
                asset=asset, mapped_symbol=mapped_symbol,
                backfill_status="failed", mode=self.mode.value,
                data_origin="symbol_mapping",
                network_error=None,
                error_reason=f"unsupported_symbol: cannot map '{asset}'",
                calculated_at=utc_now(),
            )

        event_dt = parse_iso_time(event_time)
        if event_dt is None:
            return PriceBackfillResult(
                event_id=event_id, event_time=event_time,
                asset=asset, mapped_symbol=mapped_symbol,
                backfill_status="failed", mode=self.mode.value,
                data_origin="input_validation",
                error_reason=f"invalid_event_time: cannot parse '{event_time}'",
                calculated_at=utc_now(),
            )

        event_time_ms = int(event_dt.timestamp() * 1000)
        data_origin = self.mode.value

        # ── Get t0 price ──────────────────────────────────────────────
        t0_kline, t0_source, network_err, t0_sel_err = self._fetch_target_kline(
            mapped_symbol, event_time_ms, "t0",
        )
        t0_snapshot = self._build_snapshot(
            symbol=mapped_symbol, kline=t0_kline,
            requested_time=event_time, source=t0_source,
            target_time_ms=event_time_ms,
            select_error=t0_sel_err,
        )

        if t0_snapshot.status != "completed":
            return PriceBackfillResult(
                event_id=event_id, event_time=event_time,
                asset=asset, mapped_symbol=mapped_symbol,
                t0_snapshot=t0_snapshot,
                backfill_status="failed", mode=self.mode.value,
                data_origin=data_origin,
                network_error=network_err,
                error_reason=t0_snapshot.error_reason or "t0_kline_unavailable",
                calculated_at=utc_now(),
            )

        t0_price = t0_snapshot.price
        assert t0_price is not None  # guaranteed by status check above

        # ── Get benchmark klines at event time ────────────────────────
        btc_t0_kline, _, _, _ = self._fetch_target_kline("BTCUSDT", event_time_ms, "t0")
        eth_t0_kline, _, _, _ = self._fetch_target_kline("ETHUSDT", event_time_ms, "t0")
        btc_t0_price = kline_open_price(btc_t0_kline) if btc_t0_kline else None
        eth_t0_price = kline_open_price(eth_t0_kline) if eth_t0_kline else None

        # ── Calculate windows ─────────────────────────────────────────
        windows: list[WindowReturn] = []
        all_completed = True
        any_completed = False

        for wname in OBSERVATION_WINDOWS:
            delta_ms = WINDOW_DELTA_MS[wname]
            target_ms = event_time_ms + delta_ms
            window_deadline = datetime.fromtimestamp(target_ms / 1000.0, tz=timezone.utc)

            if window_deadline > now_utc:
                windows.append(WindowReturn(
                    window=wname,
                    target_price_snapshot=PriceSnapshot(
                        symbol=mapped_symbol, status="pending",
                        requested_time=ms_to_iso(target_ms),
                    ),
                    status="pending",
                ))
                all_completed = False
                continue

            # Fetch kline for this window
            wk, w_source, w_err, w_sel_err = self._fetch_target_kline(
                mapped_symbol, target_ms, wname,
            )
            w_snap = self._build_snapshot(
                symbol=mapped_symbol, kline=wk,
                requested_time=ms_to_iso(target_ms),
                source=w_source, target_time_ms=target_ms,
                select_error=w_sel_err,
            )

            if w_snap.status != "completed":
                windows.append(WindowReturn(
                    window=wname,
                    target_price_snapshot=w_snap,
                    status=w_snap.status,
                ))
                continue

            target_price = w_snap.price
            assert target_price is not None

            # Asset return
            r_dec = (target_price / t0_price) - 1.0
            r_pct = r_dec * 100.0

            # Benchmark returns for this window
            btc_r = self._benchmark_return_at(
                "BTCUSDT", target_ms, btc_t0_price, event_time_ms,
            )
            eth_r = self._benchmark_return_at(
                "ETHUSDT", target_ms, eth_t0_price, event_time_ms,
            )

            # Self-benchmark handling
            is_btc_self = is_self_benchmark(mapped_symbol, "BTCUSDT")
            is_eth_self = is_self_benchmark(mapped_symbol, "ETHUSDT")

            btc_ab_dec: Optional[float] = None
            btc_ab_pct: Optional[float] = None
            eth_ab_dec: Optional[float] = None
            eth_ab_pct: Optional[float] = None

            if is_btc_self:
                btc_ab_dec = None
                btc_ab_pct = None
            elif btc_r is not None:
                btc_ab_dec = r_dec - btc_r
                btc_ab_pct = btc_ab_dec * 100.0 if btc_ab_dec is not None else None

            if is_eth_self:
                eth_ab_dec = None
                eth_ab_pct = None
            elif eth_r is not None:
                eth_ab_dec = r_dec - eth_r
                eth_ab_pct = eth_ab_dec * 100.0 if eth_ab_dec is not None else None

            wr = WindowReturn(
                window=wname,
                target_price_snapshot=w_snap,
                status="completed",
                return_decimal=round(r_dec, 6),
                return_percent=round(r_pct, 4),
                btc_return_decimal=round(btc_r, 6) if btc_r is not None else None,
                btc_return_percent=round(btc_r * 100.0, 4) if btc_r is not None else None,
                eth_return_decimal=round(eth_r, 6) if eth_r is not None else None,
                eth_return_percent=round(eth_r * 100.0, 4) if eth_r is not None else None,
                btc_abnormal_return_decimal=round(btc_ab_dec, 6) if btc_ab_dec is not None else None,
                btc_abnormal_return_percent=round(btc_ab_pct, 4) if btc_ab_pct is not None else None,
                eth_abnormal_return_decimal=round(eth_ab_dec, 6) if eth_ab_dec is not None else None,
                eth_abnormal_return_percent=round(eth_ab_pct, 4) if eth_ab_pct is not None else None,
            )
            windows.append(wr)
            any_completed = True

        # Overall status
        if all_completed and all(w.status == "completed" for w in windows):
            status = "completed"
        elif any_completed:
            status = "partial"
        elif all(w.status == "pending" for w in windows):
            status = "pending"
        else:
            status = "partial"

        return PriceBackfillResult(
            event_id=event_id, event_time=event_time,
            asset=asset, mapped_symbol=mapped_symbol,
            t0_snapshot=t0_snapshot, windows=windows,
            backfill_status=status, mode=self.mode.value,
            calculation_version=CALCULATION_VERSION,
            data_origin=data_origin,
            network_error=network_err,
            fixture_id=fixture_id,
            calculated_at=utc_now(),
        )

    # ── Kline Fetch (mode-aware) ─────────────────────────────────────────

    def _fetch_target_kline(
        self, symbol: str, target_time_ms: int, label: str,
    ) -> tuple[Optional[list], str, Optional[str], Optional[str]]:
        """Fetch kline near target_time_ms.

        Returns:
            (kline_or_None, source_label, network_error_or_None, select_error_or_None)
        """
        if self.mode == BackfillMode.FIXTURE:
            klines = get_fixture_klines(symbol)
            if klines is None:
                return None, "fixture", None, None
            k, _, sel_err = select_kline_at_time(klines, target_time_ms, self._max_lag)
            return k, "fixture", None, sel_err

        # network or network_with_cache
        if self.mode == BackfillMode.NETWORK_WITH_CACHE:
            # TODO: implement disk cache layer
            pass

        # mode = network (or cache fallback from above)
        klines = fetch_klines_window(symbol, target_time_ms, window_minutes=5)
        if klines is None:
            return None, "network_error", f"binance_api_failed: {symbol} at {ms_to_iso(target_time_ms)}", None

        k, _, sel_err = select_kline_at_time(klines, target_time_ms, self._max_lag)
        return k, "binance_public_api", None, sel_err

    # ── Benchmark Return at Time ─────────────────────────────────────────

    def _benchmark_return_at(
        self,
        benchmark_symbol: str,
        target_time_ms: int,
        benchmark_t0_price: Optional[float],
        event_time_ms: int,
    ) -> Optional[float]:
        """Calculate benchmark return at target_time.

        Returns decimal return (e.g. 0.007353), or None if unavailable.
        """
        if benchmark_t0_price is None or benchmark_t0_price == 0:
            return None
        bk, _, _, _ = self._fetch_target_kline(benchmark_symbol, target_time_ms, "benchmark")
        if bk is None:
            return None
        b_price = kline_open_price(bk)
        if b_price is None or b_price == 0:
            return None
        return (b_price / benchmark_t0_price) - 1.0

    # ── Snapshot Builder ─────────────────────────────────────────────────

    def _build_snapshot(
        self,
        symbol: str,
        kline: Optional[list],
        requested_time: str,
        source: str,
        target_time_ms: int,
        select_error: Optional[str] = None,
    ) -> PriceSnapshot:
        """Build a PriceSnapshot from a kline result.

        If select_error indicates max lag exceeded, status becomes max_lag_exceeded.
        """
        if select_error and "price_snapshot_too_far_from_target" in select_error:
            actual_iso = ms_to_iso(int(kline[0])) if kline else None
            lag_s = abs(int((int(kline[0]) - target_time_ms) / 1000)) if kline else 0
            return PriceSnapshot(
                symbol=symbol, status="max_lag_exceeded",
                requested_time=requested_time,
                actual_kline_open_time=actual_iso,
                lag_seconds=lag_s, source=source,
                error_reason=select_error,
            )

        if kline is None:
            return PriceSnapshot(
                symbol=symbol, status="unavailable",
                requested_time=requested_time,
                source=source,
                error_reason="no_kline_found",
            )
        price = kline_open_price(kline)
        actual_open = int(kline[0])
        lag_s = abs(int((actual_open - target_time_ms) / 1000))
        actual_iso = ms_to_iso(actual_open)

        if price is None:
            return PriceSnapshot(
                symbol=symbol, price=None, status="unavailable",
                requested_time=requested_time,
                actual_kline_open_time=actual_iso,
                lag_seconds=lag_s, source=source,
                error_reason="cannot_extract_price_from_kline",
            )

        return PriceSnapshot(
            symbol=symbol, price=price, status="completed",
            requested_time=requested_time,
            actual_kline_open_time=actual_iso,
            lag_seconds=lag_s, source=source,
        )


def create_backfill(
    mode: str | BackfillMode = BackfillMode.FIXTURE,
    now_provider: Optional[Callable[[], datetime]] = None,
) -> EventPriceBackfill:
    return EventPriceBackfill(mode=mode, now_provider=now_provider)
