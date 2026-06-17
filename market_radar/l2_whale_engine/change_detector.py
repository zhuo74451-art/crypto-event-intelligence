"""L2 — Whale Position Change Detector.

Detects position changes between consecutive snapshots with proper
baseline semantics: first-seen positions are marked as
BASELINE_OPEN_POSITION, NOT as newly opened.

Supports all 11 change types:
  open_long, open_short,
  increase_long, increase_short,
  reduce_long, reduce_short,
  close_long, close_short,
  flip_long_to_short, flip_short_to_long,
  liquidation_distance_narrowed

Plus baseline variant:
  baseline_open_position (first run, no previous state)

Requirements:
- Configurable size change threshold (default 0.001 coins) for float jitter
- Deterministic for same inputs
- Snapshot time order validation
- Old snapshots never overwrite new
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from market_radar.l1_hyperliquid_provider.provenance import (
    make_source_health, utc_now_str,
)
from market_radar.l2_whale_engine.state_manager import (
    make_position_key, extract_snapshot,
)

# If absolute size change is below this, treat as no change (float jitter)
DEFAULT_SIZE_THRESHOLD = 0.001

# Risk flag thresholds
# Liquidation distance is now always positive (distance FROM liquidation).
# Smaller value = closer to liquidation. <= 5% means within 5% of liq.
LIQ_DISTANCE_CRITICAL = 5.0
HIGH_LEVERAGE = 10.0
LARGE_POSITION_USD = 1_000_000
MASSIVE_POSITION_USD = 5_000_000


def _iso_to_ts(iso_str: Optional[str]) -> float:
    """Parse ISO timestamp to Unix timestamp. Returns 0 on failure."""
    if not iso_str:
        return 0
    try:
        s = iso_str.replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, TypeError):
        return 0


def detect_change(
    current: dict,
    previous: Optional[dict],
    size_threshold: float = DEFAULT_SIZE_THRESHOLD,
    is_baseline_run: bool = False,
) -> tuple[str, str, Optional[dict], Optional[dict], dict]:
    """Detect change between current and previous position snapshot.

    Args:
        current: Current WhalePosition dict
        previous: Previous snapshot dict (None if first time seeing this position)
        size_threshold: Minimum absolute size change to consider as a real change
        is_baseline_run: True if this is the first run (no previous state at all)

    Returns:
        (change_type, direction, previous_snapshot, current_snapshot, delta)
    """
    direction = current.get("direction", "long")
    curr_signed = current.get("signed_size", 0)
    curr_abs = current.get("absolute_size", 0)

    prev_signed = previous.get("signed_size") if previous else None
    prev_abs = abs(prev_signed) if prev_signed is not None else None

    delta = _compute_delta(previous, current)

    # Snapshot time order check
    curr_time = current.get("snapshot_time_utc", "")
    prev_time = previous.get("snapshot_time_utc") if previous else None
    if prev_time and curr_time:
        if _iso_to_ts(curr_time) < _iso_to_ts(prev_time):
            # Current is older than previous — reject this change
            return ("stale_snapshot_rejected", direction,
                    extract_snapshot(previous) if previous else None,
                    extract_snapshot(current), delta)

    # Case 1: First run — mark as baseline
    if is_baseline_run:
        return ("baseline_open_position", direction,
                None, extract_snapshot(current), delta)

    # Case 2: No previous position → newly opened
    if prev_signed is None or prev_signed == 0:
        ct = f"open_{direction}"
        return (ct, direction, None, extract_snapshot(current), delta)

    # Case 3: Direction flip
    if (prev_signed > 0 and curr_signed < 0):
        return ("flip_long_to_short", "short",
                extract_snapshot(previous), extract_snapshot(current), delta)
    if (prev_signed < 0 and curr_signed > 0):
        return ("flip_short_to_long", "long",
                extract_snapshot(previous), extract_snapshot(current), delta)

    # Case 4: Position closed
    if curr_signed == 0 or curr_abs < size_threshold:
        ct = f"close_{direction}"
        return (ct, direction,
                extract_snapshot(previous), None, delta)

    # Case 5: Size change
    size_delta = curr_abs - prev_abs
    if abs(size_delta) <= size_threshold:
        # Same size — check liquidation distance change
        prev_liq_dist = previous.get("liquidation_distance_pct")
        curr_liq_dist = current.get("liquidation_distance_pct")
        if (prev_liq_dist is not None and curr_liq_dist is not None
                and abs(curr_liq_dist - prev_liq_dist) > 0.5):
            return ("liquidation_distance_narrowed", direction,
                    extract_snapshot(previous), extract_snapshot(current), delta)
        # No meaningful change
        return ("no_change", direction,
                extract_snapshot(previous), extract_snapshot(current), delta)

    if size_delta > 0:
        ct = f"increase_{direction}"
    else:
        ct = f"reduce_{direction}"

    return (ct, direction,
            extract_snapshot(previous) if previous else None,
            extract_snapshot(current), delta)


def _compute_delta(previous: Optional[dict], current: dict) -> dict:
    """Compute delta between previous and current position values."""
    if previous is None:
        return {
            "size_delta": current.get("signed_size"),
            "position_value_delta_usd": current.get("position_value_usd"),
            "entry_price_delta_usd": None,
            "unrealized_pnl_delta_usd": current.get("unrealized_pnl_usd"),
            "liquidation_distance_delta_pct": None,
        }

    def _sub(a, b):
        if a is not None and b is not None:
            return round(a - b, 6) if isinstance(a, float) else a - b
        return None

    return {
        "size_delta": _sub(current.get("signed_size"), previous.get("signed_size")),
        "position_value_delta_usd": _sub(
            current.get("position_value_usd"), previous.get("position_value_usd")
        ),
        "entry_price_delta_usd": _sub(
            current.get("entry_price"), previous.get("entry_price")
        ),
        "unrealized_pnl_delta_usd": _sub(
            current.get("unrealized_pnl_usd"), previous.get("unrealized_pnl_usd")
        ),
        "liquidation_distance_delta_pct": _sub(
            current.get("liquidation_distance_pct"),
            previous.get("liquidation_distance_pct"),
        ),
    }


def compute_risk_flags(
    change_type: str,
    current: dict,
    previous: Optional[dict] = None,
) -> list[dict]:
    """Compute risk flags with rule evidence.

    Each flag includes rule_id, threshold, observed_value, generated_at, data_mode.
    """
    flags: list[dict] = []
    now = utc_now_str()
    data_mode = current.get("_provenance", {}).get("data_mode", "live")

    # R1: Liquidation distance critical
    # Distance is now always positive (distance FROM liquidation).
    # Smaller value = closer to liquidation. <= threshold means critical.
    liq_dist = current.get("liquidation_distance_pct")
    if liq_dist is not None and liq_dist > 0 and liq_dist <= LIQ_DISTANCE_CRITICAL:
        flags.append({
            "rule_id": "R1_LIQ_DISTANCE_CRITICAL",
            "threshold": f"<= {LIQ_DISTANCE_CRITICAL}% (distance from liquidation)",
            "observed_value": liq_dist,
            "observed_at": now,
            "data_mode": data_mode,
        })

    # R2: High leverage
    leverage = current.get("leverage", 0)
    if leverage and leverage > HIGH_LEVERAGE:
        prev_lev = previous.get("leverage") if previous else None
        if prev_lev is None or leverage > prev_lev:
            flags.append({
                "rule_id": "R2_HIGH_LEVERAGE",
                "threshold": f"> {HIGH_LEVERAGE}x",
                "observed_value": leverage,
                "observed_at": now,
                "data_mode": data_mode,
            })

    # R3: Large position open
    pos_value = current.get("position_value_usd", 0) or 0
    if "open" in change_type and pos_value >= LARGE_POSITION_USD:
        flags.append({
            "rule_id": "R3_LARGE_POSITION_OPEN",
            "threshold": f">= ${LARGE_POSITION_USD:,.0f}",
            "observed_value": pos_value,
            "observed_at": now,
            "data_mode": data_mode,
        })

    # R4: Large position close
    if "close" in change_type and previous:
        prev_value = previous.get("position_value_usd", 0) or 0
        if prev_value >= LARGE_POSITION_USD:
            flags.append({
                "rule_id": "R4_LARGE_POSITION_CLOSE",
                "threshold": f">= ${LARGE_POSITION_USD:,.0f}",
                "observed_value": prev_value,
                "observed_at": now,
                "data_mode": data_mode,
            })

    # R5: Direction flip
    if "flip" in change_type:
        flags.append({
            "rule_id": "R5_DIRECTION_FLIP",
            "threshold": "direction changed",
            "observed_value": change_type,
            "observed_at": now,
            "data_mode": data_mode,
        })

    # R6: Concentrated asset risk
    if pos_value >= MASSIVE_POSITION_USD:
        flags.append({
            "rule_id": "R6_CONCENTRATED_ASSET",
            "threshold": f">= ${MASSIVE_POSITION_USD:,.0f} single asset",
            "observed_value": pos_value,
            "observed_at": now,
            "data_mode": data_mode,
        })

    return flags


def detect_all_changes(
    current_positions: list[dict],
    previous_state: dict[str, dict],
    is_baseline_run: bool = False,
    size_threshold: float = DEFAULT_SIZE_THRESHOLD,
) -> list[dict]:
    """Detect changes for all current positions compared to previous state.

    Also detects positions that existed before but are now closed.
    """
    changes: list[dict] = []
    current_keys: set[str] = set()
    now = utc_now_str()

    for pos in current_positions:
        key = make_position_key(
            pos.get("address", ""),
            pos.get("coin", ""),
        )
        current_keys.add(key)
        prev = previous_state.get(key)

        change_type, direction, prev_snap, curr_snap, delta = detect_change(
            pos, prev, size_threshold, is_baseline_run,
        )

        if change_type == "no_change":
            continue

        risk_flags = compute_risk_flags(change_type, pos, prev)

        change_record: dict = {
            "address": pos.get("address"),
            "label": pos.get("label"),
            "coin": pos.get("coin"),
            "change_type": change_type,
            "previous": prev_snap,
            "current": curr_snap,
            "delta": delta,
            "detected_at_utc": now,
            "data_source": "whale_change_engine",
            "source_health": make_source_health(
                source="whale_change_engine", status="healthy",
                occurred_at_utc=now,
            ),
            "risk_flags": [f["rule_id"] for f in risk_flags],
            "_risk_evidence": risk_flags,
        }
        changes.append(change_record)

    # Detect disappeared positions (closed between runs)
    if not is_baseline_run:
        for key, prev in previous_state.items():
            if key not in current_keys:
                parts = key.split(":")
                addr, coin = parts[0], parts[1] if len(parts) > 1 else "?"
                prev_signed = prev.get("signed_size", 0)
                direction = "long" if prev_signed > 0 else "short"
                ct = f"close_{direction}"

                # Try to find label from current positions
                label = None
                for pos in current_positions:
                    if pos.get("address", "").lower() == addr:
                        label = pos.get("label")
                        break

                change_record: dict = {
                    "address": addr,
                    "label": label,
                    "coin": coin,
                    "change_type": ct,
                    "previous": prev,
                    "current": None,
                    "delta": {
                        "size_delta": -(prev.get("signed_size", 0)),
                        "position_value_delta_usd": -(prev.get("position_value_usd") or 0),
                        "entry_price_delta_usd": None,
                        "unrealized_pnl_delta_usd": None,
                        "liquidation_distance_delta_pct": None,
                    },
                    "detected_at_utc": now,
                    "data_source": "whale_change_engine",
                    "source_health": make_source_health(
                        source="whale_change_engine", status="healthy",
                        occurred_at_utc=now,
                    ),
                    "risk_flags": [],
                    "_risk_evidence": [],
                }
                # Add close risk flag if large
                if (prev.get("position_value_usd") or 0) >= LARGE_POSITION_USD:
                    change_record["risk_flags"].append("R4_LARGE_POSITION_CLOSE")
                    change_record["_risk_evidence"].append({
                        "rule_id": "R4_LARGE_POSITION_CLOSE",
                        "threshold": f">= ${LARGE_POSITION_USD:,.0f}",
                        "observed_value": prev.get("position_value_usd"),
                        "observed_at": now,
                        "data_mode": "cached",
                    })
                changes.append(change_record)

    return changes


