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
