"""Week 1 RC — Price Data Provider with run-level snapshot cache.

Hyperliquid 15m: nearest_candle_open (signed lag, max 450 s).
Binance 1m: first candle at/after target (max lag 120 s).
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional, Protocol
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from market_radar.shared.event_price_backfill import (
    PriceSnapshot,
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
        return HLCandle(open_time_ms=open_ms, close_time_ms=int(candle.get("T", 0)),
                        symbol=str(candle.get("s", "")), interval=str(candle.get("i", "")),
                        open=open_p, high=float(candle.get("h", 0)),
                        low=float(candle.get("l", 0)), close=float(candle.get("c", 0)),
                        volume=float(candle.get("v", 0)), trade_count=int(candle.get("n", 0)))
    except (ValueError, TypeError, KeyError):
        return None


def parse_hl_candles(raw: Any) -> list[HLCandle]:
    if not isinstance(raw, list):
        return []
    return [c for c in (parse_hl_candle(x) for x in raw) if c is not None]


def select_nearest_candle(
    candles: list[HLCandle], target_time_ms: int, max_lag_s: int = HL_LAG_MAX_S,
) -> tuple[Optional[HLCandle], dict]:
    info: dict = {"selection_policy": "nearest_candle_open", "precision_seconds": 900,
                   "signed_lag_seconds": None, "absolute_lag_seconds": None, "error_reason": None}
    if not candles:
        info["error_reason"] = "no_candles_available"
        return None, info
    best: Optional[HLCandle] = None
    best_abs: Optional[int] = None
    for c in candles:
        signed = c.open_time_ms - target_time_ms
        a = abs(signed)
        if a > max_lag_s * 1000:
            continue
        if best is None or a < best_abs:
            best = c; best_abs = a
        elif a == best_abs and c.open_time_ms < best.open_time_ms:
            best = c
    if best is None:
        n = min(candles, key=lambda c: abs(c.open_time_ms - target_time_ms))
        sl = int((n.open_time_ms - target_time_ms) / 1000)
        info.update({"signed_lag_seconds": sl, "absolute_lag_seconds": abs(sl),
                      "error_reason": f"max_lag_exceeded: nearest at {ms_to_iso(n.open_time_ms)}, "
                                      f"abs_lag={abs(sl)}s > max={max_lag_s}s"})
        return None, info
    sl = int((best.open_time_ms - target_time_ms) / 1000)
    info["signed_lag_seconds"] = sl
    info["absolute_lag_seconds"] = abs(sl)
    return best, info


def get_hl_candle_fixture() -> list[dict]:
    b = 1779714000000
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

    def get_snapshot(self, symbol: str, requested_time_iso: str,
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
                                 error_reason=f"invalid_time"), info
        kline, source, net_err, sel_err = self._backfill._fetch_target_kline(mapped, event_ms, "snapshot")
        snap = self._kline_snapshot(mapped, kline, requested_time_iso, source, event_ms,
                                     max_lag_seconds, sel_err, net_err)
        if kline and len(kline) >= 2:
            sl = int((int(kline[0]) - event_ms) / 1000)
            info["signed_lag_seconds"] = sl; info["absolute_lag_seconds"] = abs(sl)
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

    def get_snapshot(self, symbol: str, requested_time_iso: str,
                     interval: str = "15m", max_lag_seconds: int = HL_LAG_MAX_S,
                     ) -> tuple[PriceSnapshot, dict]:
        info: dict = {"selection_policy": self.selection_policy, "precision_seconds": self.precision_seconds,
                       "signed_lag_seconds": None, "absolute_lag_seconds": None}
        req_ms = iso_to_ms(requested_time_iso)
        if req_ms is None:
            return PriceSnapshot(symbol=symbol, status="unavailable",
                                 requested_time=requested_time_iso, source=self.provider_name,
                                 error_reason=f"invalid_time"), info
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
                                  source="router", error_reason=f"unsupported"), "", "", {}, "")
        try:
            snap, si = p.get_snapshot(asset, rtime, interval)
            return snap, pname, interval, si, snap.error_reason or ""
        except Exception as e:
            return (PriceSnapshot(symbol=asset, status="unavailable", requested_time=rtime,
                                  source=pname, error_reason=f"exception: {type(e).__name__}: {e}"),
                    pname, interval, {}, str(e))


# ── Run-level Snapshot Cache ────────────────────────────────────────────────


def make_cache_key(provider: str, symbol: str, time_iso: str,
                   interval: str, policy: str) -> str:
    """Stable human-readable cache key."""
    return f"{provider}:{symbol}:{time_iso}:{interval}:{policy}"


def make_price_observation_key(provider: str, symbol: str, time_iso: str,
                                interval: str, policy: str) -> str:
    """Stable hash-based observation key for dedup detection."""
    raw = f"{provider}|{symbol}|{time_iso}|{interval}|{policy}"
    return "obs:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


class SnapshotCache:
    """Run-level cache for price snapshots. One instance per run_week1() call."""

    def __init__(self, router: ProviderRouter):
        self._router = router
        self._store: dict[str, tuple[PriceSnapshot, str, str, dict, str]] = {}

    def get(self, asset: str, time_iso: str) -> tuple[PriceSnapshot, str, str, dict, str]:
        """Get or fetch a snapshot. Cache keyed on (provider, symbol, time, interval, policy)."""
        p, pname, interval = self._router.get_provider(asset)
        policy = getattr(p, "selection_policy", "") if p else ""
        mapped_asset = asset
        if pname == "binance":
            mapped_asset, _ = map_symbol(asset)
        key = make_cache_key(pname, mapped_asset, time_iso, interval, policy)

        if key in self._store:
            snap, pn, iv, si, err = self._store[key]
            return deepcopy(snap), pn, iv, dict(si), err

        snap, pn, iv, si, err = self._router.get_snapshot(asset, time_iso)
        self._store[key] = (deepcopy(snap), pn, iv, dict(si), err)
        return snap, pn, iv, si, err

    def get_benchmark(self, asset: str, time_iso: str, pname_hint: str = "",
                      ) -> tuple[PriceSnapshot, str, str, dict, str]:
        """Get benchmark snapshot (always uses 'binance'/'1m'/'first_after_target')."""
        return self.get(asset, time_iso)


# ── PriceObservationBundle ──────────────────────────────────────────────────


@dataclass
class PriceObservationBundle:
    """All snapshots needed for one observation, fetched at most once per unique key."""
    key: str
    price_observation_key: str
    asset_t0: Optional[PriceSnapshot] = None
    asset_1h: Optional[PriceSnapshot] = None
    asset_4h: Optional[PriceSnapshot] = None
    asset_24h: Optional[PriceSnapshot] = None
    btc_t0: Optional[PriceSnapshot] = None
    btc_1h: Optional[PriceSnapshot] = None
    btc_4h: Optional[PriceSnapshot] = None
    btc_24h: Optional[PriceSnapshot] = None
    eth_t0: Optional[PriceSnapshot] = None
    eth_1h: Optional[PriceSnapshot] = None
    eth_4h: Optional[PriceSnapshot] = None
    eth_24h: Optional[PriceSnapshot] = None


def fetch_bundle(cache: SnapshotCache, asset: str, bt_iso: str,
                 pname: str, interval: str, policy: str) -> PriceObservationBundle:
    """Fetch all snapshots for an observation in a single pass.

    Returns bundle with all 12 snapshots. Each may be completed or unavailable.
    """
    key = make_cache_key(pname, asset, bt_iso, interval, policy)
    pok = make_price_observation_key(pname, asset, bt_iso, interval, policy)
    bundle = PriceObservationBundle(key=key, price_observation_key=pok)

    bt_ms = iso_to_ms(bt_iso)
    bundle.asset_t0, _, _, _, _ = cache.get(asset, bt_iso)
    bundle.btc_t0, _, _, _, _ = cache.get_benchmark("BTC", bt_iso)
    bundle.eth_t0, _, _, _, _ = cache.get_benchmark("ETH", bt_iso)

    for wname, delta_ms in [("asset_1h", 3600000), ("asset_4h", 14400000), ("asset_24h", 86400000)]:
        if bt_ms:
            t_iso = ms_to_iso(bt_ms + delta_ms)
            snap, _, _, _, _ = cache.get(asset, t_iso)
            setattr(bundle, wname, snap)

    for wname, delta_ms in [("btc_1h", 3600000), ("btc_4h", 14400000), ("btc_24h", 86400000)]:
        if bt_ms:
            t_iso = ms_to_iso(bt_ms + delta_ms)
            snap, _, _, _, _ = cache.get_benchmark("BTC", t_iso)
            setattr(bundle, wname, snap)

    for wname, delta_ms in [("eth_1h", 3600000), ("eth_4h", 14400000), ("eth_24h", 86400000)]:
        if bt_ms:
            t_iso = ms_to_iso(bt_ms + delta_ms)
            snap, _, _, _, _ = cache.get_benchmark("ETH", t_iso)
            setattr(bundle, wname, snap)

    return bundle


# ── Week 1 Result Types ─────────────────────────────────────────────────────


@dataclass
class Week1WindowResult:
    window: str; status: str
    return_decimal: Optional[float] = None; return_percent: Optional[float] = None
    target_snapshot: Optional[PriceSnapshot] = None
    selection_policy: Optional[str] = None; precision_seconds: Optional[int] = None
    signed_lag_seconds: Optional[int] = None; absolute_lag_seconds: Optional[int] = None
    btc_return_decimal: Optional[float] = None; btc_return_percent: Optional[float] = None
    eth_return_decimal: Optional[float] = None; eth_return_percent: Optional[float] = None
    btc_abnormal_return_decimal: Optional[float] = None; btc_abnormal_return_percent: Optional[float] = None
    eth_abnormal_return_decimal: Optional[float] = None; eth_abnormal_return_percent: Optional[float] = None
    btc_benchmark_t0_snapshot: Optional[PriceSnapshot] = None
    btc_benchmark_target_snapshot: Optional[PriceSnapshot] = None
    eth_benchmark_t0_snapshot: Optional[PriceSnapshot] = None
    eth_benchmark_target_snapshot: Optional[PriceSnapshot] = None

    def as_dict(self) -> dict:
        d = asdict(self)
        for f in ("target_snapshot", "btc_benchmark_t0_snapshot", "btc_benchmark_target_snapshot",
                   "eth_benchmark_t0_snapshot", "eth_benchmark_target_snapshot"):
            v = getattr(self, f); d[f] = v.as_dict() if v else None
        return d


@dataclass
class Week1ObservationResult:
    sample_id: str; result_id: str; subject_asset: str; observed_asset: str
    broadcast_time_utc: str; t0_basis: str
    provider: str; interval: str
    precision_seconds: Optional[int] = None; selection_policy: Optional[str] = None
    signed_lag_seconds: Optional[int] = None
    price_observation_key: str = ""
    observation_reused: bool = False
    reused_from_result_id: Optional[str] = None
    t0_snapshot: Optional[PriceSnapshot] = None
    return_1h: Optional[Week1WindowResult] = None; return_4h: Optional[Week1WindowResult] = None
    return_24h: Optional[Week1WindowResult] = None
    data_origin: str = ""; network_error: Optional[str] = None
    calculation_version: str = "v1.18-week1-rc"; calculated_at: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        for f in ("t0_snapshot", "return_1h", "return_4h", "return_24h"):
            v = getattr(self, f); d[f] = v.as_dict() if v else None
        return d


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


# ── Window Builder (pure computation from bundle) ──────────────────────────


def _compute_windows(bundle: PriceObservationBundle, asset: str, now: datetime,
                     ) -> tuple[Optional[Week1WindowResult], Optional[Week1WindowResult],
                                Optional[Week1WindowResult]]:
    """Compute 1h/4h/24h returns purely from bundle snapshots.

    Each window uses the same asset_t0 and benchmark_t0 from the bundle,
    never making additional network calls.
    """
    t0 = bundle.asset_t0
    if t0 is None or t0.status != "completed" or t0.price is None:
        return (None, None, None)

    windows: list[Optional[Week1WindowResult]] = []
    for wname, delta_s, asset_snap, btc_snap, eth_snap in [
        ("1h", 3600, bundle.asset_1h, bundle.btc_1h, bundle.eth_1h),
        ("4h", 14400, bundle.asset_4h, bundle.btc_4h, bundle.eth_4h),
        ("24h", 86400, bundle.asset_24h, bundle.btc_24h, bundle.eth_24h),
    ]:
        target_ms = iso_to_ms(t0.requested_time)
        if target_ms:
            target_ms += delta_s * 1000
            deadline = datetime.fromtimestamp(target_ms / 1000.0, tz=timezone.utc)
        else:
            deadline = datetime.min.replace(tzinfo=timezone.utc)

        if deadline > now:
            windows.append(Week1WindowResult(window=wname, status="pending"))
            continue

        if asset_snap is None or asset_snap.status != "completed" or asset_snap.price is None:
            windows.append(Week1WindowResult(window=wname, status="unavailable",
                                             target_snapshot=asset_snap))
            continue

        rd = (asset_snap.price / t0.price) - 1.0
        wr = Week1WindowResult(window=wname, status="completed", target_snapshot=asset_snap,
                               return_decimal=round(rd, 6), return_percent=round(rd * 100.0, 4))

        # Benchmark returns
        br = _safe_return(btc_snap, bundle.btc_t0) if btc_snap and bundle.btc_t0 else None
        er = _safe_return(eth_snap, bundle.eth_t0) if eth_snap and bundle.eth_t0 else None
        wr.btc_return_decimal = round(br, 6) if br is not None else None
        wr.btc_return_percent = round(br * 100.0, 4) if br is not None else None
        wr.eth_return_decimal = round(er, 6) if er is not None else None
        wr.eth_return_percent = round(er * 100.0, 4) if er is not None else None
        wr.btc_benchmark_t0_snapshot = bundle.btc_t0
        wr.btc_benchmark_target_snapshot = btc_snap
        wr.eth_benchmark_t0_snapshot = bundle.eth_t0
        wr.eth_benchmark_target_snapshot = eth_snap

        if is_self_benchmark(asset, "BTCUSDT"):
            wr.btc_abnormal_return_decimal = None; wr.btc_abnormal_return_percent = None
        elif br is not None:
            v = rd - br
            wr.btc_abnormal_return_decimal = round(v, 6); wr.btc_abnormal_return_percent = round(v * 100.0, 4)

        if is_self_benchmark(asset, "ETHUSDT"):
            wr.eth_abnormal_return_decimal = None; wr.eth_abnormal_return_percent = None
        elif er is not None:
            v = rd - er
            wr.eth_abnormal_return_decimal = round(v, 6); wr.eth_abnormal_return_percent = round(v * 100.0, 4)

        windows.append(wr)

    return tuple(windows)  # type: ignore


def _safe_return(snap: Optional[PriceSnapshot], t0_snap: Optional[PriceSnapshot]) -> Optional[float]:
    if snap is None or t0_snap is None or snap.price is None or t0_snap.price is None or t0_snap.price == 0:
        return None
    if snap.status != "completed" or t0_snap.status != "completed":
        return None
    return (snap.price / t0_snap.price) - 1.0


# ── Main Runner ─────────────────────────────────────────────────────────────


def run_week1(router=None, now_maturity=None) -> list[Week1ObservationResult]:
    """Run all Week 1 observations with run-level snapshot cache.

    Observations sharing the same price_observation_key are computed once
    and the result is reused without additional network calls.
    """
    if router is None:
        router = ProviderRouter()
    cache = SnapshotCache(router)
    now = now_maturity or datetime.now(timezone.utc)
    bundle_cache: dict[str, tuple[PriceObservationBundle, list[Week1ObservationResult]]] = {}
    entries = (
        [{"sid": s["sid"], "subj": s["subj"], "obs": s["obs"], "bt": s["bt"]} for s in W1_SAMPLES]
        + [{"sid": w["sid"], "subj": w["subj"], "obs": w["obs"], "bt": w["bt"]} for w in W1_WTI]
    )

    def _finish_entry(sid, subj, obs, bt, pname, interval, snap, bundle, reused_from=None):
        rid = f"{sid}__{obs}" if sid == "w1_005" else sid
        origin = "network"
        if snap.status != "completed":
            origin = "network_error" if "fixture" not in (snap.source or "") else "fixture"
        w1, w4, w24 = _compute_windows(bundle, obs, now)
        return Week1ObservationResult(
            sample_id=sid, result_id=rid, subject_asset=subj, observed_asset=obs,
            broadcast_time_utc=bt, t0_basis="broadcast_time",
            provider=pname, interval=interval,
            precision_seconds=900 if pname == "hyperliquid" else 60 if pname == "binance" else None,
            selection_policy=getattr(router.get_provider(obs)[0], "selection_policy", None),
            signed_lag_seconds=None,
            price_observation_key=bundle.price_observation_key,
            observation_reused=reused_from is not None,
            reused_from_result_id=reused_from,
            t0_snapshot=snap,
            return_1h=w1, return_4h=w4, return_24h=w24,
            data_origin=origin, network_error=snap.error_reason or None,
            calculated_at=utc_now(),
        )

    results = []
    for e in entries:
        sid, subj, obs, bt = e["sid"], e["subj"], e["obs"], e["bt"]
        p, pname, interval = router.get_provider(obs)
        policy = getattr(p, "selection_policy", "") if p else ""
        mapped = obs
        if pname == "binance":
            mapped, _ = map_symbol(obs)
        pok = make_price_observation_key(pname, mapped, bt, interval, policy)

        if pok in bundle_cache:
            # Reuse existing bundle
            existing_bundle, existing_results = bundle_cache[pok]
            for er in existing_results:
                r = _finish_entry(sid, subj, obs, bt, pname, interval,
                                  er.t0_snapshot, existing_bundle, reused_from=er.result_id)
                results.append(r)
                break
            continue

        bt_ms = iso_to_ms(bt)
        bundle = fetch_bundle(cache, obs, bt, pname, interval, policy)
        snap = bundle.asset_t0
        r = _finish_entry(sid, subj, obs, bt, pname, interval, snap, bundle)
        bundle_cache[pok] = (bundle, [r])
        results.append(r)

    return results
