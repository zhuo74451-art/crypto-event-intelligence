#!/usr/bin/env python3
"""MVP+ Lane 2 — Whale Position Change & Risk Engine.

Detects position changes between consecutive snapshots:
  open_long, open_short, increase_long, increase_short,
  reduce_long, reduce_short, close_long, close_short,
  flip_long_to_short, flip_short_to_long, liquidation_distance_narrowed

Outputs WhalePositionChange[] matching
contracts/mvpplus/v1/whale_position_change.schema.json.

Also computes risk flags for each position.
"""

from __future__ import annotations

import json
import os
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(__file__, *[os.pardir] * 4))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "results", "mvpplus")
os.makedirs(OUTPUT_DIR, exist_ok=True)

STATE_DIR = os.path.join(PROJECT_ROOT, "data", "mvpplus_state")
os.makedirs(STATE_DIR, exist_ok=True)
PREVIOUS_STATE_PATH = os.path.join(STATE_DIR, "previous_whale_positions.json")

# Risk thresholds
LIQ_DISTANCE_CRITICAL_PCT = -5.0  # Within 5% of liquidation
HIGH_LEVERAGE_THRESHOLD = 10.0
LARGE_POSITION_THRESHOLD_USD = 1_000_000  # $1M
CONCENTRATED_ASSET_RATIO = 0.5  # >50% of account in one asset


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_source_health(
    source: str, status: str, occurred_at_utc: str,
    error_type: Optional[str] = None, retryable: Optional[bool] = None,
    message_summary: Optional[str] = None,
) -> dict:
    entry: dict[str, Any] = {"status": status, "source": source, "occurred_at_utc": occurred_at_utc}
    if error_type is not None: entry["error_type"] = error_type
    if retryable is not None: entry["retryable"] = retryable
    if message_summary is not None: entry["message_summary"] = message_summary
    return entry


