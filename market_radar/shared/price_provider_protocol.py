"""Week 1 RC — Price Data Provider Protocol & HL Candle Provider (dict schema).

Hyperliquid 15m selection: nearest_candle_open (signed lag, max 450 s).
Binance 1m selection: first candle at/after target (max lag 120 s).
No fixture in network mode.
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
    WindowReturn,
    EventPriceBackfill,
    BackfillMode,
    map_symbol,
    is_self_benchmark,
    ms_to_iso,
    iso_to_ms,
    utc_now,
)

HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"
HL_USER_AGENT = "SignalSpineIO-v1/1.0 (hl-candle-provider; no-key)"
BINANCE_LAG_MAX_S = 120
HL_LAG_MAX_S = 450


# ── HL Candle Parsing ───────────────────────────────────────────────────────


@dataclass
class HLCandle:
    open_time_ms: int
    close_time_ms: int
    symbol: str
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int


def parse_hl_candle(candle: Any) -> Optional[HLCandle]:
    if not isinstance(candle, dict):
        return None
    try:
        open_ms = int(candle.get("t", 0))
        if open_ms <= 0:
            return None
        o = candle.get("o")
        if o is None:
            return None
        open_p = float(o)
        if open_p <= 0:
            return None
        return HLCandle(
            open_time_ms=open_ms,
            close_time_ms=int(candle.get("T", 0)),
            symbol=str(candle.get("s", "")),
            interval=str(candle.get("i", "")),
            open=open_p,
            high=float(candle.get("h", 0)),
            low=float(candle.get("l", 0)),
            close=float(candle.get("c", 0)),
            volume=float(candle.get("v", 0)),
            trade_count=int(candle.get("n", 0)),
        )
    except (ValueError, TypeError, KeyError):
        return None


def parse_hl_candles(raw: Any) -> list[HLCandle]:
    if not isinstance(raw, list):
        return []
    return [c for c in (parse_hl_candle(x) for x in raw) if c is not None]


# ── HL 15m Selection: nearest_candle_open ───────────────────────────────────


def select_nearest_candle(
    candles: list[HLCandle], target_time_ms: int, max_lag_s: int = HL_LAG_MAX_S,
) -> tuple[Optional[HLCandle], dict]:
    info: dict = {
        "selection_policy": "nearest_candle_open",
        "precision_seconds": 900,
        "signed_lag_seconds": None,
        "absolute_lag_seconds": None,
        "error_reason": None,
    }
    if not candles:
        info["error_reason"] = "no_candles_available"
        return None, info
    best: Optional[HLCandle] = None
    best_abs: Optional[int] = None
    for c in candles:
        signed = c.open_time_ms - target_time_ms
        abs_lag = abs(signed)
        if abs_lag > max_lag_s * 1000:
            continue
        if best is None or abs_lag < best_abs:
            best = c
            best_abs = abs_lag
        elif abs_lag == best_abs and c.open_time_ms < best.open_time_ms:
            best = c
    if best is None:
        nearest = min(candles, key=lambda c: abs(c.open_time_ms - target_time_ms))
        sl = int((nearest.open_time_ms - target_time_ms) / 1000)
        info["signed_lag_seconds"] = sl
        info["absolute_lag_seconds"] = abs(sl)
        info["error_reason"] = (
            f"max_lag_exceeded: nearest at {ms_to_iso(nearest.open_time_ms)}, "
            f"abs_lag={abs(sl)}s > max={max_lag_s}s"
        )
        return None, info
    sl = int((best.open_time_ms - target_time_ms) / 1000)
    info["signed_lag_seconds"] = sl
    info["absolute_lag_seconds"] = abs(sl)
    return best, info


# ── Fixture (dict format) ───────────────────────────────────────────────────


def get_hl_candle_fixture() -> list[dict]:
    b = 1779714000000  # 2026-05-25T13:00:00Z
    return [
        {"t": b, "T": b + 899999, "s": "HYPE", "i": "15m",
         "o": "12.50", "c": "12.65", "h": "12.80", "l": "12.30", "v": "500000", "n": "125"},
        {"t": b + 900000, "T": b + 1799999, "s": "HYPE", "i": "15m",
         "o": "12.65", "c": "12.75", "h": "12.90", "l": "12.40", "v": "450000", "n": "110"},
        {"t": b + 1800000, "T": b + 2699999, "s": "HYPE", "i": "15m",
         "o": "12.75", "c": "12.95", "h": "13.10", "l": "12.60", "v": "520000", "n": "135"},
    ]


# ── Binance Provider ────────────────────────────────────────────────────────


class BinanceProvider:
    provider_name: str = "binance"
    default_interval: str = "1m"
    selection_policy: str = "first_after_target"

    def __init__(self):
        self._backfill = EventPriceBackfill(mode=BackfillMode.NETWORK)

    def get_snapshot(
        self, symbol: str, requested_time_iso: str,
        interval: str = "1m", max_lag_seconds: int = BINANCE_LAG_MAX_S,
    ) -> tuple[PriceSnapshot, dict]:
        info: dict = {"selection_policy": self.selection_policy, "precision_seconds": 60,
                      "signed_lag_seconds": None, "absolute_lag_seconds": None}
        mapped, supported = map_symbol(symbol)
        if not supported:
            return PriceSnapshot(symbol=symbol, status="unavailable",
                                 requested_time=requested_time_iso, source=self.provider_name,
                                 error_reason=f"unsupported: '{symbol}'"), info
        event_ms = iso_to_ms(requested_time_iso)
        if event_ms is None:
            return PriceSnapshot(symbol=mapped, status="unavailable",
                                 requested_time=requested_time_iso, source=self.provider_name,
                                 error_reason=f"invalid_time: '{requested_time_iso}'"), info
        kline, source, net_err, sel_err = self._backfill._fetch_target_kline(mapped, event_ms, "snapshot")
        snap = self._kline_snapshot(mapped, kline, requested_time_iso, source, event_ms,
                                     max_lag_seconds, sel_err, net_err)
        if kline and len(kline) >= 2:
            sl = int((int(kline[0]) - event_ms) / 1000)
            info["signed_lag_seconds"] = sl
            info["absolute_lag_seconds"] = abs(sl)
        return snap, info

    def _kline_snapshot(self, symbol, kline, rtime, source, t_ms, max_lag, sel_err, net_err):
        if net_err:
            return PriceSnapshot(symbol=symbol, status="unavailable", requested_time=rtime,
                                 source=source, error_reason=net_err)
        if kline is None:
            return PriceSnapshot(symbol=symbol, status="unavailable", requested_time=rtime,
                                 source=source, error_reason="no_kline")
        if sel_err and "too_far" in sel_err:
            return PriceSnapshot(symbol=symbol, status="max_lag_exceeded", requested_time=rtime,
                                 actual_kline_open_time=ms_to_iso(int(kline[0])),
                                 lag_seconds=abs(int((int(kline[0]) - t_ms) / 1000)),
                                 source=source, error_reason=sel_err)
        price = float(kline[1]) if len(kline) >= 2 and kline[1] else None
        if price is None:
            return PriceSnapshot(symbol=symbol, status="unavailable", requested_time=rtime,
                                 source=source, error_reason="bad_price")
        return PriceSnapshot(symbol=symbol, price=price, status="completed", requested_time=rtime,
                             actual_kline_open_time=ms_to_iso(int(kline[0])),
                             lag_seconds=abs(int((int(kline[0]) - t_ms) / 1000)), source=source)


# ── Hyperliquid Provider ────────────────────────────────────────────────────


def _hl_post(payload: dict, timeout: int = 15):
    body = json.dumps(payload).encode("utf-8")
    req = Request(HYPERLIQUID_INFO_URL, data=body,
                  headers={"User-Agent": HL_USER_AGENT, "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, HTTPError, OSError, ValueError, json.JSONDecodeError):
        return None


class HyperliquidCandleProvider:
    provider_name: str = "hyperliquid"
    default_interval: str = "15m"
    precision_seconds: int = 900
    selection_policy: str = "nearest_candle_open"

    def __init__(self, use_fixture: bool = False):
        self._use_fixture = use_fixture
        self._source = "hyperliquid_fixture" if use_fixture else "hyperliquid_public_api"

    def get_snapshot(
        self, symbol: str, requested_time_iso: str,
        interval: str = "15m", max_lag_seconds: int = HL_LAG_MAX_S,
    ) -> tuple[PriceSnapshot, dict]:
        info: dict = {"selection_policy": self.selection_policy, "precision_seconds": self.precision_seconds,
                       "signed_lag_seconds": None, "absolute_lag_seconds": None}
        req_ms = iso_to_ms(requested_time_iso)
        if req_ms is None:
            return PriceSnapshot(symbol=symbol, status="unavailable",
                                 requested_time=requested_time_iso, source=self.provider_name,
                                 error_reason=f"invalid_time: '{requested_time_iso}'"), info
        raw = self._fetch_raw(symbol, req_ms)
        if raw is None:
            return PriceSnapshot(symbol=symbol, status="unavailable",
                                 requested_time=requested_time_iso, source=self.provider_name,
                                 error_reason="hl_api_failed"), info
        candles = parse_hl_candles(raw)
        if not candles:
            return PriceSnapshot(symbol=symbol, status="unavailable",
                                 requested_time=requested_time_iso, source=self.provider_name,
                                 error_reason="no_valid_hl_candles"), info
        best, sel_info = select_nearest_candle(candles, req_ms, max_lag_seconds)
        info.update(sel_info)
        if best is None:
            return PriceSnapshot(symbol=symbol, status="unavailable",
                                 requested_time=requested_time_iso, source=self._source,
                                 error_reason=sel_info.get("error_reason", "no_candle")), info
        return PriceSnapshot(symbol=symbol, price=best.open, status="completed",
                             requested_time=requested_time_iso,
                             actual_kline_open_time=ms_to_iso(best.open_time_ms),
                             lag_seconds=info["absolute_lag_seconds"], source=self._source), info

    def _fetch_raw(self, symbol: str, start_ms: int):
        if self._use_fixture:
            return get_hl_candle_fixture()
        payload = {"type": "candleSnapshot", "req": {"coin": symbol, "interval": "15m",
                   "startTime": start_ms, "endTime": start_ms + 3600000}}
        r = _hl_post(payload)
        return r if isinstance(r, list) else None


# ── Router ──────────────────────────────────────────────────────────────────


class ProviderRouter:
    def __init__(self, binance_provider=None, hyperliquid_provider=None):
        self.binance = binance_provider or BinanceProvider()
        self.hyperliquid = hyperliquid_provider or HyperliquidCandleProvider()

    def get_provider(self, asset: str):
        u = asset.strip().upper()
        if u == "HYPE":
            return self.hyperliquid, "hyperliquid", "15m"
        _, supported = map_symbol(u)
        if supported:
            return self.binance, "binance", "1m"
        return None, "unsupported", ""

    def get_snapshot(self, asset: str, rtime: str):
        p, pname, interval = self.get_provider(asset)
        if p is None:
            return (PriceSnapshot(symbol=asset, status="unavailable", requested_time=rtime,
                                  source="router", error_reason=f"unsupported: '{asset}'"),
                    "unsupported", "", {}, "unsupported_asset")
        try:
            snap, si = p.get_snapshot(asset, rtime, interval)
            return snap, pname, interval, si, snap.error_reason or ""
        except Exception as e:
            return (PriceSnapshot(symbol=asset, status="unavailable", requested_time=rtime,
                                  source=pname, error_reason=f"exception: {type(e).__name__}: {e}"),
                    pname, interval, {}, str(e))


# ── Week 1 Results ──────────────────────────────────────────────────────────


@dataclass
class Week1WindowResult:
    """One observation window: return + target snapshot + benchmark snapshots."""
    window: str
    status: str
    return_decimal: Optional[float] = None
    return_percent: Optional[float] = None

    # Target snapshot at this window
    target_snapshot: Optional[PriceSnapshot] = None
    selection_policy: Optional[str] = None
    precision_seconds: Optional[int] = None
    signed_lag_seconds: Optional[int] = None
    absolute_lag_seconds: Optional[int] = None

    # Benchmark returns (decimal)
    btc_return_decimal: Optional[float] = None
    btc_return_percent: Optional[float] = None
    eth_return_decimal: Optional[float] = None
    eth_return_percent: Optional[float] = None

    # Abnormal returns
    btc_abnormal_return_decimal: Optional[float] = None
    btc_abnormal_return_percent: Optional[float] = None
    eth_abnormal_return_decimal: Optional[float] = None
    eth_abnormal_return_percent: Optional[float] = None

    # Benchmark snapshot provenance
    btc_benchmark_t0_snapshot: Optional[PriceSnapshot] = None
    btc_benchmark_target_snapshot: Optional[PriceSnapshot] = None
    eth_benchmark_t0_snapshot: Optional[PriceSnapshot] = None
    eth_benchmark_target_snapshot: Optional[PriceSnapshot] = None

    def as_dict(self) -> dict:
        d = asdict(self)
        for f in ("target_snapshot", "btc_benchmark_t0_snapshot", "btc_benchmark_target_snapshot",
                   "eth_benchmark_t0_snapshot", "eth_benchmark_target_snapshot"):
            v = getattr(self, f)
            d[f] = v.as_dict() if v else None
        return d


@dataclass
class Week1ObservationResult:
    """One observed-asset price backfill result. No attribution or trading advice."""
    sample_id: str
    result_id: str
    subject_asset: str
    observed_asset: str
    broadcast_time_utc: str
    t0_basis: str  # always "broadcast_time"
    provider: str
    interval: str
    precision_seconds: Optional[int] = None
    selection_policy: Optional[str] = None
    signed_lag_seconds: Optional[int] = None
    t0_snapshot: Optional[PriceSnapshot] = None
    return_1h: Optional[Week1WindowResult] = None
    return_4h: Optional[Week1WindowResult] = None
    return_24h: Optional[Week1WindowResult] = None
    data_origin: str = ""
    network_error: Optional[str] = None
    calculation_version: str = "v1.18-week1-rc"
    calculated_at: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        for f in ("t0_snapshot", "return_1h", "return_4h", "return_24h"):
            v = getattr(self, f)
            d[f] = v.as_dict() if v else None
        return d


# ── Sample Definitions ──────────────────────────────────────────────────────


W1_SAMPLES = [
    {"sid": "w1_001", "subj": "HYPE", "obs": "HYPE", "bt": "2026-05-25T13:02:00Z"},
    {"sid": "w1_002", "subj": "ETH",  "obs": "ETH",  "bt": "2026-05-25T15:19:00Z"},
    {"sid": "w1_003", "subj": "BTC",  "obs": "BTC",  "bt": "2026-05-25T16:12:00Z"},
    {"sid": "w1_004", "subj": "BTC",  "obs": "BTC",  "bt": "2026-05-25T16:12:00Z"},
]
W1_WTI = [
    {"sid": "w1_005", "subj": "WTI", "obs": "BTC", "bt": "2026-05-25T11:34:00Z"},
    {"sid": "w1_005", "subj": "WTI", "obs": "ETH", "bt": "2026-05-25T11:34:00Z"},
]


# ── Main Runner ─────────────────────────────────────────────────────────────


def run_week1(router=None, now_maturity=None) -> list[Week1ObservationResult]:
    """Run all Week 1 observations. Never raises."""
    if router is None:
        router = ProviderRouter()
    now = now_maturity or datetime.now(timezone.utc)
    entries = (
        [{"sid": s["sid"], "subj": s["subj"], "obs": s["obs"], "bt": s["bt"]} for s in W1_SAMPLES]
        + [{"sid": w["sid"], "subj": w["subj"], "obs": w["obs"], "bt": w["bt"]} for w in W1_WTI]
    )
    results = []
    for e in entries:
        sid, subj, obs, bt = e["sid"], e["subj"], e["obs"], e["bt"]
        rid = f"{sid}__{obs}" if sid == "w1_005" else sid
        snap, pname, interval, si, err = router.get_snapshot(obs, bt)
        origin = "network"
        if snap.status != "completed":
            origin = "network_error" if "fixture" not in (snap.source or "") else "fixture"
        prec = 900 if pname == "hyperliquid" else 60 if pname == "binance" else None
        sp = si.get("selection_policy") if isinstance(si, dict) else None
        sl = si.get("signed_lag_seconds") if isinstance(si, dict) else None
        bms = iso_to_ms(bt)
        results.append(Week1ObservationResult(
            sample_id=sid, result_id=rid, subject_asset=subj, observed_asset=obs,
            broadcast_time_utc=bt,
            t0_basis="broadcast_time",  # always this literal string
            provider=pname, interval=interval, precision_seconds=prec,
            selection_policy=sp, signed_lag_seconds=sl,
            t0_snapshot=snap,
            return_1h=_build_window(obs, bt, bms, 3600000, now, router, pname),
            return_4h=_build_window(obs, bt, bms, 14400000, now, router, pname),
            return_24h=_build_window(obs, bt, bms, 86400000, now, router, pname),
            data_origin=origin, network_error=err if err else None,
            calculated_at=utc_now(),
        ))
    return results


# ── Window Builder ──────────────────────────────────────────────────────────


WINDOW_NAMES = {3600000: "1h", 14400000: "4h", 86400000: "24h"}


def _build_window(
    asset: str, bt_iso: str, bt_ms: Optional[int],
    delta_ms: int, now: datetime, router: ProviderRouter, pname_hint: str = "",
) -> Optional[Week1WindowResult]:
    if bt_ms is None:
        return Week1WindowResult(window="?", status="unavailable")
    target_ms = bt_ms + delta_ms
    wname = WINDOW_NAMES.get(delta_ms, "?")
    deadline = datetime.fromtimestamp(target_ms / 1000.0, tz=timezone.utc)
    if deadline > now:
        return Week1WindowResult(window=wname, status="pending")

    # Get target snapshot
    t_iso = ms_to_iso(target_ms)
    tsnap, _, _, tinfo, _ = router.get_snapshot(asset, t_iso)

    # Determine selection info for this window
    sel_policy = tinfo.get("selection_policy") if isinstance(tinfo, dict) else None
    prec = tinfo.get("precision_seconds") if isinstance(tinfo, dict) else (900 if pname_hint == "hyperliquid" else 60)
    signed_lag = tinfo.get("signed_lag_seconds") if isinstance(tinfo, dict) else None
    abs_lag = tinfo.get("absolute_lag_seconds") if isinstance(tinfo, dict) else None

    if tsnap.status != "completed" or tsnap.price is None:
        return Week1WindowResult(
            window=wname, status=tsnap.status,
            target_snapshot=tsnap, selection_policy=sel_policy,
            precision_seconds=prec, signed_lag_seconds=signed_lag, absolute_lag_seconds=abs_lag,
        )

    # Get t0 snapshot for return calculation
    t0s, _, _, _, _ = router.get_snapshot(asset, bt_iso)
    if t0s.status != "completed" or t0s.price is None:
        return Week1WindowResult(window=wname, status="unavailable", target_snapshot=tsnap)

    rd = (tsnap.price / t0s.price) - 1.0
    wr = Week1WindowResult(
        window=wname, status="completed",
        return_decimal=round(rd, 6), return_percent=round(rd * 100.0, 4),
        target_snapshot=tsnap, selection_policy=sel_policy,
        precision_seconds=prec, signed_lag_seconds=signed_lag, absolute_lag_seconds=abs_lag,
    )

    # Benchmark returns + snapshots
    wr.btc_benchmark_t0_snapshot, wr.btc_benchmark_target_snapshot, br = _bm_snapshots(router, "BTC", bt_iso, target_ms)
    wr.eth_benchmark_t0_snapshot, wr.eth_benchmark_target_snapshot, er = _bm_snapshots(router, "ETH", bt_iso, target_ms)

    wr.btc_return_decimal = round(br, 6) if br is not None else None
    wr.btc_return_percent = round(br * 100.0, 4) if br is not None else None
    wr.eth_return_decimal = round(er, 6) if er is not None else None
    wr.eth_return_percent = round(er * 100.0, 4) if er is not None else None

    if is_self_benchmark(asset, "BTCUSDT"):
        wr.btc_abnormal_return_decimal = None
        wr.btc_abnormal_return_percent = None
    elif br is not None:
        v = rd - br
        wr.btc_abnormal_return_decimal = round(v, 6)
        wr.btc_abnormal_return_percent = round(v * 100.0, 4)

    if is_self_benchmark(asset, "ETHUSDT"):
        wr.eth_abnormal_return_decimal = None
        wr.eth_abnormal_return_percent = None
    elif er is not None:
        v = rd - er
        wr.eth_abnormal_return_decimal = round(v, 6)
        wr.eth_abnormal_return_percent = round(v * 100.0, 4)

    return wr


def _bm_snapshots(
    router: ProviderRouter, asset: str, bt_iso: str, target_ms: int,
) -> tuple[Optional[PriceSnapshot], Optional[PriceSnapshot], Optional[float]]:
    """Get benchmark t0 + target snapshots and return.

    Returns (t0_snapshot, target_snapshot, return_decimal).
    """
    t0s, _, _, _, _ = router.get_snapshot(asset, bt_iso)
    if t0s.status != "completed" or t0s.price is None:
        return t0s, None, None
    ts, _, _, _, _ = router.get_snapshot(asset, ms_to_iso(target_ms))
    if ts.status != "completed" or ts.price is None:
        return t0s, ts, None
    return t0s, ts, (ts.price / t0s.price) - 1.0
