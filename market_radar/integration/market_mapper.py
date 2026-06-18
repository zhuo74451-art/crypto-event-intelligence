"""Market mapper — CCXT tickers + Hyperliquid allMids → MarketSnapshotResult.

Read-only: no credentials, no trading.
"""
from __future__ import annotations

import time
from typing import Optional

from market_radar.external_adapters.ccxt_public_market_adapter import (
    CcxtPublicMarketAdapter,
)
from market_radar.external_adapters.hyperliquid_public_adapter import (
    HyperliquidPublicAdapter,
)
from market_radar.integration.models import MarketSnapshotResult, SourceRunStatus


# Assets we track by source
CCXT_SYMBOLS = {"BTC/USDT", "ETH/USDT", "SOL/USDT"}
HYPE_VENUE_SYMBOLS = {"HYPE"}  # HYPE must come from Hyperliquid, not CCXT


def run_ccxt_ticker(
    adapter: CcxtPublicMarketAdapter,
    exchange: str,
    symbol: str,
) -> tuple[MarketSnapshotResult, SourceRunStatus]:
    """Fetch a single ticker via CCXT and normalize."""
    t0 = time.monotonic()
    try:
        result = adapter.fetch(exchange, "ticker", symbol)
        elapsed = (time.monotonic() - t0) * 1000
    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return (
            MarketSnapshotResult(symbol=symbol, source=exchange, ok=False, error=str(e)),
            SourceRunStatus(
                source=f"ccxt:{symbol}", status="unavailable", ok=False,
                latency_ms=round(elapsed, 1), error=str(e),
            ),
        )

    if not result.ok:
        err = result.error.message if result.error else "unknown"
        return (
            MarketSnapshotResult(symbol=symbol, source=exchange, ok=False, error=err),
            SourceRunStatus(
                source=f"ccxt:{symbol}", status="unavailable", ok=False,
                latency_ms=round(elapsed, 1), error=err,
                provenance=result.provenance.source if result.provenance else None,
            ),
        )

    data = result.data if isinstance(result.data, dict) else {}
    last = data.get("last")
    bid = data.get("bid")
    ask = data.get("ask")

    snapshot = MarketSnapshotResult(
        symbol=symbol,
        source=exchange,
        ok=True,
        last_price=float(last) if last is not None else None,
        bid=float(bid) if bid is not None else None,
        ask=float(ask) if ask is not None else None,
        provenance=result.provenance.source if result.provenance else None,
        latency_ms=round(elapsed, 1),
    )

    health_ok = result.health.available if result.health else False
    src_status = SourceRunStatus(
        source=f"ccxt:{symbol}",
        status="ok" if health_ok else "degraded",
        ok=health_ok,
        latency_ms=round(elapsed, 1),
        provenance=result.provenance.source if result.provenance else None,
    )

    return snapshot, src_status


def run_hype_mid(
    adapter: HyperliquidPublicAdapter,
) -> tuple[Optional[MarketSnapshotResult], Optional[SourceRunStatus]]:
    """Fetch HYPE mid price from Hyperliquid allMids."""
    t0 = time.monotonic()
    try:
        result = adapter.fetch_all_mids()
        elapsed = (time.monotonic() - t0) * 1000
    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return None, SourceRunStatus(
            source="hyperliquid:allMids", status="unavailable", ok=False,
            latency_ms=round(elapsed, 1), error=str(e),
        )

    if not result.ok or not isinstance(result.data, dict):
        return None, SourceRunStatus(
            source="hyperliquid:allMids", status="unavailable", ok=False,
            latency_ms=round(elapsed, 1),
            error="no data from allMids",
        )

    hype_mid = result.data.get("HYPE")
    if hype_mid is None:
        return None, SourceRunStatus(
            source="hyperliquid:allMids", status="degraded", ok=False,
            latency_ms=round(elapsed, 1),
            error="HYPE not found in allMids response",
        )

    try:
        hype_price = float(hype_mid)
    except (ValueError, TypeError):
        return None, SourceRunStatus(
            source="hyperliquid:allMids", status="degraded", ok=False,
            latency_ms=round(elapsed, 1),
            error=f"HYPE mid not parseable: {hype_mid!r}",
        )

    snapshot = MarketSnapshotResult(
        symbol="HYPE/USDT",
        source="hyperliquid",
        ok=True,
        last_price=hype_price,
        bid=None,
        ask=None,
        provenance=result.provenance.source if result.provenance else None,
        latency_ms=round(elapsed, 1),
    )

    src_status = SourceRunStatus(
        source="hyperliquid:HYPE",
        status="ok",
        ok=True,
        latency_ms=round(elapsed, 1),
        provenance=result.provenance.source if result.provenance else None,
    )

    return snapshot, src_status


def run_market_snapshot(
    ccxt_adapter: CcxtPublicMarketAdapter,
    hl_adapter: HyperliquidPublicAdapter,
    exchange: str,
) -> tuple[list[MarketSnapshotResult], list[SourceRunStatus]]:
    """Fetch all tracked market assets."""
    snapshots: list[MarketSnapshotResult] = []
    sources: list[SourceRunStatus] = []

    # CCXT symbols
    for symbol in sorted(CCXT_SYMBOLS):
        snap, src = run_ccxt_ticker(ccxt_adapter, exchange, symbol)
        snapshots.append(snap)
        sources.append(src)

    # HYPE from Hyperliquid
    hype_snap, hype_src = run_hype_mid(hl_adapter)
    if hype_snap:
        snapshots.append(hype_snap)
    if hype_src:
        sources.append(hype_src)

    return snapshots, sources
