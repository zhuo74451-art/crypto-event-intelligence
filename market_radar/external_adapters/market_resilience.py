"""Multi-exchange market resilience — cross-venue snapshot, fallback, anomaly detection.

Read-only: uses CcxtPublicMarketAdapter and HyperliquidPublicAdapter.
No credentials, no wallet, no orders.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from statistics import median
from typing import Any, Optional

from market_radar.external_adapters.ccxt_public_market_adapter import (
    CcxtPublicMarketAdapter, ALLOWLISTED_EXCHANGES,
)
from market_radar.external_adapters.hyperliquid_public_adapter import (
    HyperliquidPublicAdapter,
)
from market_radar.external_adapters.adapter_models import AdapterResult


# ── Constants ──

SUPPORTED_VENUES = {"binance", "okx", "bybit", "hyperliquid"}
MAX_RETRIES_PER_VENUE = 2
TIMEOUT_PER_REQUEST = 15.0

# ── Anomaly thresholds ──
MAX_DISPERSION_BPS = 50       # 0.5%
MAX_SPREAD_BPS = 20           # 0.2%
STALE_AGE_SECONDS = 300       # 5 minutes
MIN_HEALTHY_VENUES_CONSENSUS = 2


# ═══════════════════════════════════════════════════════════════════
# Capability Matrix
# ═══════════════════════════════════════════════════════════════════

class Capability(str):
    """Marker type for capability strings."""

# Standard capability keys
CAP_SPOT_TICKER = "spot_ticker"
CAP_PERP_TICKER = "perp_ticker"
CAP_VOLUME_24H = "volume_24h"
CAP_OPEN_INTEREST = "open_interest"
CAP_FUNDING_RATE = "funding_rate"
CAP_NEXT_FUNDING_TIME = "next_funding_time"
CAP_MARK_PRICE = "mark_price"
CAP_INDEX_PRICE = "index_price"
CAP_BASIS = "basis"
CAP_ORDER_BOOK_TOP = "order_book_top"

CapabilityValue = str  # "supported" | "unsupported" | "unavailable" | "degraded" | "unknown"

# Known capabilities per venue
KNOWN_CAPABILITIES: dict[str, dict[str, CapabilityValue]] = {
    "binance": {
        CAP_SPOT_TICKER: "supported",
        CAP_PERP_TICKER: "supported",
        CAP_VOLUME_24H: "supported",
        CAP_OPEN_INTEREST: "supported",
        CAP_FUNDING_RATE: "supported",
        CAP_NEXT_FUNDING_TIME: "supported",
        CAP_MARK_PRICE: "supported",
        CAP_INDEX_PRICE: "supported",
        CAP_BASIS: "supported",
        CAP_ORDER_BOOK_TOP: "supported",
    },
    "okx": {
        CAP_SPOT_TICKER: "supported",
        CAP_PERP_TICKER: "supported",
        CAP_VOLUME_24H: "supported",
        CAP_OPEN_INTEREST: "supported",
        CAP_FUNDING_RATE: "supported",
        CAP_NEXT_FUNDING_TIME: "supported",
        CAP_MARK_PRICE: "supported",
        CAP_INDEX_PRICE: "supported",
        CAP_BASIS: "supported",
        CAP_ORDER_BOOK_TOP: "supported",
    },
    "bybit": {
        CAP_SPOT_TICKER: "supported",
        CAP_PERP_TICKER: "supported",
        CAP_VOLUME_24H: "supported",
        CAP_OPEN_INTEREST: "supported",
        CAP_FUNDING_RATE: "supported",
        CAP_NEXT_FUNDING_TIME: "supported",
        CAP_MARK_PRICE: "supported",
        CAP_INDEX_PRICE: "supported",
        CAP_BASIS: "supported",
        CAP_ORDER_BOOK_TOP: "supported",
    },
    "hyperliquid": {
        CAP_SPOT_TICKER: "unsupported",
        CAP_PERP_TICKER: "supported",
        CAP_VOLUME_24H: "unsupported",
        CAP_OPEN_INTEREST: "unsupported",
        CAP_FUNDING_RATE: "supported",
        CAP_NEXT_FUNDING_TIME: "unsupported",
        CAP_MARK_PRICE: "supported",
        CAP_INDEX_PRICE: "unsupported",
        CAP_BASIS: "unsupported",
        CAP_ORDER_BOOK_TOP: "unsupported",
    },
}


def get_venue_capabilities(venue: str) -> dict[str, CapabilityValue]:
    """Return known capability for a venue (or all unknown if unlisted)."""
    return dict(KNOWN_CAPABILITIES.get(venue, {
        k: "unknown" for k in KNOWN_CAPABILITIES.get("binance", {})
    }))


def get_supported_count(venue: str) -> int:
    caps = get_venue_capabilities(venue)
    return sum(1 for v in caps.values() if v == "supported")


# ═══════════════════════════════════════════════════════════════════
# MarketVenueSnapshot — single venue per symbol
# ═══════════════════════════════════════════════════════════════════

@dataclass
class MarketVenueSnapshot:
    """Normalized snapshot from a single venue."""
    venue: str
    symbol: str
    market_type: str  # "spot" | "perp" | "unknown"
    timestamp: str
    last: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    mark: Optional[float] = None
    index: Optional[float] = None
    spot_reference: Optional[float] = None
    basis_absolute: Optional[float] = None
    basis_bps: Optional[float] = None
    volume_24h: Optional[float] = None
    open_interest: Optional[float] = None
    open_interest_usd: Optional[float] = None
    funding_rate: Optional[float] = None
    next_funding_at: Optional[str] = None
    data_age_ms: Optional[float] = None
    fields_available: list[str] = field(default_factory=list)
    fields_missing: list[str] = field(default_factory=list)
    status: str = "ok"
    errors: list[str] = field(default_factory=list)
    provenance: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in asdict(self).items() if v is not None}
        if not self.errors:
            d.pop("errors", None)
        if not self.fields_available:
            d.pop("fields_available", None)
        if not self.fields_missing:
            d.pop("fields_missing", None)
        return d


# ═══════════════════════════════════════════════════════════════════
# CrossVenueMarketSnapshot — aggregated
# ═══════════════════════════════════════════════════════════════════

@dataclass
class CrossVenueMarketSnapshot:
    """Cross-venue aggregated market snapshot."""
    symbol: str
    venue_snapshots: list[MarketVenueSnapshot] = field(default_factory=list)
    median_price: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    dispersion_bps: Optional[float] = None
    venue_count: int = 0
    healthy_venue_count: int = 0
    stale_venue_count: int = 0
    funding_median: Optional[float] = None
    funding_range: Optional[float] = None
    oi_total: Optional[float] = None
    basis_median: Optional[float] = None
    outliers: list[str] = field(default_factory=list)
    consensus_status: str = "unknown"  # "ok" | "degraded" | "unavailable"
    generated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in asdict(self).items() if v is not None}
        d["venue_snapshots"] = [v.as_dict() for v in self.venue_snapshots]
        if not self.outliers:
            d.pop("outliers", None)
        return d

    @property
    def has_consensus(self) -> bool:
        return self.consensus_status == "ok" and self.healthy_venue_count >= MIN_HEALTHY_VENUES_CONSENSUS


# ═══════════════════════════════════════════════════════════════════
# Resilience utilities
# ═══════════════════════════════════════════════════════════════════

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _coalesce_float(*vals: Any) -> Optional[float]:
    for v in vals:
        if v is not None:
            try:
                f = float(v)
                if f == f and f != float("inf") and f != float("-inf"):
                    return f
            except (ValueError, TypeError):
                pass
    return None


def detect_anomalies(snapshot: CrossVenueMarketSnapshot) -> list[str]:
    """Detect anomalies across venue snapshots. Returns anomaly descriptions."""
    anomalies: list[str] = []
    if not snapshot.venue_snapshots:
        return ["no_venue_data"]

    prices = [v.last for v in snapshot.venue_snapshots if v.last is not None]
    if len(prices) >= 2:
        pmin, pmax = min(prices), max(prices)
        if pmin > 0:
            disp = (pmax - pmin) / pmin * 10000
            if disp > MAX_DISPERSION_BPS:
                anomalies.append(f"cross_venue_dispersion:{disp:.0f}bps")

    for v in snapshot.venue_snapshots:
        if v.data_age_ms is not None and v.data_age_ms > STALE_AGE_SECONDS * 1000:
            anomalies.append(f"stale:{v.venue}")
        if v.bid is not None and v.ask is not None and v.bid > 0:
            spread = (v.ask - v.bid) / v.bid * 10000
            if spread > MAX_SPREAD_BPS:
                anomalies.append(f"wide_spread:{v.venue}:{spread:.0f}bps")
        if v.last is not None and v.last <= 0:
            anomalies.append(f"zero_price:{v.venue}")
        if v.funding_rate is not None:
            fr_abs = abs(v.funding_rate)
            if fr_abs > 0.01:
                anomalies.append(f"high_funding:{v.venue}:{v.funding_rate}")

    # Funding divergence
    frates = [v.funding_rate for v in snapshot.venue_snapshots
              if v.funding_rate is not None]
    if len(frates) >= 2:
        fr_min, fr_max = min(frates), max(frates)
        if abs(fr_max - fr_min) > 0.0005:
            anomalies.append(f"funding_divergence:{fr_max - fr_min}")

    return anomalies


def fallback_order(configured_venues: list[str]) -> list[str]:
    """Return venue list in fallback priority:
    1. Configured order, 2. Healthy known venues, 3. Stable default order.
    """
    default = ["binance", "okx", "bybit", "hyperliquid"]
    seen = set()
    result = []
    for v in configured_venues + default:
        if v not in seen:
            seen.add(v)
            result.append(v)
    return result


# ═══════════════════════════════════════════════════════════════════
# Multi-venue fetcher
# ═══════════════════════════════════════════════════════════════════

def fetch_cross_venue_snapshot(
    symbols: list[str],
    venues: Optional[list[str]] = None,
    exchange_timeout: float = TIMEOUT_PER_REQUEST,
) -> dict[str, CrossVenueMarketSnapshot]:
    """Fetch market data from multiple venues and aggregate.

    Returns dict of {symbol: CrossVenueMarketSnapshot}.
    Each venue is independent — one failure does not block others.
    """
    from market_radar.external_adapters.ccxt_public_market_adapter import CcxtPublicMarketAdapter
    from market_radar.external_adapters.hyperliquid_public_adapter import HyperliquidPublicAdapter

    if venues is None:
        venues = ["binance", "okx", "bybit"]

    ccxt_adapters: dict[str, CcxtPublicMarketAdapter] = {}
    hl_adapter: Optional[HyperliquidPublicAdapter] = None
    try:
        for v in venues:
            if v.lower() == "hyperliquid":
                hl_adapter = HyperliquidPublicAdapter()
            else:
                ccxt_adapters[v] = CcxtPublicMarketAdapter(exchange_timeout=exchange_timeout)

        # Fetch HL allMids once for all HL symbols
        hl_mids: dict[str, float] = {}
        if hl_adapter is not None:
            try:
                r = hl_adapter.fetch_all_mids()
                if r.ok and isinstance(r.data, dict):
                    hl_mids = {k: _coalesce_float(v) for k, v in r.data.items()
                              if _coalesce_float(v) is not None}
            except Exception:
                pass

        # Build per-symbol results
        results: dict[str, CrossVenueMarketSnapshot] = {}
        for symbol in symbols:
            snapshots: list[MarketVenueSnapshot] = []
            base = symbol.replace("/USDT", "").split("/")[0] if "/" in symbol else symbol

            # CCXT venues
            for venue, ccxt_a in ccxt_adapters.items():
                snap = _fetch_ccxt_venue(ccxt_a, venue, symbol, hl_mids)
                snapshots.append(snap)

            # Hyperliquid venue
            if hl_adapter is not None and base in hl_mids:
                snap = _build_hl_snapshot(base, hl_mids, hl_adapter)
                snapshots.append(snap)
            elif hl_adapter is not None:
                snap = MarketVenueSnapshot(
                    venue="hyperliquid", symbol=base, market_type="perp",
                    timestamp=_utc_now(), status="unavailable",
                    errors=["symbol not found in allMids"],
                    provenance="sdk",
                )
                snapshots.append(snap)

            aggregated = _aggregate_snapshots(symbol, snapshots)
            results[symbol] = aggregated

        return results

    finally:
        for a in ccxt_adapters.values():
            a.close()
        if hl_adapter is not None:
            hl_adapter.close()


def _fetch_ccxt_venue(
    adapter: CcxtPublicMarketAdapter,
    venue: str,
    symbol: str,
    hl_mids: dict[str, float],
) -> MarketVenueSnapshot:
    """Fetch and normalize a single CCXT venue snapshot."""
    start = time.monotonic()
    ts = _utc_now()

    # Ticker
    ticker: Optional[AdapterResult] = None
    try:
        ticker = adapter.fetch(venue, "ticker", symbol, kwargs={"timeout": int(TIMEOUT_PER_REQUEST * 1000)})
    except Exception:
        pass

    elapsed = (time.monotonic() - start) * 1000

    if ticker is None or not ticker.ok:
        err_msg = ticker.error.message if ticker and ticker.error else "ticker fetch failed"
        return MarketVenueSnapshot(
            venue=venue, symbol=symbol, market_type="spot",
            timestamp=ts, status="unavailable",
            errors=[err_msg],
            provenance="ccxt",
        )

    raw = ticker.data if isinstance(ticker.data, dict) else {}
    last = _coalesce_float(raw.get("last"))
    bid = _coalesce_float(raw.get("bid"))
    ask = _coalesce_float(raw.get("ask"))
    volume = _coalesce_float(raw.get("quoteVolume"))
    high = _coalesce_float(raw.get("high"))
    low = _coalesce_float(raw.get("low"))

    # For perp tickers, CCXT provides mark/funding via ticker on some venues
    mark = _coalesce_float(raw.get("markPrice")) or _coalesce_float(raw.get("mark"))
    index = _coalesce_float(raw.get("indexPrice")) or _coalesce_float(raw.get("index"))

    # Basis from spot reference (if mark is available)
    spot_ref = None
    basis_abs = None
    basis_bps = None
    if mark is not None and last is not None and last > 0:
        spot_ref = last
        basis_abs = mark - last
        basis_bps = (basis_abs / last) * 10000

    fields_available = [k for k, v in [
        ("last", last), ("bid", bid), ("ask", ask),
        ("mark", mark), ("index", index),
        ("volume_24h", volume),
    ] if v is not None]

    fields_missing = [k for k, v in [
        ("last", last), ("bid", bid), ("ask", ask),
        ("mark", mark), ("index", index),
        ("volume_24h", volume),
    ] if v is None]

    return MarketVenueSnapshot(
        venue=venue, symbol=symbol, market_type="spot",
        timestamp=ts, last=last, bid=bid, ask=ask,
        mark=mark, index=index, spot_reference=spot_ref,
        basis_absolute=basis_abs, basis_bps=basis_bps,
        volume_24h=volume,
        data_age_ms=round(elapsed, 1),
        fields_available=fields_available,
        fields_missing=fields_missing,
        status="ok",
        provenance="ccxt",
    )


def _build_hl_snapshot(
    base: str,
    hl_mids: dict[str, float],
    hl_adapter: HyperliquidPublicAdapter,
) -> MarketVenueSnapshot:
    """Build a Hyperliquid perp snapshot from allMids data."""
    ts = _utc_now()
    start = time.monotonic()

    price = hl_mids.get(base)
    elapsed = (time.monotonic() - start) * 1000

    if price is None or price <= 0:
        return MarketVenueSnapshot(
            venue="hyperliquid", symbol=base, market_type="perp",
            timestamp=ts, status="unavailable",
            errors=[f"{base} not found in allMids"],
            provenance="sdk",
        )

    # Try to get funding info
    funding_rate: Optional[float] = None
    try:
        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = end_ms - 3600_000
        fr = hl_adapter.fetch_funding_history(base, start_ms, end_ms)
        if fr.ok and isinstance(fr.data, list) and fr.data:
            funding_rate = _coalesce_float(fr.data[0].get("fundingRate"))
    except Exception:
        pass

    fields_avail = ["last", "mark"]
    if funding_rate is not None:
        fields_avail.append("funding_rate")

    return MarketVenueSnapshot(
        venue="hyperliquid", symbol=base, market_type="perp",
        timestamp=ts, last=price, mark=price,
        funding_rate=funding_rate,
        data_age_ms=round(elapsed, 1),
        fields_available=fields_avail,
        fields_missing=["bid", "ask", "volume_24h", "open_interest"],
        status="ok",
        provenance="sdk",
    )


def _aggregate_snapshots(
    symbol: str,
    snapshots: list[MarketVenueSnapshot],
) -> CrossVenueMarketSnapshot:
    """Aggregate venue snapshots into a cross-venue result."""
    ts = _utc_now()
    healthy = [s for s in snapshots if s.status == "ok"]
    stale = [s for s in snapshots if s.status != "ok"]
    stale.extend(s for s in snapshots if s.data_age_ms is not None and s.data_age_ms > STALE_AGE_SECONDS * 1000)

    prices = [s.last for s in healthy if s.last is not None]
    frates = [s.funding_rate for s in healthy if s.funding_rate is not None]
    bases = [s.basis_absolute for s in healthy if s.basis_absolute is not None]
    # OI — only aggregate same-type (spot vs perp)
    perpetuals = [s for s in healthy if s.market_type == "perp"]

    median_price = median(prices) if len(prices) >= 3 else (prices[0] if prices else None)
    min_price = min(prices) if prices else None
    max_price = max(prices) if prices else None

    dispersion_bps = None
    if min_price is not None and max_price is not None and min_price > 0:
        dispersion_bps = (max_price - min_price) / min_price * 10000

    consensus = "ok"
    if len(healthy) == 0:
        consensus = "unavailable"
    elif len(healthy) < MIN_HEALTHY_VENUES_CONSENSUS:
        consensus = "degraded"

    return CrossVenueMarketSnapshot(
        symbol=symbol,
        venue_snapshots=snapshots,
        median_price=median_price,
        min_price=min_price,
        max_price=max_price,
        dispersion_bps=dispersion_bps,
        venue_count=len(snapshots),
        healthy_venue_count=len(healthy),
        stale_venue_count=len(stale) - len([s for s in stale if s not in healthy]),
        funding_median=median(frates) if len(frates) >= 2 else (frates[0] if frates else None),
        funding_range=max(frates) - min(frates) if len(frates) >= 2 else None,
        basis_median=median(bases) if len(bases) >= 2 else (bases[0] if bases else None),
        outliers=[],
        consensus_status=consensus,
        generated_at=ts,
    )


# ═══════════════════════════════════════════════════════════════════
# Fallback fetcher (deterministic, auditable)
# ═══════════════════════════════════════════════════════════════════

def fetch_with_fallback(
    symbol: str,
    preferred_venues: Optional[list[str]] = None,
    exchange_timeout: float = TIMEOUT_PER_REQUEST,
) -> tuple[MarketVenueSnapshot, list[str]]:
    """Fetch *symbol* trying venues in fallback order.

    Returns (snapshot, fallback_chain) where fallback_chain records
    which venues were tried and why.
    """
    order = fallback_order(preferred_venues or [])
    chain: list[str] = []

    for venue in order:
        if venue == "hyperliquid":
            # HL handled separately
            chain.append(f"{venue}:skip_needs_cross_venue")
            continue
        try:
            a = CcxtPublicMarketAdapter(exchange_timeout=exchange_timeout)
            snap = _fetch_ccxt_venue(a, venue, symbol, {})
            a.close()
            chain.append(f"{venue}:{snap.status}")
            if snap.status == "ok":
                return snap, chain
        except Exception as e:
            chain.append(f"{venue}:error:{e}")

    return MarketVenueSnapshot(
        venue="unknown", symbol=symbol, market_type="unknown",
        timestamp=_utc_now(), status="unavailable",
        errors=["all venues exhausted"],
        provenance="fallback",
    ), chain


# ═══════════════════════════════════════════════════════════════════
# Section 1: Independent Field Fetchers
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FieldResult:
    """Result of a single field fetch from one venue."""
    capability: str
    value: Optional[float] = None
    timestamp: str = ""
    age_ms: Optional[float] = None
    status: str = "ok"  # "ok" | "unsupported" | "unavailable" | "error"
    error: Optional[str] = None
    provenance: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def fetch_field_open_interest(
    adapter: CcxtPublicMarketAdapter, venue: str, symbol: str,
    timeout: float = TIMEOUT_PER_REQUEST,
) -> FieldResult:
    """Fetch open interest from a CCXT venue."""
    t0 = time.monotonic()
    try:
        r = adapter.fetch(venue, "open_interest", symbol, kwargs={"timeout": int(timeout * 1000)})
        elapsed = (time.monotonic() - t0) * 1000
        if not r.ok or not isinstance(r.data, dict):
            return FieldResult("open_interest", status="unavailable", timestamp=_utc_now(),
                               age_ms=round(elapsed, 1), error=r.error.message if r.error else "fetch failed",
                               provenance="ccxt")
        oi = _coalesce_float(r.data.get("openInterest"))
        if oi is None:
            return FieldResult("open_interest", status="unavailable", timestamp=_utc_now(),
                               age_ms=round(elapsed, 1), error="openInterest field missing",
                               provenance="ccxt")
        return FieldResult("open_interest", value=oi, timestamp=_utc_now(), age_ms=round(elapsed, 1),
                           provenance="ccxt")
    except Exception as e:
        return FieldResult("open_interest", status="unavailable", timestamp=_utc_now(),
                           error=f"{type(e).__name__}: {e}", provenance="ccxt")


def fetch_field_funding_rate(
    adapter: CcxtPublicMarketAdapter, venue: str, symbol: str,
    timeout: float = TIMEOUT_PER_REQUEST,
) -> FieldResult:
    """Fetch funding rate from a CCXT venue."""
    t0 = time.monotonic()
    try:
        r = adapter.fetch(venue, "funding_rate", symbol, kwargs={"timeout": int(timeout * 1000)})
        elapsed = (time.monotonic() - t0) * 1000
        if not r.ok or not isinstance(r.data, dict):
            return FieldResult("funding_rate", status="unavailable", timestamp=_utc_now(),
                               age_ms=round(elapsed, 1), error=r.error.message if r.error else "fetch failed",
                               provenance="ccxt")
        fr = _coalesce_float(r.data.get("fundingRate"))
        if fr is None:
            return FieldResult("funding_rate", status="unavailable", timestamp=_utc_now(),
                               age_ms=round(elapsed, 1), error="fundingRate field missing",
                               provenance="ccxt")
        return FieldResult("funding_rate", value=fr, timestamp=_utc_now(), age_ms=round(elapsed, 1),
                           provenance="ccxt")
    except Exception as e:
        return FieldResult("funding_rate", status="unavailable", timestamp=_utc_now(),
                           error=f"{type(e).__name__}: {e}", provenance="ccxt")


def fetch_field_order_book_top(
    adapter: CcxtPublicMarketAdapter, venue: str, symbol: str,
    timeout: float = TIMEOUT_PER_REQUEST,
) -> FieldResult:
    """Fetch top-of-order-book bid/ask from a CCXT venue (uses ticker)."""
    # Order book top is available via ticker's bid/ask
    t0 = time.monotonic()
    try:
        r = adapter.fetch(venue, "ticker", symbol, kwargs={"timeout": int(timeout * 1000)})
        elapsed = (time.monotonic() - t0) * 1000
        if not r.ok or not isinstance(r.data, dict):
            return FieldResult("order_book_top", status="unavailable", timestamp=_utc_now(),
                               age_ms=round(elapsed, 1), error=r.error.message if r.error else "fetch failed",
                               provenance="ccxt")
        bid = _coalesce_float(r.data.get("bid"))
        ask = _coalesce_float(r.data.get("ask"))
        if bid is None or ask is None:
            return FieldResult("order_book_top", status="unavailable", timestamp=_utc_now(),
                               age_ms=round(elapsed, 1), error="bid/ask missing",
                               provenance="ccxt")
        return FieldResult("order_book_top", value=(bid + ask) / 2, timestamp=_utc_now(),
                           age_ms=round(elapsed, 1), provenance="ccxt")
    except Exception as e:
        return FieldResult("order_book_top", status="unavailable", timestamp=_utc_now(),
                           error=f"{type(e).__name__}: {e}", provenance="ccxt")


# ═══════════════════════════════════════════════════════════════════
# Section 2: Market Type & Unit Normalization
# ═══════════════════════════════════════════════════════════════════

class MarketType(str):
    """Market type classification."""

MARKET_SPOT = "spot"
MARKET_LINEAR_PERP = "linear_perp"
MARKET_INVERSE_PERP = "inverse_perp"
MARKET_SWAP = "swap"
MARKET_UNKNOWN = "unknown"


def classify_market_type(venue: str, symbol: str) -> str:
    """Classify market type from venue and symbol.

    Rules:
    - Hyperliquid: always linear_perp
    - Binance: USDT-marginated = linear_perp; no suffix = spot
    - OKX: USDT-SWAP = linear_perp; USDT = spot
    - Bybit: USDT = linear_perp; no suffix = spot
    """
    sym_upper = symbol.upper()
    if venue == "hyperliquid":
        return MARKET_LINEAR_PERP
    if "/" in sym_upper:
        base, quote = sym_upper.split("/", 1)
        if quote == "USDT":
            return MARKET_SPOT
    if "USDT" in sym_upper and any(t in sym_upper for t in ("SWAP", "PERP", "LINEAR")):
        return MARKET_LINEAR_PERP
    if "INV" in sym_upper or "INVERSE" in sym_upper:
        return MARKET_INVERSE_PERP
    return MARKET_SPOT


@dataclass
class NormalizedOI:
    """Normalized open interest value with unit metadata."""
    value_usd: Optional[float] = None
    value_contracts: Optional[float] = None
    value_base: Optional[float] = None
    market_type: str = MARKET_UNKNOWN
    unit: str = "usd"  # "usd" | "contracts" | "base" | "incomparable"
    comparable_with: list[str] = field(default_factory=lambda: ["usd"])
    incomparable: bool = False
    incomparable_reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None or k == "incomparable"}


def normalize_oi(
    raw_oi: Optional[float],
    market_type: str,
    price: Optional[float] = None,
    contract_size: Optional[float] = None,
) -> NormalizedOI:
    """Normalize OI to USD notional where possible.

    Spot: OI value is directly USD equivalent.
    Linear perp: OI * contract_size * price → USD (contract_size is often 1).
    Inverse perp: cannot reliably convert without knowing margin currency.
    """
    if raw_oi is None:
        return NormalizedOI(incomparable=True, incomparable_reason="raw OI is None")

    if market_type == MARKET_INVERSE_PERP:
        return NormalizedOI(
            value_contracts=raw_oi, market_type=market_type, unit="contracts",
            incomparable=True,
            incomparable_reason="inverse perp OI requires margin currency conversion",
        )

    if market_type in (MARKET_SPOT, MARKET_LINEAR_PERP, MARKET_SWAP):
        cs = contract_size or 1.0
        if market_type == MARKET_SPOT:
            usd_value = raw_oi * cs
            return NormalizedOI(value_usd=usd_value, value_contracts=raw_oi,
                                market_type=market_type, unit="usd")
        else:
            usd_value = raw_oi * cs * (price or 1.0)
            return NormalizedOI(value_usd=usd_value, value_contracts=raw_oi,
                                market_type=market_type, unit="usd")

    return NormalizedOI(value_contracts=raw_oi, market_type=market_type,
                        incomparable=True,
                        incomparable_reason=f"unknown market type: {market_type}")


def aggregate_oi(snapshots: list[MarketVenueSnapshot]) -> tuple[Optional[float], list[str]]:
    """Aggregate OI across venues where comparable.

    Returns (total_usd, incomparable_venues).
    Skips venues whose OI unit is not comparable (e.g. inverse perp).
    """
    total: Optional[float] = None
    incomparable: list[str] = []
    for s in snapshots:
        if s.open_interest_usd is not None:
            total = (total or 0) + s.open_interest_usd
        elif s.open_interest is not None:
            incomparable.append(f"{s.venue}(oi={s.open_interest},unit=contracts,incomparable)")
    return total, incomparable


# ═══════════════════════════════════════════════════════════════════
# Section 3: Venue Health
# ═══════════════════════════════════════════════════════════════════

@dataclass
class VenueHealthSnapshot:
    """Non-persistent, non-threaded health snapshot for a venue."""
    venue: str
    available: bool = True
    latency_ms: Optional[float] = None
    freshness_ms: Optional[float] = None
    completeness: float = 0.0  # 0.0 - 1.0 fraction of fields available
    consecutive_failures: int = 0
    last_success_utc: str = ""
    last_error_utc: str = ""
    last_error: Optional[str] = None
    capability_coverage: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def compute_venue_health(
    snapshots: list[MarketVenueSnapshot],
    venue: str,
    total_capabilities: int = 10,
) -> VenueHealthSnapshot:
    """Compute health for a venue from its current snapshot batch.

    No threads, no persistence — purely derived from current data.
    """
    venue_snaps = [s for s in snapshots if s.venue == venue]
    if not venue_snaps:
        return VenueHealthSnapshot(venue=venue, available=False,
                                    last_error="no snapshots in batch")

    latest = max(venue_snaps, key=lambda s: s.timestamp)

    caps = get_venue_capabilities(venue)
    supported_count = sum(1 for v in caps.values() if v == "supported")
    fields_present = set()
    for s in venue_snaps:
        fields_present.update(s.fields_available)

    capability_coverage = len(fields_present) / max(supported_count, 1)

    # Completeness: fields_present / expected per snapshot
    expected_fields = {"last", "bid", "ask", "mark"}
    completeness = len(fields_present & expected_fields) / len(expected_fields)

    available = latest.status == "ok"
    return VenueHealthSnapshot(
        venue=venue,
        available=available,
        latency_ms=latest.data_age_ms,
        freshness_ms=latest.data_age_ms,
        completeness=completeness,
        capability_coverage=capability_coverage,
        last_success_utc=latest.timestamp if available else "",
        last_error=next(iter(latest.errors), None) if not available else None,
    )


# ═══════════════════════════════════════════════════════════════════
# Section 4: Health-aware Fallback
# ═══════════════════════════════════════════════════════════════════

@dataclass
class FallbackDecision:
    """Record of a fallback decision with audit trail."""
    chosen_venue: str
    reason: str
    chain: list[str] = field(default_factory=list)
    market_type: str = ""
    field_capability: bool = False
    freshness_ok: bool = False
    completeness_ok: bool = False
    latency_ok: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def health_aware_fallback(
    symbol: str,
    preferred_venues: list[str],
    venue_health: dict[str, VenueHealthSnapshot],
    field: str = "ticker",
) -> tuple[Optional[str], FallbackDecision]:
    """Select best venue based on health metrics.

    Priority:
    1. Preferred venue is healthy
    2. Market type matches
    3. Field capability supported
    4. Fresh enough
    5. High completeness
    6. Low latency
    """
    chain: list[str] = []

    for venue in preferred_venues:
        health = venue_health.get(venue)
        if health is None:
            chain.append(f"{venue}:no_health_data")
            continue
        if not health.available:
            chain.append(f"{venue}:unavailable")
            continue

        caps = get_venue_capabilities(venue)
        cap_key_map = {
            "ticker": CAP_SPOT_TICKER,
            "open_interest": CAP_OPEN_INTEREST,
            "funding_rate": CAP_FUNDING_RATE,
        }
        cap_key = cap_key_map.get(field, CAP_SPOT_TICKER)
        if caps.get(cap_key) != "supported":
            chain.append(f"{venue}:{cap_key}_unsupported")
            continue

        freshness_ok = health.freshness_ms is None or health.freshness_ms < STALE_AGE_SECONDS * 1000
        completeness_ok = health.completeness >= 0.5
        latency_ok = health.latency_ms is None or health.latency_ms < 10000

        decision = FallbackDecision(
            chosen_venue=venue,
            reason=f"healthy preferred venue: {venue}",
            chain=chain,
            field_capability=True,
            freshness_ok=freshness_ok,
            completeness_ok=completeness_ok,
            latency_ok=latency_ok,
        )
        return venue, decision

    chain.append("all_preferred_venues_exhausted")
    return None, FallbackDecision(
        chosen_venue="", reason="no healthy venue available", chain=chain,
    )
