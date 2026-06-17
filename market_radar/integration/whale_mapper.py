"""Whale mapper — Hyperliquid clearinghouseState → W2 WhalePositionInput.

Read-only: uses HyperliquidPublicAdapter.fetch_clearinghouse_state().
No signing, no wallet, no orders.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from market_radar.external_adapters.hyperliquid_public_adapter import (
    HyperliquidPublicAdapter,
)
from market_radar.integration.models import SourceRunStatus, WhaleSnapshotResult

# W2 domain — change/alert/risk logic
from market_radar.whale_domain.models import (
    WhalePositionInput, extract_snapshot, make_position_key,
    dict_to_snapshot, snapshot_to_dict,
)
from market_radar.whale_domain.change_detector import detect_all_changes
from market_radar.whale_domain.alert_candidate import generate_alert_candidates

# W5 operations — snapshot persistence
from market_radar.operations.atomic_json import atomic_write_json


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


def _parse_hl_position(pos: dict, use_legacy_fixture: bool = False) -> Optional[dict]:
    """Parse a single Hyperliquid asset position dict into a normalized dict.

    Hyperliquid LIVE position shape (clearinghouseState, official):
      {
        "type": "oneWay",
        "position": {
          "coin": "BTC",
          "szi": "0.5",
          "entryPx": "50000.0",
          "positionValue": "25500.0",
          "leverage": {"type": "isolated", "value": 5},
          "unrealizedPnl": "500.0",
          "liquidationPx": "45000.0",
          "marginMode": "isolated"
        }
      }

    Legacy fixture shape (may still exist in recorded test data):
      {
        "type": "oneWay",
        "data": { ... same fields ... }
      }

    Priority: position > data when use_legacy_fixture=False (live mode).
    When use_legacy_fixture=True, only check "data" (test backward compat).
    """
    if not isinstance(pos, dict):
        return None

    # Official live shape first (unless explicitly in legacy mode)
    data = None
    if not use_legacy_fixture:
        data = pos.get("position")
    if not isinstance(data, dict):
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


def _inject_mark_prices(
    positions: list[dict],
    all_mids: dict[str, float],
) -> tuple[list[dict], list[dict]]:
    """Inject mark prices from allMids into parsed positions.

    clearinghouseState does NOT guarantee markPx on every position.
    This function fills mark_price from fetch_all_mids() by coin.

    Returns (updated_positions, mapping_errors).
    Each mapping_error is a dict with address, coin, and reason.
    """
    mapping_errors: list[dict] = []
    updated: list[dict] = []

    for pos in positions:
        coin = pos.get("coin", "")
        existing_mark = pos.get("mark_price")

        if existing_mark is not None and existing_mark != 0:
            # Already has a valid mark from clearinghouseState
            updated.append(pos)
            continue

        raw_mid = all_mids.get(coin)
        try:
            mid = float(raw_mid) if raw_mid is not None else None
        except (ValueError, TypeError):
            mid = None

        if mid is not None and mid > 0:
            pos["mark_price"] = mid
            pos["mark_price_source"] = "all_mids"
            updated.append(pos)
        else:
            # No mark available — record mapping error
            mapping_errors.append({
                "address": pos.get("address", ""),
                "coin": coin,
                "reason": f"coin {coin} not found or zero in all_mids",
                "signed_size": pos.get("signed_size"),
            })
            # Keep position but mark_price stays None/tracking missing
            pos["mark_price"] = None
            pos["mark_price_source"] = "missing"
            updated.append(pos)

    return updated, mapping_errors


def _build_w2_input(
    position: dict,
    label: str,
) -> WhalePositionInput:
    """Build a WhalePositionInput from a parsed position dict."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return WhalePositionInput(
        address=position.get("address", ""),
        label=label,
        coin=position.get("coin", ""),
        signed_size=position.get("signed_size", 0.0),
        entry_price=position.get("entry_price", 0.0),
        mark_price=position.get("mark_price") or 0.0,
        position_value_usd=position.get("position_value_usd", 0.0),
        leverage=position.get("leverage", 1.0),
        unrealized_pnl_usd=position.get("unrealized_pnl_usd"),
        liquidation_price=position.get("liquidation_price"),
        snapshot_time_utc=now_utc,
        margin_mode=position.get("margin_mode"),
    )


