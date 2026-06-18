"""Whale Domain — position change detector.

Pure deterministic logic. No network, no I/O, no random.
All inputs injected as parameters.
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.whale_domain.models import (
    WhalePositionInput, WhaleSnapshot, WhalePositionChange,
    ChangeType, SIZE_CHANGE_THRESHOLD,
    LIQ_DISTANCE_CRITICAL, HIGH_LEVERAGE_THRESHOLD,
    LARGE_POSITION_USD, MASSIVE_POSITION_USD,
    extract_snapshot, snapshot_to_dict, make_position_key,
    _iso_to_ts,
)


def _compute_delta(
    prev: Optional[WhaleSnapshot],
    curr: WhaleSnapshot,
) -> dict:
    """Compute delta between two snapshots."""
    if prev is None:
        return {
            "size_delta": curr.signed_size,
            "position_value_delta_usd": curr.position_value_usd,
            "entry_price_delta_usd": None,
            "unrealized_pnl_delta_usd": curr.unrealized_pnl_usd,
            "liquidation_distance_delta_pct": None,
        }

    def _sub(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is not None and b is not None:
            return round(float(a) - float(b), 6)
        return None

    return {
        "size_delta": _sub(curr.signed_size, prev.signed_size),
        "position_value_delta_usd": _sub(
            curr.position_value_usd, prev.position_value_usd,
        ),
        "entry_price_delta_usd": _sub(
            curr.entry_price, prev.entry_price,
        ),
        "unrealized_pnl_delta_usd": _sub(
            curr.unrealized_pnl_usd, prev.unrealized_pnl_usd,
        ),
        "liquidation_distance_delta_pct": _sub(
            curr.liquidation_distance_pct, prev.liquidation_distance_pct,
        ),
    }


def detect_change(
    current: WhaleSnapshot,
    previous: Optional[WhaleSnapshot],
    size_threshold: float = SIZE_CHANGE_THRESHOLD,
    is_baseline_run: bool = False,
) -> tuple[ChangeType, str, Optional[dict], Optional[dict], dict]:
    """Detect change between current and previous position snapshot.

    Args:
        current: Current position snapshot.
        previous: Previous snapshot (None if first time seeing this position).
        size_threshold: Min size change to consider as real (float jitter filter).
        is_baseline_run: True if this is the first run overall.

    Returns:
        (change_type, direction, previous_dict, current_dict, delta)
        previous_dict/current_dict are None for absent positions.
    """
    direction = current.direction
    curr_signed = current.signed_size
    curr_abs = current.absolute_size

    prev_signed = previous.signed_size if previous else None
    prev_abs = abs(prev_signed) if prev_signed is not None else None

    delta = _compute_delta(previous, current)

    # Snapshot time order check
    curr_time = current.snapshot_time_utc
    prev_time = previous.snapshot_time_utc if previous else None
    if prev_time and curr_time:
        if _iso_to_ts(curr_time) < _iso_to_ts(prev_time):
            # Current is older than previous — reject
            return (
                ChangeType.STALE_SNAPSHOT_REJECTED, direction,
                snapshot_to_dict(previous) if previous else None,
                snapshot_to_dict(current), delta,
            )

    # Case 1: First run — mark as baseline
    if is_baseline_run:
        if curr_signed == 0:
            # Zero-size position on baseline — not an open position
            return (
                ChangeType.NO_CHANGE, direction,
                None, snapshot_to_dict(current), delta,
            )
        return (
            ChangeType.BASELINE_OPEN_POSITION, direction,
            None, snapshot_to_dict(current), delta,
        )

    # Case 2: No previous position → newly opened
    if prev_signed is None or prev_signed == 0:
        ct = ChangeType.OPEN_LONG if curr_signed > 0 else ChangeType.OPEN_SHORT
        return (ct, direction, None, snapshot_to_dict(current), delta)

    # Case 3: Direction flip
    if prev_signed > 0 and curr_signed < 0:
        return (
            ChangeType.FLIP_LONG_TO_SHORT, "short",
            snapshot_to_dict(previous), snapshot_to_dict(current), delta,
        )
    if prev_signed < 0 and curr_signed > 0:
        return (
            ChangeType.FLIP_SHORT_TO_LONG, "long",
            snapshot_to_dict(previous), snapshot_to_dict(current), delta,
        )

    # Case 4: Position closed (size at or near zero)
    if curr_signed == 0 or curr_abs < size_threshold:
        # When signed_size == 0, current.direction is ambiguous — use previous
        close_dir = previous.direction if curr_signed == 0 and previous else direction
        ct = ChangeType.CLOSE_LONG if close_dir == "long" else ChangeType.CLOSE_SHORT
        return (ct, close_dir, snapshot_to_dict(previous), None, delta)

    # Case 5: Size change
    if prev_abs is not None:
        size_delta = curr_abs - prev_abs
    else:
        size_delta = curr_abs

    if abs(size_delta) <= size_threshold:
        # Same size — check liquidation distance change
        prev_liq = previous.liquidation_distance_pct if previous else None
        curr_liq = current.liquidation_distance_pct
        if (prev_liq is not None and curr_liq is not None
                and (curr_liq - prev_liq) < -0.5):
            return (
                ChangeType.LIQUIDATION_DISTANCE_NARROWED, direction,
                snapshot_to_dict(previous), snapshot_to_dict(current), delta,
            )
        # No meaningful change
        return (
            ChangeType.NO_CHANGE, direction,
            snapshot_to_dict(previous), snapshot_to_dict(current), delta,
        )

    if size_delta > 0:
        ct = ChangeType.INCREASE_LONG if direction == "long" else ChangeType.INCREASE_SHORT
    else:
        ct = ChangeType.REDUCE_LONG if direction == "long" else ChangeType.REDUCE_SHORT

    return (ct, direction,
            snapshot_to_dict(previous) if previous else None,
            snapshot_to_dict(current), delta)


def compute_risk_flags(
    change_type: ChangeType,
    current: WhaleSnapshot,
    previous: Optional[WhaleSnapshot] = None,
    detected_at_utc: str = "",
) -> list[dict]:
    """Compute risk flags with rule evidence.

    Rules:
      R1: Liquidation distance <= LIQ_DISTANCE_CRITICAL
      R2: Leverage > HIGH_LEVERAGE_THRESHOLD
      R3: Large position opened (>= LARGE_POSITION_USD)
      R4: Large position closed
      R5: Direction flip
      R6: Concentrated asset risk (>= MASSIVE_POSITION_USD)
    """
    flags: list[dict] = []

    # R1: Liquidation distance critical
    liq_dist = current.liquidation_distance_pct
    if liq_dist is not None and liq_dist > 0 and liq_dist <= LIQ_DISTANCE_CRITICAL:
        flags.append({
            "rule_id": "R1_LIQ_DISTANCE_CRITICAL",
            "threshold": f"<= {LIQ_DISTANCE_CRITICAL}% from liq",
            "observed_value": liq_dist,
        })

    # R2: High leverage
    leverage = current.leverage
    if leverage and leverage > HIGH_LEVERAGE_THRESHOLD:
        prev_lev = previous.leverage if previous else None
        if prev_lev is None or leverage > prev_lev:
            flags.append({
                "rule_id": "R2_HIGH_LEVERAGE",
                "threshold": f"> {HIGH_LEVERAGE_THRESHOLD}x",
                "observed_value": leverage,
            })

    # R3: Large position open
    pos_value = current.position_value_usd
    ct_str = change_type.value if isinstance(change_type, ChangeType) else str(change_type)
    REAL_OPEN_TYPES = {ChangeType.OPEN_LONG.value, ChangeType.OPEN_SHORT.value}
    if ct_str in REAL_OPEN_TYPES and pos_value >= LARGE_POSITION_USD:
        flags.append({
            "rule_id": "R3_LARGE_POSITION_OPEN",
            "threshold": f">= ${LARGE_POSITION_USD:,.0f}",
            "observed_value": pos_value,
        })

    # R4: Large position close
    if "close" in ct_str and previous:
        prev_value = previous.position_value_usd
        if prev_value >= LARGE_POSITION_USD:
            flags.append({
                "rule_id": "R4_LARGE_POSITION_CLOSE",
                "threshold": f">= ${LARGE_POSITION_USD:,.0f}",
                "observed_value": prev_value,
            })

    # R5: Direction flip
    if "flip" in ct_str:
        flags.append({
            "rule_id": "R5_DIRECTION_FLIP",
            "threshold": "direction changed",
            "observed_value": ct_str,
        })

    # R6: Concentrated asset
    if pos_value >= MASSIVE_POSITION_USD:
        flags.append({
            "rule_id": "R6_CONCENTRATED_ASSET",
            "threshold": f">= ${MASSIVE_POSITION_USD:,.0f} single asset",
            "observed_value": pos_value,
        })

    return flags


def detect_all_changes(
    current_inputs: list[WhalePositionInput],
    previous_snapshots: dict[str, WhaleSnapshot],
    is_baseline_run: bool = False,
    detected_at_utc: str = "",
    size_threshold: float = SIZE_CHANGE_THRESHOLD,
) -> list[WhalePositionChange]:
    """Detect all position changes from current inputs vs previous state.

    Args:
        current_inputs: Current positions from external source.
        previous_snapshots: Previous state keyed by make_position_key().
        is_baseline_run: True if first run.
        detected_at_utc: Timestamp for this detection run.
        size_threshold: Float jitter threshold.

    Returns:
        List of WhalePositionChange records.
    """
    changes: list[WhalePositionChange] = []
    current_keys: set[str] = set()

    for inp in current_inputs:
        snap = extract_snapshot(inp)
        key = make_position_key(snap.address, snap.coin)
        current_keys.add(key)

        prev = previous_snapshots.get(key)
        ct, direction, prev_dict, curr_dict, delta = detect_change(
            snap, prev, size_threshold, is_baseline_run,
        )

        if ct == ChangeType.NO_CHANGE:
            continue

        risk_flags = compute_risk_flags(ct, snap, prev, detected_at_utc)
        ct_str = ct.value if isinstance(ct, ChangeType) else str(ct)

        change = WhalePositionChange(
            change_id=WhalePositionChange.compute_id(
                snap.address, snap.coin, ct_str, detected_at_utc,
            ),
            address=snap.address,
            label=snap.label,
            coin=snap.coin,
            change_type=ct_str,
            direction=direction,
            previous=prev_dict,
            current=curr_dict,
            delta=delta,
            risk_flags=[f["rule_id"] for f in risk_flags],
            detected_at_utc=detected_at_utc,
        )
        changes.append(change)

    # Detect disappeared positions (closed between runs)
    if not is_baseline_run:
        for key, prev_snap in previous_snapshots.items():
            if key not in current_keys:
                parts = key.split(":")
                addr = parts[0]
                coin = parts[1] if len(parts) > 1 else "?"
                direction = "long" if prev_snap.signed_size > 0 else "short"
                ct_str = f"close_{direction}"
                ct = ChangeType.CLOSE_LONG if direction == "long" else ChangeType.CLOSE_SHORT

                risk_flags = compute_risk_flags(ct, prev_snap, detected_at_utc=detected_at_utc)

                change = WhalePositionChange(
                    change_id=WhalePositionChange.compute_id(
                        addr, coin, ct_str, detected_at_utc,
                    ),
                    address=addr,
                    label=prev_snap.label,
                    coin=coin,
                    change_type=ct_str,
                    direction=direction,
                    previous=snapshot_to_dict(prev_snap),
                    current=None,
                    delta={
                        "size_delta": -prev_snap.signed_size,
                        "position_value_delta_usd": -prev_snap.position_value_usd,
                        "entry_price_delta_usd": None,
                        "unrealized_pnl_delta_usd": None,
                        "liquidation_distance_delta_pct": None,
                    },
                    risk_flags=[f["rule_id"] for f in risk_flags],
                    detected_at_utc=detected_at_utc,
                )
                changes.append(change)

    return changes
