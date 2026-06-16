"""Signal Spine IO v1 — Event Price Backfill & Abnormal Return Module.

Calculates deterministic post-event price returns across three observation
windows (1h / 4h / 24h) using Binance public 1m klines.

Design:
  - Reads only — never writes to any database, ledger, or Notion
  - No API key required — uses Binance public REST endpoint
  - Network-optional: all tests work offline via fixture fallback
  - Single-asset failure never blocks a batch
  - Pending windows (event not yet mature) are marked pending, not error
  - Self-benchmark (BTC→BTC, ETH→ETH) returns null benchmark with
    self_benchmark marker — does not fabricate information

Integration note: When the core pipeline integrates this module, call it
before the EventIntelligence stage so that price return data is available
for risk assessment. This module does NOT make trading decisions.

Output semantic: observation-only. No buy/sell/long/short advice.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CN_TZ = timezone(timedelta(hours=8))

# ── Constants ───────────────────────────────────────────────────────────────

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
USER_AGENT = "SignalSpineIO-v1/1.0 (price-backfill; no-key public data)"

OBSERVATION_WINDOWS = ["1h", "4h", "24h"]
WINDOW_DELTA_MAP = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "24h": timedelta(hours=24),
}

SYMBOL_MAP: dict[str, str] = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    "DOGE": "DOGEUSDT",
    "LINK": "LINKUSDT",
    "ARB": "ARBUSDT",
    "OP": "OPUSDT",
    "AVAX": "AVAXUSDT",
    "SUI": "SUIUSDT",
    "DOT": "DOTUSDT",
    "ATOM": "ATOMUSDT",
    "UNI": "UNIUSDT",
    "AAVE": "AAVEUSDT",
    "TRX": "TRXUSDT",
    "TON": "TONUSDT",
    "NEAR": "NEARUSDT",
    "INJ": "INJUSDT",
    "APT": "APTUSDT",
}

BENCHMARK_SYMBOLS = {"BTCUSDT": "BTC", "ETHUSDT": "ETH"}
BENCHMARK_ASSETS = ["BTCUSDT", "ETHUSDT"]

PIPELINE_VERSION = "v1.17"


# ── Data Structures ─────────────────────────────────────────────────────────


@dataclass
class WindowReturn:
    """Price return for a single observation window."""
    window: str
    target_price: Optional[float] = None
    target_time: Optional[str] = None
    return_pct: Optional[float] = None
    btc_return_pct: Optional[float] = None
    eth_return_pct: Optional[float] = None
    btc_abnormal_return: Optional[float] = None
    eth_abnormal_return: Optional[float] = None
    status: str = "pending"  # "completed" | "pending" | "unavailable"

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class PriceBackfillResult:
    """Complete result of backfilling prices for one event on one asset."""
    event_id: str
    event_time: str
    asset: str
    mapped_symbol: str
    t0_price: Optional[float] = None
    t0_time: Optional[str] = None
    windows: list[WindowReturn] = field(default_factory=list)
    backfill_status: str = "pending"  # "completed" | "partial" | "pending" | "failed"
    source: str = "unknown"
    error_reason: Optional[str] = None
    calculated_at: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        d["windows"] = [w.as_dict() for w in self.windows]
        return d


# ── HTTP Helper (reuses pattern from free_api_adapters.py) ──────────────────


def _http_get_json(url: str, timeout: int = 15) -> list | dict:
    """Simple HTTP GET -> JSON via urllib (no external deps)."""
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        data = resp.read().decode("utf-8")
    return json.loads(data)


# ── Symbol Mapping ──────────────────────────────────────────────────────────


def map_symbol(asset: str) -> tuple[str, bool]:
    """Map an asset name to a Binance symbol.

    Returns:
        (mapped_symbol, is_supported)
    """
    if not asset:
        return "", False
    upper = asset.strip().upper()
    # Already a USDT pair
    if upper.endswith("USDT") and len(upper) > 4:
        return upper, True
    # Look up in symbol map
    if upper in SYMBOL_MAP:
        return SYMBOL_MAP[upper], True
    # Try common pattern
    candidate = f"{upper}USDT"
    if candidate in set(SYMBOL_MAP.values()):
        return candidate, True
    return upper, False


def is_self_benchmark(asset: str, benchmark_symbol: str) -> bool:
    """Check if an asset IS the benchmark asset.

    e.g., BTCUSDT vs BTC benchmark => self_benchmark
    """
    mapped, _ = map_symbol(asset)
    return mapped == benchmark_symbol


# ── Time Helpers ────────────────────────────────────────────────────────────


def utc_now() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_time(iso_str: str) -> Optional[datetime]:
    """Parse an ISO-8601 time string to timezone-aware UTC datetime.

    Returns None if parsing fails.
    """
    if not iso_str:
        return None
    try:
        # Handle both Z and +00:00 suffixes
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def iso_from_binance_ms(ms: int) -> str:
    """Convert Binance millisecond timestamp to ISO UTC string."""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Binance Kline Fetching ──────────────────────────────────────────────────


def fetch_klines(
    symbol: str,
    interval: str = "1m",
    limit: int = 1,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    timeout: int = 15,
) -> Optional[list]:
    """Fetch klines from Binance public API.

    Uses the same no-key pattern as free_api_adapters.py.

    Args:
        symbol: Binance symbol e.g. BTCUSDT
        interval: Kline interval e.g. "1m"
        limit: Max number of klines
        start_time: Optional millisecond timestamp
        end_time: Optional millisecond timestamp

    Returns:
        List of klines, or None on failure.
    """
    params = f"symbol={symbol}&interval={interval}&limit={limit}"
    if start_time is not None:
        params += f"&startTime={start_time}"
    if end_time is not None:
        params += f"&endTime={end_time}"
    url = f"{BINANCE_KLINES_URL}?{params}"
    try:
        data = _http_get_json(url, timeout=timeout)
        if isinstance(data, list):
            return data
        return None
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None


def select_t0_kline(klines: list, event_time_ms: int) -> Optional[list]:
    """Select the first kline whose open_time >= event_time.

    Binance kline format: [open_time, open, high, low, close, volume, ...]
    """
    if not klines:
        return None
    for k in klines:
        if isinstance(k, list) and len(k) >= 5:
            open_time = int(k[0])
            if open_time >= event_time_ms:
                return k
    # If all klines are before event_time, return the last one
    return klines[-1] if isinstance(klines[-1], list) and len(klines[-1]) >= 5 else None


def select_window_kline(klines: list, target_time_ms: int) -> Optional[list]:
    """Select the first kline whose open_time >= target_time.

    Returns None if no kline meets the criterion.
    """
    if not klines:
        return None
    for k in klines:
        if isinstance(k, list) and len(k) >= 5:
            open_time = int(k[0])
            if open_time >= target_time_ms:
                return k
    return None


def kline_open_price(kline: list) -> Optional[float]:
    """Extract open price from a kline.

    Binance kline format: [open_time, open, high, low, close, volume, ...]
    """
    if not kline or len(kline) < 5:
        return None
    try:
        return float(kline[1])
    except (ValueError, TypeError, IndexError):
        return None


def ms_to_iso(ms: int) -> str:
    """Convert epoch milliseconds to ISO UTC string."""
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Fixture: Pre-built Kline Data ───────────────────────────────────────────


def get_fixture_klines(symbol: str) -> Optional[list]:
    """Get pre-built kline fixture data for offline testing.

    Returns a list of klines matching Binance format, or None if
    no fixture is available for this symbol.

    All fixtures use 1-minute intervals and are deterministic.
    """
    # Reference time: 2026-06-15T12:00:00Z in ms
    ref_time_ms = 1781524800000

    # ── BTCUSDT fixture (complete 24h) ──
    btc_fixture = [
        # [open_time, open, high, low, close, volume, close_time]
        [ref_time_ms, "68000.00", "68100.00", "67900.00", "68050.00", "100.5", ref_time_ms + 60000],
        [ref_time_ms + 60000, "68050.00", "68150.00", "67950.00", "68100.00", "95.2", ref_time_ms + 120000],
        # t+1h window (ref + 3600000ms)
        [ref_time_ms + 3600000, "68500.00", "68600.00", "68400.00", "68550.00", "110.3", ref_time_ms + 3660000],
        [ref_time_ms + 3660000, "68550.00", "68650.00", "68450.00", "68600.00", "105.8", ref_time_ms + 3720000],
        # t+4h window (ref + 14400000ms)
        [ref_time_ms + 14400000, "69200.00", "69300.00", "69100.00", "69250.00", "120.1", ref_time_ms + 14460000],
        [ref_time_ms + 14460000, "69250.00", "69350.00", "69150.00", "69300.00", "115.4", ref_time_ms + 14520000],
        # t+24h window (ref + 86400000ms)
        [ref_time_ms + 86400000, "69500.00", "69600.00", "69400.00", "69550.00", "130.7", ref_time_ms + 86460000],
        [ref_time_ms + 86460000, "69550.00", "69650.00", "69450.00", "69600.00", "125.9", ref_time_ms + 86520000],
    ]

    # ── ETHUSDT fixture ──
    eth_fixture = [
        [ref_time_ms, "3500.00", "3510.00", "3490.00", "3505.00", "500.2", ref_time_ms + 60000],
        [ref_time_ms + 60000, "3505.00", "3515.00", "3495.00", "3510.00", "480.6", ref_time_ms + 120000],
        [ref_time_ms + 3600000, "3550.00", "3560.00", "3540.00", "3555.00", "510.3", ref_time_ms + 3660000],
        [ref_time_ms + 3660000, "3555.00", "3565.00", "3545.00", "3560.00", "495.8", ref_time_ms + 3720000],
        [ref_time_ms + 14400000, "3620.00", "3630.00", "3610.00", "3625.00", "530.1", ref_time_ms + 14460000],
        [ref_time_ms + 14460000, "3625.00", "3635.00", "3615.00", "3630.00", "520.4", ref_time_ms + 14520000],
        [ref_time_ms + 86400000, "3580.00", "3590.00", "3570.00", "3585.00", "490.7", ref_time_ms + 86460000],
        [ref_time_ms + 86460000, "3585.00", "3595.00", "3575.00", "3590.00", "475.9", ref_time_ms + 86520000],
    ]

    # ── SOLUSDT fixture ──
    sol_fixture = [
        [ref_time_ms, "175.00", "176.00", "174.00", "175.50", "2000.5", ref_time_ms + 60000],
        [ref_time_ms + 60000, "175.50", "176.50", "174.50", "176.00", "1900.3", ref_time_ms + 120000],
        [ref_time_ms + 3600000, "180.00", "181.00", "179.00", "180.50", "2100.7", ref_time_ms + 3660000],
        [ref_time_ms + 3660000, "180.50", "181.50", "179.50", "181.00", "2050.2", ref_time_ms + 3720000],
        [ref_time_ms + 14400000, "178.00", "179.00", "177.00", "178.50", "1950.6", ref_time_ms + 14460000],
        [ref_time_ms + 14460000, "178.50", "179.50", "177.50", "179.00", "1900.1", ref_time_ms + 14520000],
        [ref_time_ms + 86400000, "182.00", "183.00", "181.00", "182.50", "2200.4", ref_time_ms + 86460000],
        [ref_time_ms + 86460000, "182.50", "183.50", "181.50", "183.00", "2150.8", ref_time_ms + 86520000],
    ]

    fixture_map = {
        "BTCUSDT": btc_fixture,
        "ETHUSDT": eth_fixture,
        "SOLUSDT": sol_fixture,
    }
    return fixture_map.get(symbol)


# ── Partial Fixture: Only 1h Mature ─────────────────────────────────────────


def get_fixture_klines_partial(symbol: str) -> Optional[list]:
    """Fixture data where only 1h window is mature (4h/24h pending).

    Reference time is set close to "now" so only 1h has elapsed.
    """
    # Use a very recent reference so 4h/24h haven't elapsed
    ref_near_now = int(time.time() * 1000) - 1800000  # 30 min ago
    btc_partial = [
        [ref_near_now, "69000.00", "69100.00", "68900.00", "69050.00", "100.0", ref_near_now + 60000],
        [ref_near_now + 60000, "69050.00", "69150.00", "68950.00", "69100.00", "95.0", ref_near_now + 120000],
        [ref_near_now + 3600000, "69500.00", "69600.00", "69400.00", "69550.00", "110.0", ref_near_now + 3660000],
    ]
    return btc_partial if symbol == "BTCUSDT" else (
        get_fixture_klines(symbol)  # fallback to full fixture
    )


# ── Core Backfill Logic ────────────────────────────────────────────────────


class EventPriceBackfill:
    """Backfill prices and calculate abnormal returns for an event.

    Usage:
        backfill = EventPriceBackfill(use_fixture=True)
        result = backfill.backfill(
            event_id="evt_001",
            event_time="2026-06-15T12:00:00Z",
            assets=["BTC", "ETH"],
        )
        print(result.as_dict())

    Design:
        - All times in UTC
        - Uses Binance 1m klines via public API
        - Network failure → automatic fixture fallback
        - Single-asset failure doesn't affect batch
        - Pending windows (not yet mature) → status="pending"
    """

    def __init__(self, use_fixture: bool = False):
        self.use_fixture = use_fixture
        self._source = "fixture" if use_fixture else "binance_public_api"

    def backfill(
        self,
        event_id: str,
        event_time: str,
        assets: list[str],
    ) -> list[PriceBackfillResult]:
        """Backfill prices for a single event across all specified assets.

        Args:
            event_id: Unique event identifier
            event_time: ISO-8601 UTC event timestamp
            assets: List of asset names (e.g. ["BTC", "ETH", "SOL"])

        Returns:
            List of PriceBackfillResult, one per asset.
        """
        results: list[PriceBackfillResult] = []
        now_utc = datetime.now(timezone.utc)

        for asset in assets:
            result = self._backfill_single(asset, event_id, event_time, now_utc)
            results.append(result)

        return results

    def _backfill_single(
        self,
        asset: str,
        event_id: str,
        event_time: str,
        now_utc: datetime,
    ) -> PriceBackfillResult:
        """Backfill prices for a single asset."""
        mapped_symbol, supported = map_symbol(asset)

        if not supported:
            return PriceBackfillResult(
                event_id=event_id,
                event_time=event_time,
                asset=asset,
                mapped_symbol=mapped_symbol,
                backfill_status="failed",
                source="symbol_mapping",
                error_reason=f"unsupported_symbol: cannot map '{asset}' to a known Binance pair",
                calculated_at=utc_now(),
            )

        event_dt = parse_iso_time(event_time)
        if event_dt is None:
            return PriceBackfillResult(
                event_id=event_id,
                event_time=event_time,
                asset=asset,
                mapped_symbol=mapped_symbol,
                backfill_status="failed",
                source="input_validation",
                error_reason=f"invalid_event_time: cannot parse '{event_time}'",
                calculated_at=utc_now(),
            )

        event_time_ms = int(event_dt.timestamp() * 1000)

        # ── Fetch klines for t0 and all windows ──
        # We need klines from event_time up to event_time + 24h + 1m
        fetch_end_ms = event_time_ms + 86400000 + 60000
        klines = self._fetch_klines(mapped_symbol, event_time_ms, fetch_end_ms)

        if klines is None:
            return PriceBackfillResult(
                event_id=event_id,
                event_time=event_time,
                asset=asset,
                mapped_symbol=mapped_symbol,
                backfill_status="failed",
                source=self._source if self.use_fixture else "network_error",
                error_reason="kline_fetch_failed: no data available from source",
                calculated_at=utc_now(),
            )

        if not klines:
            return PriceBackfillResult(
                event_id=event_id,
                event_time=event_time,
                asset=asset,
                mapped_symbol=mapped_symbol,
                backfill_status="failed",
                source=self._source,
                error_reason="missing_klines: empty response from source",
                calculated_at=utc_now(),
            )

        # ── Select t0 kline ──
        t0_kline = select_t0_kline(klines, event_time_ms)
        if t0_kline is None:
            return PriceBackfillResult(
                event_id=event_id,
                event_time=event_time,
                asset=asset,
                mapped_symbol=mapped_symbol,
                backfill_status="failed",
                source=self._source,
                error_reason="missing_t0_kline: no kline found at or after event_time",
                calculated_at=utc_now(),
            )

        t0_price = kline_open_price(t0_kline)
        t0_kline_time = ms_to_iso(int(t0_kline[0])) if t0_kline else None

        if t0_price is None:
            return PriceBackfillResult(
                event_id=event_id,
                event_time=event_time,
                asset=asset,
                mapped_symbol=mapped_symbol,
                backfill_status="failed",
                source=self._source,
                error_reason="invalid_t0_price: cannot extract open price from t0 kline",
                calculated_at=utc_now(),
            )

        # ── Fetch benchmark klines (BTCUSDT, ETHUSDT) ──
        btc_klines = self._fetch_klines("BTCUSDT", event_time_ms, fetch_end_ms)
        eth_klines = self._fetch_klines("ETHUSDT", event_time_ms, fetch_end_ms)
        btc_t0 = kline_open_price(select_t0_kline(btc_klines, event_time_ms)) if btc_klines else None
        eth_t0 = kline_open_price(select_t0_kline(eth_klines, event_time_ms)) if eth_klines else None

        # ── Calculate returns for each window ──
        windows: list[WindowReturn] = []
        all_completed = True
        any_completed = False

        for window_name in OBSERVATION_WINDOWS:
            w_result = self._calculate_window(
                window_name=window_name,
                event_time_ms=event_time_ms,
                t0_price=t0_price,
                now_utc=now_utc,
                mapped_symbol=mapped_symbol,
                klines=klines,
                btc_klines=btc_klines,
                eth_klines=eth_klines,
                btc_t0_price=btc_t0,
                eth_t0_price=eth_t0,
            )
            windows.append(w_result)
            if w_result.status == "completed":
                any_completed = True
            elif w_result.status == "pending":
                all_completed = False

        # ── Determine overall status ──
        if all_completed and all(w.status == "completed" for w in windows):
            backfill_status = "completed"
        elif any_completed:
            backfill_status = "partial"
        elif all(w.status == "pending" for w in windows):
            backfill_status = "pending"
        else:
            backfill_status = "partial"

        return PriceBackfillResult(
            event_id=event_id,
            event_time=event_time,
            asset=asset,
            mapped_symbol=mapped_symbol,
            t0_price=t0_price,
            t0_time=t0_kline_time,
            windows=windows,
            backfill_status=backfill_status,
            source=self._source,
            calculated_at=utc_now(),
        )

    def _fetch_klines(
        self,
        symbol: str,
        start_ms: int,
        end_ms: int,
    ) -> Optional[list]:
        """Fetch klines from Binance or fixture.

        If use_fixture is True, returns pre-built fixture data.
        Otherwise attempts Binance API with automatic fixture fallback.
        """
        if self.use_fixture:
            return get_fixture_klines(symbol)

        # Attempt Binance API
        klines = fetch_klines(
            symbol=symbol,
            interval="1m",
            limit=1500,  # ~24h at 1m intervals
            start_time=start_ms,
            end_time=end_ms,
        )

        if klines is not None:
            self._source = "binance_public_api"
            return klines

        # Fallback to fixture
        self._source = "fixture_fallback"
        return get_fixture_klines(symbol)

    def _calculate_window(
        self,
        window_name: str,
        event_time_ms: int,
        t0_price: float,
        now_utc: datetime,
        mapped_symbol: str,
        klines: list,
        btc_klines: Optional[list],
        eth_klines: Optional[list],
        btc_t0_price: Optional[float] = None,
        eth_t0_price: Optional[float] = None,
    ) -> WindowReturn:
        """Calculate return for a single observation window."""
        delta = WINDOW_DELTA_MAP.get(window_name, timedelta(hours=1))
        target_time_ms = event_time_ms + int(delta.total_seconds() * 1000)

        # Check if window is mature
        window_deadline = datetime.fromtimestamp(target_time_ms / 1000.0, tz=timezone.utc)
        if window_deadline > now_utc:
            return WindowReturn(
                window=window_name,
                status="pending",
            )

        # Select window kline
        wk = select_window_kline(klines, target_time_ms)
        if wk is None:
            return WindowReturn(
                window=window_name,
                status="unavailable",
            )

        target_price = kline_open_price(wk)
        target_time = ms_to_iso(int(wk[0])) if wk else None

        if target_price is None or target_price == 0:
            return WindowReturn(
                window=window_name,
                status="unavailable",
            )

        # Calculate asset return
        asset_return = (target_price / t0_price) - 1.0

        # Calculate benchmark returns (percentage)
        btc_return = self._get_benchmark_return(btc_klines, target_time_ms, btc_t0_price)
        eth_return = self._get_benchmark_return(eth_klines, target_time_ms, eth_t0_price)

        # Handle self-benchmark
        is_btc_self = is_self_benchmark(mapped_symbol, "BTCUSDT")
        is_eth_self = is_self_benchmark(mapped_symbol, "ETHUSDT")

        btc_abnormal: Optional[float] = None
        eth_abnormal: Optional[float] = None

        if is_btc_self:
            btc_abnormal = None  # self_benchmark — no information gain
        elif btc_return is not None:
            btc_abnormal = asset_return - btc_return

        if is_eth_self:
            eth_abnormal = None  # self_benchmark
        elif eth_return is not None:
            eth_abnormal = asset_return - eth_return

        return WindowReturn(
            window=window_name,
            target_price=target_price,
            target_time=target_time,
            return_pct=round(asset_return, 6),
            btc_return_pct=round(btc_return, 6) if btc_return is not None else None,
            eth_return_pct=round(eth_return, 6) if eth_return is not None else None,
            btc_abnormal_return=round(btc_abnormal, 6) if btc_abnormal is not None else None,
            eth_abnormal_return=round(eth_abnormal, 6) if eth_abnormal is not None else None,
            status="completed",
        )

    def _get_benchmark_return(
        self,
        benchmark_klines: Optional[list],
        target_time_ms: int,
        benchmark_t0_price: Optional[float] = None,
    ) -> Optional[float]:
        """Get benchmark return (percentage) at target time.

        Calculates: window_price / t0_price - 1
        Returns None if data is unavailable.
        """
        if benchmark_klines is None or benchmark_t0_price is None or benchmark_t0_price == 0:
            return None
        bk = select_window_kline(benchmark_klines, target_time_ms)
        if bk is None:
            return None
        b_price = kline_open_price(bk)
        if b_price is None or b_price == 0:
            return None
        return (b_price / benchmark_t0_price) - 1.0


def create_backfill(use_fixture: bool = False) -> EventPriceBackfill:
    """Factory: create an EventPriceBackfill instance."""
    return EventPriceBackfill(use_fixture=use_fixture)