def _load_previous_snapshots(
    state_dir: Path,
    address: str,
) -> dict[str, dict]:
    """Load previous snapshot state from disk."""
    state_path = state_dir / f"whale_state_{address.lower()}.json"
    if not state_path.exists():
        return {}
    try:
        import json
        with open(str(state_path), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_snapshot_state(
    state_dir: Path,
    address: str,
    snapshots_by_key: dict[str, dict],
) -> None:
    """Atomically write snapshot state to disk."""
    state_path = state_dir / f"whale_state_{address.lower()}.json"
    atomic_write_json(snapshots_by_key, str(state_path))


def run_whale_mapper(
    adapter: HyperliquidPublicAdapter,
    address: str,
    config_timeout: float,
    is_baseline_run: bool = True,
    label: str = "",
    state_dir: Optional[Path] = None,
) -> tuple[WhaleSnapshotResult, SourceRunStatus]:
    """Execute whale mapper: fetch HL state → parse → W2 domain.

    When is_baseline_run=True:
      - Extracts snapshots but suppresses large_new_position alerts.
      - All non-zero positions produce baseline_open_position.

    When is_baseline_run=False:
      - Compares against previous state on disk.
      - Detects increase/reduce/close/reverse via W2 detect_all_changes.
      - Generates alert_candidates via W2 generate_alert_candidates.

    Reads mark prices from clearinghouseState if available, otherwise
    fetches fetch_all_mids() to inject markPx per coin.
    """
    t0 = time.monotonic()

    # First fetch clearinghouse state for raw positions
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

    # Parse raw positions from clearinghouseState
    raw_positions, parse_errors = map_clearinghouse_to_snapshots(address, result.data)

    # If clearinghouseState didn't provide markPx, fetch allMids to inject
    positions_need_marks = any(
        p.get("mark_price") is None or p.get("mark_price") == 0
        for p in raw_positions
    )
    all_mids: dict[str, float] = {}
    if positions_need_marks and raw_positions:
        try:
            mids_result = adapter.fetch_all_mids()
            if mids_result.ok and isinstance(mids_result.data, dict):
                for coin, val in mids_result.data.items():
                    try:
                        all_mids[coin] = float(val)
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass

    # Inject mark prices from all_mids
    marked_positions, mark_errors = _inject_mark_prices(raw_positions, all_mids)
    all_parse_errors = parse_errors + mark_errors

    # Determine overall source health
    has_mapping_failure = any("mapping_error" in str(e) for e in all_parse_errors)
    src_ok = len(all_parse_errors) == 0 or not has_mapping_failure
    src_status_str = "ok" if src_ok else "degraded"
    if not marked_positions and not parse_errors:
        src_status_str = "ok"  # Empty positions is OK

    # ── W2 Domain Processing ──
    w2_inputs = [_build_w2_input(p, label or address[:10]) for p in marked_positions]

    # Load previous snapshots
    previous_snapshots: dict[str, WhaleSnapshot] = {}
    previous_raw: dict[str, dict] = {}
    if state_dir and not is_baseline_run:
        previous_raw = _load_previous_snapshots(state_dir, address)
        for key, snap_dict in previous_raw.items():
            try:
                previous_snapshots[key] = dict_to_snapshot(snap_dict)
            except Exception:
                pass

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Detect changes via W2 domain
    changes = detect_all_changes(
        current_inputs=w2_inputs,
        previous_snapshots=previous_snapshots,
        is_baseline_run=is_baseline_run,
        detected_at_utc=now_utc,
    )

    # Generate alert candidates via W2 domain
    snapshots = [extract_snapshot(inp) for inp in w2_inputs]
    alert_candidates = generate_alert_candidates(
        snapshots=snapshots,
        changes=changes,
        generated_at_utc=now_utc,
    )

    # ── Persist state for next run ──
    if state_dir:
        state_dir.mkdir(parents=True, exist_ok=True)
        new_state: dict[str, dict] = {}
        for snap in snapshots:
            key = make_position_key(snap.address, snap.coin)
            new_state[key] = snapshot_to_dict(snap)
        _save_snapshot_state(state_dir, address, new_state)

    # ── Build results ──
    raw_positions_serializable = [dict(p) for p in marked_positions]
    changes_serializable = [c.to_dict() for c in changes]
    alerts_serializable = [a.to_dict() for a in alert_candidates]

    src_detail_parts = [f"{len(marked_positions)} positions"]
    if all_parse_errors:
        src_detail_parts.append(f"{len(all_parse_errors)} mapping errors")
    if changes:
        src_detail_parts.append(f"{len(changes)} changes")
    if alert_candidates:
        src_detail_parts.append(f"{len(alert_candidates)} alerts")

    src_status = SourceRunStatus(
        source=f"whale:{address[:10]}",
        status=src_status_str,
        ok=len(all_parse_errors) == 0,
        latency_ms=round(elapsed, 1),
        provenance=result.provenance.source if result.provenance else None,
        detail=", ".join(src_detail_parts),
    )

    whale_result = WhaleSnapshotResult(
        address=address,
        ok=len(all_parse_errors) == 0,
        position_count=len(marked_positions),
        positions=raw_positions_serializable,
        changes=changes_serializable,
        alert_candidates=alerts_serializable,
        is_baseline=is_baseline_run,
    )
    if all_parse_errors:
        whale_result.error = f"{len(all_parse_errors)} mapping errors"

    return whale_result, src_status