def load_current_positions() -> list[dict]:
    """Load the current positions from Lane 1 output."""
    path = os.path.join(OUTPUT_DIR, "lane1_whale_positions.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("positions", [])
    except (IOError, json.JSONDecodeError) as e:
        print(f"  [ERROR] Failed to load current positions: {e}", file=sys.stderr)
        return []


def load_previous_state() -> dict[str, dict]:
    """Load previous position state keyed by address+coin."""
    if not os.path.isfile(PREVIOUS_STATE_PATH):
        return {}
    try:
        with open(PREVIOUS_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("positions_by_key", {})
    except (IOError, json.JSONDecodeError):
        return {}


def save_current_state(positions: list[dict]):
    """Save current positions as previous state for next run."""
    by_key: dict[str, dict] = {}
    for p in positions:
        key = f"{p['address']}:{p['coin']}"
        by_key[key] = {
            "signed_size": p["signed_size"],
            "position_value_usd": p["position_value_usd"],
            "entry_price": p["entry_price"],
            "mark_price": p["mark_price"],
            "unrealized_pnl_usd": p.get("unrealized_pnl_usd"),
            "leverage": p["leverage"],
            "liquidation_price": p.get("liquidation_price"),
            "liquidation_distance_pct": p.get("liquidation_distance_pct"),
            "snapshot_time_utc": p["snapshot_time_utc"],
        }
    state = {
        "saved_at_utc": utc_now_str(),
        "positions_by_key": by_key,
    }
    try:
        with open(PREVIOUS_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"  [WARN] Failed to save previous state: {e}", file=sys.stderr)


def determine_change_type(
    prev_signed: Optional[float],
    curr_signed: float,
) -> tuple[str, str]:
    """Determine change type and direction.

    Returns (change_type, direction).
    """
    if prev_signed is None or prev_signed == 0:
        # New position
        return ("open_long" if curr_signed > 0 else "open_short",
                "long" if curr_signed > 0 else "short")

    if prev_signed > 0 and curr_signed < 0:
        return ("flip_long_to_short", "short")
    if prev_signed < 0 and curr_signed > 0:
        return ("flip_short_to_long", "long")

    direction = "long" if curr_signed > 0 else "short"
    size_delta = abs(curr_signed) - abs(prev_signed)

    if curr_signed == 0 or abs(curr_signed) < 0.001:
        return (f"close_{direction}", direction)
    elif abs(size_delta) < 0.001:
        # Same size - check for liquidation distance change
        return ("liquidation_distance_narrowed", direction)
    elif size_delta > 0:
        return (f"increase_{direction}", direction)
    else:
        return (f"reduce_{direction}", direction)


def compute_risk_flags(
    change_type: str,
    current: dict,
    previous: Optional[dict],
) -> list[str]:
    """Compute risk flags for a position change."""
    flags: list[str] = []

    # Liquidation distance critical
    liq_dist = current.get("liquidation_distance_pct")
    if liq_dist is not None and liq_dist < LIQ_DISTANCE_CRITICAL_PCT:
        flags.append("liquidation_distance_critical")

    # High leverage increase
    leverage = current.get("leverage", 0)
    prev_leverage = previous.get("leverage") if previous else None
    if leverage and leverage > HIGH_LEVERAGE_THRESHOLD:
        if prev_leverage is None or leverage > prev_leverage:
            flags.append("high_leverage_increase")

    # Large position open/close
    pos_value = current.get("position_value_usd", 0) or 0
    if "open" in change_type and pos_value >= LARGE_POSITION_THRESHOLD_USD:
        flags.append("large_position_open")
    if "close" in change_type and previous:
        prev_value = previous.get("position_value_usd", 0) or 0
        if prev_value >= LARGE_POSITION_THRESHOLD_USD:
            flags.append("large_position_close")

    # Direction flip
    if "flip" in change_type:
        flags.append("direction_flip")

    # Concentrated asset risk (single large position relative to account)
    # We don't have full portfolio, so mark if >$5M in one asset
    if pos_value >= 5_000_000:
        flags.append("concentrated_asset_risk")

    return flags


def build_previous_snapshot(prev: dict) -> Optional[dict]:
    """Build the 'previous' object for the change record."""
    if prev is None:
        return None
    return {
        "signed_size": prev.get("signed_size"),
        "position_value_usd": prev.get("position_value_usd"),
        "entry_price": prev.get("entry_price"),
        "mark_price": prev.get("mark_price"),
        "unrealized_pnl_usd": prev.get("unrealized_pnl_usd"),
        "leverage": prev.get("leverage"),
        "liquidation_price": prev.get("liquidation_price"),
        "liquidation_distance_pct": prev.get("liquidation_distance_pct"),
        "snapshot_time_utc": prev.get("snapshot_time_utc"),
    }


def build_current_snapshot(curr: dict) -> dict:
    """Build the 'current' object for the change record."""
    return {
        "signed_size": curr["signed_size"],
        "position_value_usd": curr["position_value_usd"],
        "entry_price": curr.get("entry_price"),
        "mark_price": curr["mark_price"],
        "unrealized_pnl_usd": curr.get("unrealized_pnl_usd"),
        "leverage": curr.get("leverage"),
        "liquidation_price": curr.get("liquidation_price"),
        "liquidation_distance_pct": curr.get("liquidation_distance_pct"),
        "snapshot_time_utc": curr["snapshot_time_utc"],
    }


def compute_delta(prev: Optional[dict], curr: dict) -> dict:
    """Compute delta between previous and current."""
    if prev is None:
        return {
            "size_delta": curr["signed_size"],
            "position_value_delta_usd": curr.get("position_value_usd"),
            "entry_price_delta_usd": None,
            "unrealized_pnl_delta_usd": curr.get("unrealized_pnl_usd"),
            "liquidation_distance_delta_pct": None,
        }
    return {
        "size_delta": round(curr["signed_size"] - prev.get("signed_size", 0), 6),
        "position_value_delta_usd": (
            round((curr.get("position_value_usd") or 0) - (prev.get("position_value_usd") or 0), 2)
            if curr.get("position_value_usd") is not None and prev.get("position_value_usd") is not None
            else None
        ),
        "entry_price_delta_usd": (
            round((curr.get("entry_price") or 0) - (prev.get("entry_price") or 0), 2)
            if curr.get("entry_price") is not None and prev.get("entry_price") is not None
            else None
        ),
        "unrealized_pnl_delta_usd": (
            round((curr.get("unrealized_pnl_usd") or 0) - (prev.get("unrealized_pnl_usd") or 0), 2)
            if curr.get("unrealized_pnl_usd") is not None and prev.get("unrealized_pnl_usd") is not None
            else None
        ),
        "liquidation_distance_delta_pct": (
            round((curr.get("liquidation_distance_pct") or 0) - (prev.get("liquidation_distance_pct") or 0), 4)
            if curr.get("liquidation_distance_pct") is not None and prev.get("liquidation_distance_pct") is not None
            else None
        ),
    }


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    start_time = time.time()
    run_id = f"mvpplus_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_lane2"
    snapshot_time = utc_now_str()
    source = "whale_change_engine"

    print(f"[{run_id}] Lane 2: Whale Position Change & Risk Engine", file=sys.stderr)
    print(f"  Detection time: {snapshot_time}", file=sys.stderr)

    # Load data
    current_positions = load_current_positions()
    if not current_positions:
        print("  [DEGRADED] No current positions from Lane 1. "
              "Run Lane 1 first.", file=sys.stderr)
        empty_output = {
            "run_id": run_id, "detected_at_utc": snapshot_time,
            "lane": "lane2_whale_engine",
            "changes": [],
            "source_health": make_source_health(
                source=source, status="degraded", occurred_at_utc=snapshot_time,
                error_type="no_input_data",
                message_summary="No current positions from Lane 1",
            ),
            "errors": [{"source": source, "error_type": "no_input_data",
                         "message_summary": "Lane 1 output not found or empty",
                         "occurred_at_utc": snapshot_time}],
        }
        output_path = os.path.join(OUTPUT_DIR, "lane2_whale_changes.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(empty_output, f, indent=2, ensure_ascii=False)
        return 1

    previous_state = load_previous_state()
    is_first_run = not previous_state
    if is_first_run:
        print("  First run — no previous state, saving current as baseline.", file=sys.stderr)

    # Detect changes
    changes: list[dict] = []
    errors: list[dict] = []

    for pos in current_positions:
        key = f"{pos['address']}:{pos['coin']}"
        prev = previous_state.get(key)

        change_type, direction = determine_change_type(
            prev.get("signed_size") if prev else None,
            pos["signed_size"],
        )

        if is_first_run:
            # On first run, treat all existing positions as "open" events
            if prev is None:
                change_type = "open_long" if pos["signed_size"] > 0 else "open_short"
        else:
            # Skip if the change type is trivial and no meaningful metric changed
            if change_type == "liquidation_distance_narrowed":
                # Always report this for monitoring
                pass

        prev_snapshot = build_previous_snapshot(prev) if prev else None
        curr_snapshot = build_current_snapshot(pos)
        delta = compute_delta(prev, pos) if prev else {
            "size_delta": pos["signed_size"],
            "position_value_delta_usd": pos.get("position_value_usd"),
            "entry_price_delta_usd": None,
            "unrealized_pnl_delta_usd": pos.get("unrealized_pnl_usd"),
            "liquidation_distance_delta_pct": None,
        }
        risk_flags = compute_risk_flags(change_type, pos, prev)

        change_record: dict[str, Any] = {
            "address": pos["address"],
            "label": pos.get("label"),
            "coin": pos["coin"],
            "change_type": change_type,
            "previous": prev_snapshot,
            "current": curr_snapshot,
            "delta": delta,
            "detected_at_utc": snapshot_time,
            "data_source": source,
            "source_health": make_source_health(
                source=source, status="healthy", occurred_at_utc=snapshot_time,
            ),
            "risk_flags": risk_flags,
        }

        # Format change description
        desc = f"  {change_type}: {pos.get('label','?')} {pos['coin']}"
        if prev and delta.get("size_delta"):
            desc += f" (size Δ={delta['size_delta']:+.4f})"
        if risk_flags:
            desc += f" ⚠ {risk_flags}"
        print(desc, file=sys.stderr)

        changes.append(change_record)

    # Also detect positions that existed before but are now closed (not in current)
    if not is_first_run:
        current_keys = {f"{p['address']}:{p['coin']}" for p in current_positions}
        for key, prev in previous_state.items():
            if key not in current_keys:
                prev_signed = prev.get("signed_size", 0)
                direction = "long" if prev_signed > 0 else "short"
                change_type = f"close_{direction}"
                parts = key.split(":")
                addr, coin = parts[0], parts[1] if len(parts) > 1 else "?"

                # Find label from tracked addresses
                label = None
                for p in current_positions:
                    if p["address"] == addr:
                        label = p.get("label")
                        break

                change_record = {
                    "address": addr,
                    "label": label,
                    "coin": coin,
                    "change_type": change_type,
                    "previous": build_previous_snapshot(prev),
                    "current": None,
                    "delta": {
                        "size_delta": -prev.get("signed_size", 0),
                        "position_value_delta_usd": -(prev.get("position_value_usd") or 0),
                        "entry_price_delta_usd": None,
                        "unrealized_pnl_delta_usd": None,
                        "liquidation_distance_delta_pct": None,
                    },
                    "detected_at_utc": snapshot_time,
                    "data_source": source,
                    "source_health": make_source_health(
                        source=source, status="healthy", occurred_at_utc=snapshot_time,
                    ),
                    "risk_flags": ["large_position_close"] if (prev.get("position_value_usd") or 0) >= LARGE_POSITION_THRESHOLD_USD else [],
                }
                changes.append(change_record)
                print(f"  {change_type}: position disappeared {coin}", file=sys.stderr)

    # Save current state as previous for next run
    save_current_state(current_positions)

    overall_status = "healthy"

    output = {
        "run_id": run_id,
        "detected_at_utc": snapshot_time,
        "lane": "lane2_whale_engine",
        "changes": changes,
        "is_first_run": is_first_run,
        "source_health": make_source_health(
            source=source, status=overall_status, occurred_at_utc=snapshot_time,
            message_summary=f"{len(changes)} position changes detected"
                           if changes else "No position changes detected",
        ),
    }
    if errors:
        output["errors"] = errors

    output_path = os.path.join(OUTPUT_DIR, "lane2_whale_changes.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"  Done in {elapsed:.1f}s. {len(changes)} changes detected.", file=sys.stderr)
    print(f"  Output: {output_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
