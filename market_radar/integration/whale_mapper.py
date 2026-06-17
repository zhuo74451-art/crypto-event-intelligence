"""Whale mapper — Hyperliquid clearinghouseState → W2 WhalePositionInput.

Read-only: uses HyperliquidPublicAdapter.fetch_clearinghouse_state().
No signing, no wallet, no orders.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.external_adapters.hyperliquid_public_adapter import (
    HyperliquidPublicAdapter,
)
from market_radar.integration.models import SourceRunStatus, WhaleSnapshotResult


def _safe_float(val: Any) -> Optional[float]:
    """Convert to float or None if invalid."""
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:  # NaN
            return None
        return f
    except (ValueError, TypeError):
        return None


def _parse_hl_position(pos: dict) -> Optional[dict]:
    """Parse a single Hyperliquid asset position dict into a normalized dict.

    Hyperliquid position shape (from clearinghouseState):
      {
        "type": "oneWay",
        "data": {
          "coin": "BTC",
          "szi": "0.5",          # signed size (positive=long)
          "entryPx": "50000.0",
          "markPx": "51000.0",
          "positionValue": "25500.0",
          "leverage": {"type": "isolated", "value": 5, "rawUsd": ...},
          "unrealizedPnl": "500.0",
          "liquidationPx": "45000.0",
          "marginMode": "isolated"
        }
      }
    """
    if not isinstance(pos, dict):
        return None
    data = pos.get("data")
    if not isinstance(data, dict):
        return None

    coin = data.get("coin", "")
    if not coin:
        return None

    signed_size = _safe_float(data.get("szi"))
    if signed_size is None:
        return None

    entry_px = _safe_float(data.get("entryPx"))
    mark_px = _safe_float(data.get("markPx"))
    position_value = _safe_float(data.get("positionValue"))
    unrealized_pnl = _safe_float(data.get("unrealizedPnl"))
    liquidation_px = _safe_float(data.get("liquidationPx"))

    # Extract leverage
    lev_data = data.get("leverage", {})
    if isinstance(lev_data, dict):
        leverage = _safe_float(lev_data.get("value")) or 1.0
    else:
        leverage = _safe_float(lev_data) or 1.0

    return {
        "coin": coin,
        "signed_size": signed_size,
        "entry_price": entry_px,
        "mark_price": mark_px,
        "position_value_usd": position_value,
        "leverage": leverage,
        "unrealized_pnl_usd": unrealized_pnl,
        "liquidation_price": liquidation_px,
        "margin_mode": data.get("marginMode"),
    }


def map_clearinghouse_to_snapshots(
    address: str,
    raw_data: Optional[dict],
) -> tuple[list[dict], list[dict]]:
    """Map Hyperliquid clearinghouseState response to whale position snapshots.

    Returns (positions, validation_errors).
    Invalid/missing fields kept as None — never filled with 0.
    """
    positions: list[dict] = []
    errors: list[dict] = []

    if not isinstance(raw_data, dict):
        return positions, [{"error": "response not a dict", "address": address}]

    asset_positions = raw_data.get("assetPositions")
    if not isinstance(asset_positions, list):
        # Empty positions — valid state
        return positions, []

    for i, pos in enumerate(asset_positions):
        parsed = _parse_hl_position(pos)
        if parsed is None:
            errors.append({"index": i, "error": "failed to parse position", "raw": str(pos)[:200]})
            continue

        # Validate critical fields — keep null where missing, never fill with 0
        snapshot = {
            "address": address,
            "coin": parsed["coin"],
            "signed_size": parsed["signed_size"],
            "entry_price": parsed["entry_price"],
            "mark_price": parsed["mark_price"],
            "position_value_usd": parsed["position_value_usd"],
            "leverage": parsed["leverage"],
            "unrealized_pnl_usd": parsed["unrealized_pnl_usd"],
            "liquidation_price": parsed["liquidation_price"],
            "margin_mode": parsed["margin_mode"],
            "snapshot_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        positions.append(snapshot)

    return positions, errors


def run_whale_mapper(
    adapter: HyperliquidPublicAdapter,
    address: str,
    config_timeout: float,
) -> tuple[WhaleSnapshotResult, SourceRunStatus]:
    """Execute whale mapper: fetch HL state → parse → return snapshots."""
    t0 = time.monotonic()
    try:
        result = adapter.fetch_clearinghouse_state(address)
        elapsed = (time.monotonic() - t0) * 1000
    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return (
            WhaleSnapshotResult(address=address, ok=False, position_count=0, error=str(e)),
            SourceRunStatus(
                source=f"whale:{address[:10]}",
                status="unavailable",
                ok=False,
                latency_ms=round(elapsed, 1),
                error=str(e),
            ),
        )

    if not result.ok:
        err_msg = result.error.message if result.error else "unknown"
        return (
            WhaleSnapshotResult(address=address, ok=False, position_count=0, error=err_msg),
            SourceRunStatus(
                source=f"whale:{address[:10]}",
                status="unavailable",
                ok=False,
                latency_ms=round(elapsed, 1),
                error=err_msg,
                provenance=result.provenance.source if result.provenance else None,
            ),
        )

    positions, parse_errors = map_clearinghouse_to_snapshots(address, result.data)

    health_available = result.health.available if result.health else False
    status = "ok" if result.ok else "unavailable"
    src_status = SourceRunStatus(
        source=f"whale:{address[:10]}",
        status=status,
        ok=result.ok,
        latency_ms=round(elapsed, 1),
        provenance=result.provenance.source if result.provenance else None,
        detail=f"{len(positions)} positions, {len(parse_errors)} parse errors" if parse_errors else None,
    )

    whale_result = WhaleSnapshotResult(
        address=address,
        ok=True,
        position_count=len(positions),
        positions=positions,
        is_baseline=True,  # Integration has no prior state — always baseline
    )
    if parse_errors:
        whale_result.error = f"{len(parse_errors)} positions failed to parse"

    return whale_result, src_status
