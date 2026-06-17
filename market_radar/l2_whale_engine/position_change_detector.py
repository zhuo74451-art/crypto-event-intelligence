"""MVP+ L2 — Whale Position Change Detector & Risk Engine.

Compares current whale positions against previous snapshots to detect:
  - POSITION_OPENED: new position appeared
  - POSITION_INCREASED: size grew
  - POSITION_REDUCED: size shrank
  - POSITION_CLOSED: position disappeared
  - DIRECTION_FLIPPED: long↔short flip
  - NO_CHANGE: no meaningful difference

Also assesses risk level based on change magnitude, leverage proximity
to liquidation, and concentration.

Outputs list[WhalePositionChange] contracts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from market_radar.shared.contracts import (
    WhalePosition,
    WhalePositionChange,
    PositionSide,
    ChangeType,
    RiskLevel,
    EntityType,
    LabelConfidence,
    DegradedInfo,
    SourceHealth,
    SourceStatus,
)

L2_SOURCE_NAME = "whale_change_engine"
L2_SOURCE_GROUP = "hyperliquid"

# Minimum position size USD change to consider meaningful (avoid noise)
MIN_CHANGE_THRESHOLD_USD = 10_000

# Risk assessment thresholds
HIGH_LEVERAGE_THRESHOLD = 10.0  # 10x+
CRITICAL_LIQUIDATION_DISTANCE_PCT = 5.0  # Within 5% of liquidation
ELEVATED_LIQUIDATION_DISTANCE_PCT = 15.0  # Within 15%
LARGE_POSITION_CHANGE_PCT = 50.0  # 50%+ change in position size
MASSIVE_POSITION_CHANGE_PCT = 200.0  # 200%+ change


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_key(address: str, asset: str) -> str:
    """Unique key for a (address, asset) pair."""
    return f"{address.lower()}:{asset.upper()}"


def _assess_risk_level(
    change_type: ChangeType,
    position_size_usd: float,
    leverage: Optional[float],
    liquidation_distance_pct: Optional[float],
    change_pct: Optional[float],
) -> tuple[RiskLevel, list[str]]:
    """Assess risk level and return (risk_level, risk_factors)."""
    risk_factors: list[str] = []

    # Liquidation proximity
    if liquidation_distance_pct is not None:
        if liquidation_distance_pct < CRITICAL_LIQUIDATION_DISTANCE_PCT:
            risk_factors.append("liquidation_critical")
        elif liquidation_distance_pct < ELEVATED_LIQUIDATION_DISTANCE_PCT:
            risk_factors.append("liquidation_near")

    # High leverage
    if leverage is not None and leverage >= HIGH_LEVERAGE_THRESHOLD:
        risk_factors.append("high_leverage")

    # Large position changes
    if change_type in (ChangeType.POSITION_INCREASED, ChangeType.POSITION_REDUCED):
        if change_pct is not None and change_pct >= MASSIVE_POSITION_CHANGE_PCT:
            risk_factors.append("massive_position_shift")
        elif change_pct is not None and change_pct >= LARGE_POSITION_CHANGE_PCT:
            risk_factors.append("large_position_shift")

    # New position or flip
    if change_type == ChangeType.POSITION_OPENED:
        if position_size_usd >= 5_000_000:
            risk_factors.append("large_new_position")
        if leverage is not None and leverage >= HIGH_LEVERAGE_THRESHOLD:
            risk_factors.append("high_leverage_new_position")

    if change_type == ChangeType.DIRECTION_FLIPPED:
        risk_factors.append("direction_flipped")

    # Risk level determination
    if not risk_factors:
        return RiskLevel.LOW, risk_factors
    if any(f in ("liquidation_critical", "massive_position_shift") for f in risk_factors):
        return RiskLevel.CRITICAL, risk_factors
    if len(risk_factors) >= 2:
        return RiskLevel.ELEVATED, risk_factors
    return RiskLevel.NORMAL, risk_factors


def detect_changes(
    current_positions: list[WhalePosition],
    previous_positions: list[WhalePosition],
    observed_at: str | None = None,
) -> list[WhalePositionChange]:
    """Detect changes between current and previous position snapshots.

    Args:
        current_positions: List of current WhalePosition contracts
        previous_positions: List of previous WhalePosition contracts (or empty list)
        observed_at: Override timestamp (default: now)

    Returns:
        List of WhalePositionChange contracts
    """
    if observed_at is None:
        observed_at = _utc_now()

    changes: list[WhalePositionChange] = []

    # Index previous positions by key
    prev_by_key: dict[str, WhalePosition] = {}
    for p in previous_positions:
        key = _build_key(p.address, p.asset)
        prev_by_key[key] = p

    # Index current positions by key
    cur_by_key: dict[str, WhalePosition] = {}
    for p in current_positions:
        key = _build_key(p.address, p.asset)
        cur_by_key[key] = p

    # Check current positions against previous
    for key, cur in cur_by_key.items():
        prev = prev_by_key.get(key)

        if prev is None:
            # POSITION_OPENED — no previous record
            change_type = ChangeType.POSITION_OPENED
            previous_size = None
            previous_observed = None
            delta = None
            change_pct = None
        else:
            # Check for direction flip
            if prev.side != cur.side:
                change_type = ChangeType.DIRECTION_FLIPPED
                previous_size = prev.position_size_usd
                previous_observed = prev.observed_at
                delta = None
                change_pct = None
            else:
                # Calculate size delta
                delta = cur.position_size_usd - prev.position_size_usd
                prev_size = prev.position_size_usd

                if abs(delta) <= MIN_CHANGE_THRESHOLD_USD:
                    change_type = ChangeType.NO_CHANGE
                    delta = 0.0
                    change_pct = 0.0
                elif delta > 0:
                    change_type = ChangeType.POSITION_INCREASED
                    change_pct = (delta / prev_size * 100) if prev_size > 0 else None
                else:
                    change_type = ChangeType.POSITION_REDUCED
                    change_pct = (delta / prev_size * 100) if prev_size > 0 else None

                previous_size = prev.position_size_usd
                previous_observed = prev.observed_at

        # Risk assessment
        risk_level, risk_factors = _assess_risk_level(
            change_type=change_type,
            position_size_usd=cur.position_size_usd,
            leverage=cur.leverage,
            liquidation_distance_pct=cur.liquidation_distance_pct,
            change_pct=change_pct,
        )

        changes.append(WhalePositionChange(
            address=cur.address,
            asset=cur.asset,
            side=cur.side,
            change_type=change_type,
            current_position_size_usd=cur.position_size_usd,
            current_observed_at=cur.observed_at,
            current_entry_price=cur.entry_price,
            current_mark_price=cur.mark_price,
            current_unrealized_pnl_usd=cur.unrealized_pnl_usd,
            current_liquidation_price=cur.liquidation_price,
            current_liquidation_distance_pct=cur.liquidation_distance_pct,
            current_leverage=cur.leverage,
            previous_position_size_usd=previous_size,
            previous_observed_at=previous_observed,
            position_delta_usd=round(delta, 2) if delta is not None else None,
            change_pct=round(change_pct, 4) if change_pct is not None else None,
            risk_level=risk_level,
            risk_factors=risk_factors,
            label=cur.label,
            entity_type=cur.entity_type,
            label_confidence=cur.label_confidence,
            data_origin=cur.data_origin,
            source=L2_SOURCE_NAME,
        ))

    # Check for CLOSED positions (in previous but not current)
    prev_seen = set(prev_by_key.keys())
    cur_seen = set(cur_by_key.keys())
    closed_keys = prev_seen - cur_seen

    for key in closed_keys:
        p = prev_by_key[key]
        risk_level, risk_factors = _assess_risk_level(
            change_type=ChangeType.POSITION_CLOSED,
            position_size_usd=p.position_size_usd,
            leverage=p.leverage,
            liquidation_distance_pct=p.liquidation_distance_pct,
            change_pct=-100.0,
        )
        changes.append(WhalePositionChange(
            address=p.address,
            asset=p.asset,
            side=p.side,
            change_type=ChangeType.POSITION_CLOSED,
            current_position_size_usd=0.0,
            current_observed_at=observed_at,
            current_entry_price=None,
            current_mark_price=None,
            current_unrealized_pnl_usd=None,
            current_liquidation_price=None,
            current_liquidation_distance_pct=None,
            current_leverage=None,
            previous_position_size_usd=p.position_size_usd,
            previous_observed_at=p.observed_at,
            position_delta_usd=-p.position_size_usd,
            change_pct=-100.0,
            risk_level=risk_level,
            risk_factors=risk_factors,
            label=p.label,
            entity_type=p.entity_type,
            label_confidence=p.label_confidence,
            data_origin=p.data_origin,
            source=L2_SOURCE_NAME,
        ))

    return changes


class PositionChangeDetector:
    """Stateful change detector with JSON persistence for previous snapshot."""

    def __init__(self, state_path: str | Path | None = None):
        self.state_path = Path(state_path) if state_path else None

    def load_previous_positions(self) -> list[WhalePosition]:
        """Load previous positions from state file."""
        if not self.state_path or not self.state_path.exists():
            return []
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            positions = []
            for item in data:
                try:
                    side = PositionSide(item.get("side", "LONG"))
                    et = item.get("entity_type")
                    entity_type = EntityType(et) if et and EntityType._value2member_map_.get(et) else None
                    lc = item.get("label_confidence")
                    label_confidence = LabelConfidence(lc) if lc and LabelConfidence._value2member_map_.get(lc) else None
                    positions.append(WhalePosition(
                        address=item["address"],
                        asset=item["asset"],
                        side=side,
                        position_size_usd=item["position_size_usd"],
                        observed_at=item.get("observed_at", ""),
                        entry_price=item.get("entry_price"),
                        mark_price=item.get("mark_price"),
                        leverage=item.get("leverage"),
                        unrealized_pnl_usd=item.get("unrealized_pnl_usd"),
                        margin_used_usd=item.get("margin_used_usd"),
                        liquidation_price=item.get("liquidation_price"),
                        liquidation_distance_pct=item.get("liquidation_distance_pct"),
                        label=item.get("label"),
                        entity_type=entity_type,
                        label_confidence=label_confidence,
                        data_origin=item.get("data_origin", "live"),
                        source=item.get("source", L2_SOURCE_NAME),
                    ))
                except (KeyError, ValueError) as e:
                    continue
            return positions
        except (json.JSONDecodeError, OSError):
            return []

    def save_current_positions(self, positions: list[WhalePosition]) -> None:
        """Save current positions as serialized JSON for next comparison."""
        if not self.state_path:
            return
        data = [p.as_dict() for p in positions]
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_health(self) -> SourceHealth:
        """Return current source health."""
        has_state = self.state_path and self.state_path.exists()
        return SourceHealth(
            source_name=L2_SOURCE_NAME,
            source_group=L2_SOURCE_GROUP,
            status=SourceStatus.OK if has_state else SourceStatus.DEGRADED,
            last_success_at=_utc_now() if has_state else None,
            success_count=1 if has_state else 0,
            error_count=0,
            degraded_info=DegradedInfo(
                error_type="NO_PREVIOUS_STATE",
                occurred_at=_utc_now(),
                retryable=True,
                message_summary="No previous position state file found — first run or state reset",
            ) if not has_state else None,
        )
