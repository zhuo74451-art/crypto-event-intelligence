"""MVP+ Lane 2 — Whale Position Change & Risk Engine.

Detects position changes between two snapshots of WhalePosition data:
  - POSITION_OPENED: new position appeared
  - POSITION_INCREASED: size grew
  - POSITION_REDUCED: size shrank
  - POSITION_CLOSED: position disappeared
  - DIRECTION_FLIPPED: LONG→SHORT or SHORT→LONG
  - NO_CHANGE: same position within threshold

Design:
  - One-shot: single comparison, no daemon/cron
  - Deterministic: same inputs → same outputs
  - Graceful degradation: missing snapshots → empty changes
  - No secret/credential handling
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.shared.contracts import (
    WhalePosition,
    WhalePositionChange,
    ChangeType,
    RiskLevel,
    PositionSide,
    EntityType,
    LabelConfidence,
    SourceHealth,
    SourceStatus,
)

# ── Constants ─────────────────────────────────────────────────────────────────

SIZE_CHANGE_THRESHOLD_PCT = 1.0  # Minimum % change to report (avoid floating noise)
VERSION = "mvp+v1.0-l2"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _position_key(pos: WhalePosition) -> tuple[str, str]:
    """Unique key: (address, asset). A whale can have only one side per asset at a time on HL."""
    return (pos.address.lower(), pos.asset.upper())


def _classify_risk(
    change_type: ChangeType,
    delta_usd: Optional[float],
    change_pct: Optional[float],
    current_position_usd: float,
    leverage: Optional[float],
) -> tuple[RiskLevel, list[str]]:
    """Classify the risk level of a position change."""
    factors: list[str] = []

    if change_type == ChangeType.POSITION_OPENED and current_position_usd >= 10_000_000:
        factors.append("large_new_position")
        return RiskLevel.ELEVATED, factors

    if change_type == ChangeType.DIRECTION_FLIPPED:
        factors.append("direction_flipped")
        return RiskLevel.ELEVATED, factors

    if change_type == ChangeType.POSITION_CLOSED and current_position_usd >= 5_000_000:
        factors.append("large_position_closed")
        return RiskLevel.ELEVATED, factors

    if delta_usd is not None and change_pct is not None:
        if delta_usd >= 5_000_000 or change_pct >= 50:
            factors.append("large_delta")
            if leverage and leverage >= 10:
                factors.append("high_leverage_on_large_move")
                return RiskLevel.CRITICAL, factors
            return RiskLevel.ELEVATED, factors

        if delta_usd >= 1_000_000 or change_pct >= 20:
            factors.append("notable_delta")
            return RiskLevel.NORMAL, factors

    if leverage and leverage >= 20:
        factors.append("very_high_leverage")

    if not factors:
        return RiskLevel.LOW, factors

    return RiskLevel.NORMAL, factors


@dataclass
class L2Result:
    """Aggregated result from a single L2 run."""
    changes: list[WhalePositionChange] = field(default_factory=list)
    source_health: list[SourceHealth] = field(default_factory=list)
    total_previous: int = 0
    total_current: int = 0
    total_changes: int = 0
    run_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "lane": "L2",
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_previous": self.total_previous,
            "total_current": self.total_current,
            "total_changes": self.total_changes,
            "change_count": len(self.changes),
            "error": self.error,
        }


def compute_changes(
    current_positions: list[WhalePosition],
    previous_positions: Optional[list[WhalePosition]] = None,
) -> L2Result:
    """Compare two position snapshots and return detected changes.

    Args:
        current_positions: List of WhalePosition from current snapshot.
        previous_positions: List of WhalePosition from previous snapshot.
                            If None or empty, all current positions are reported as POSITION_OPENED.

    Returns:
        L2Result with all detected changes.
    """
    run_id = uuid.uuid4().hex[:12]
    started_at = _utc_now()
    prev_map: dict[tuple[str, str], WhalePosition] = {}
    curr_map: dict[tuple[str, str], WhalePosition] = {}

    changes: list[WhalePositionChange] = []
    health: list[SourceHealth] = []

    curr_by_address: dict[str, list[WhalePosition]] = {}
    for pos in current_positions:
        key = _position_key(pos)
        curr_map[key] = pos
        addr = pos.address.lower()
        if addr not in curr_by_address:
            curr_by_address[addr] = []
        curr_by_address[addr].append(pos)

    if previous_positions:
        for pos in previous_positions:
            key = _position_key(pos)
            prev_map[key] = pos

    now = _utc_now()

    # ── Detect changes OR new positions ──
    for key, curr in curr_map.items():
        prev = prev_map.get(key)

        if prev is None:
            # POSITION_OPENED — no previous position
            risk, factors = _classify_risk(
                ChangeType.POSITION_OPENED, None, None,
                curr.position_size_usd, curr.leverage,
            )
            changes.append(WhalePositionChange(
                address=curr.address,
                asset=curr.asset,
                side=curr.side,
                change_type=ChangeType.POSITION_OPENED,
                current_position_size_usd=curr.position_size_usd,
                current_observed_at=curr.observed_at,
                current_entry_price=curr.entry_price,
                current_mark_price=curr.mark_price,
                current_unrealized_pnl_usd=curr.unrealized_pnl_usd,
                current_liquidation_price=curr.liquidation_price,
                current_liquidation_distance_pct=curr.liquidation_distance_pct,
                current_leverage=curr.leverage,
                previous_position_size_usd=None,
                previous_observed_at=None,
                position_delta_usd=None,
                change_pct=None,
                risk_level=risk,
                risk_factors=factors,
                label=curr.label,
                entity_type=curr.entity_type,
                label_confidence=curr.label_confidence,
                data_origin=curr.data_origin,
            ))
        else:
            # Position existed before — check for changes
            ctype = ChangeType.NO_CHANGE
            delta_usd: Optional[float] = None
            change_pct: Optional[float] = None

            size_diff = curr.position_size_usd - prev.position_size_usd
            if prev.position_size_usd > 0:
                change_pct = (size_diff / prev.position_size_usd) * 100.0
            else:
                change_pct = 0.0

            # Direction flip?
            if prev.side != curr.side:
                ctype = ChangeType.DIRECTION_FLIPPED
                delta_usd = None
                change_pct = None
            elif curr.position_size_usd == 0:
                ctype = ChangeType.POSITION_CLOSED
                delta_usd = -prev.position_size_usd
                change_pct = -100.0
            elif abs(change_pct or 0) > SIZE_CHANGE_THRESHOLD_PCT:
                if size_diff > 0:
                    ctype = ChangeType.POSITION_INCREASED
                else:
                    ctype = ChangeType.POSITION_REDUCED
                delta_usd = size_diff
            else:
                ctype = ChangeType.NO_CHANGE
                delta_usd = 0.0
                change_pct = 0.0

            risk, factors = _classify_risk(
                ctype, delta_usd, change_pct,
                curr.position_size_usd, curr.leverage,
            )

            changes.append(WhalePositionChange(
                address=curr.address,
                asset=curr.asset,
                side=curr.side,
                change_type=ctype,
                current_position_size_usd=curr.position_size_usd,
                current_observed_at=curr.observed_at,
                current_entry_price=curr.entry_price,
                current_mark_price=curr.mark_price,
                current_unrealized_pnl_usd=curr.unrealized_pnl_usd,
                current_liquidation_price=curr.liquidation_price,
                current_liquidation_distance_pct=curr.liquidation_distance_pct,
                current_leverage=curr.leverage,
                previous_position_size_usd=prev.position_size_usd,
                previous_observed_at=prev.observed_at,
                position_delta_usd=delta_usd,
                change_pct=change_pct,
                risk_level=risk,
                risk_factors=factors,
                label=curr.label,
                entity_type=curr.entity_type,
                label_confidence=curr.label_confidence,
                data_origin=curr.data_origin,
            ))

    # ── Detect CLOSED positions (in previous but not in current) ──
    if previous_positions:
        for key, prev in prev_map.items():
            if key not in curr_map:
                # Position was in previous snapshot but disappeared
                risk, factors = _classify_risk(
                    ChangeType.POSITION_CLOSED, -prev.position_size_usd, -100.0,
                    0.0, prev.leverage,
                )
                changes.append(WhalePositionChange(
                    address=prev.address,
                    asset=prev.asset,
                    side=prev.side,
                    change_type=ChangeType.POSITION_CLOSED,
                    current_position_size_usd=0.0,
                    current_observed_at=now,
                    current_entry_price=None,
                    current_mark_price=None,
                    current_unrealized_pnl_usd=None,
                    current_liquidation_price=None,
                    current_liquidation_distance_pct=None,
                    current_leverage=None,
                    previous_position_size_usd=prev.position_size_usd,
                    previous_observed_at=prev.observed_at,
                    position_delta_usd=-prev.position_size_usd,
                    change_pct=-100.0,
                    risk_level=risk,
                    risk_factors=factors,
                    label=prev.label,
                    entity_type=prev.entity_type,
                    label_confidence=prev.label_confidence,
                    data_origin=prev.data_origin,
                ))

    # ── Source health ──
    health.append(SourceHealth(
        source_name="whale_engine",
        source_group="hyperliquid",
        status=SourceStatus.OK,
        last_success_at=now,
        success_count=1,
        error_count=0,
    ))

    completed_at = _utc_now()
    return L2Result(
        changes=changes,
        source_health=health,
        total_previous=len(prev_map),
        total_current=len(curr_map),
        total_changes=len(changes),
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
    )


def main():
    """CLI entry: run L2 with sample data for testing."""
    from market_radar.shared.contracts import WhalePosition, PositionSide
    now = _utc_now()

    # Create sample current positions
    current = [
        WhalePosition(
            address="0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
            asset="BTC", side=PositionSide.LONG,
            position_size_usd=50_000_000.0, observed_at=now,
            entry_price=89000.0, mark_price=92000.0,
            leverage=5.0, unrealized_pnl_usd=1_500_000.0,
            liquidation_price=75000.0,
            liquidation_distance_pct=18.48,
            label="Matrixport Related",
            entity_type=EntityType.FUND_WALLET,
            label_confidence=LabelConfidence.MEDIUM,
        ),
    ]

    # No previous → all opened
    result = compute_changes(current)
    print(f"L2 Run: {result.run_id}")
    print(f"  Previous: {result.total_previous}, Current: {result.total_current}")
    print(f"  Changes detected: {result.total_changes}")
    for c in result.changes:
        d = c.as_dict()
        print(f"    {d['address'][:10]}... | {d['asset']:5s} | {d['change_type']:20s} | "
              f"risk={d['risk_level']} | delta_usd={d.get('position_delta_usd') or 'N/A'}")
    return 0


if __name__ == "__main__":
    main()
