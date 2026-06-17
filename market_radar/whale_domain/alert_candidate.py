"""Whale Domain — alert candidate generation.

Generates alert candidates from position changes and risk analysis.
Only generates — never sends. No send mechanism in domain.

Alert types:
  - large_new_position: Whale opened > $1M position
  - large_increase: Whale added > $500K to existing position
  - large_decrease: Whale reduced > $500K
  - direction_flip: Whale reversed direction
  - liquidation_critical: Position within 5% of liquidation
  - high_leverage: Position at > 10x
  - concentrated_exposure: Single position > $5M
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.whale_domain.models import (
    WhaleSnapshot, WhalePositionChange, WhaleAlertCandidate,
    LIQ_DISTANCE_CRITICAL, HIGH_LEVERAGE_THRESHOLD,
    LARGE_POSITION_USD, MASSIVE_POSITION_USD,
)

ALERT_RULES = {
    "large_new_position": {
        "label": "Large New Position", "min_value_usd": LARGE_POSITION_USD,
        "severity": "high",
    },
    "large_increase": {
        "label": "Large Increase", "min_delta_usd": 500_000,
        "severity": "medium",
    },
    "large_decrease": {
        "label": "Large Decrease", "min_delta_usd": 500_000,
        "severity": "medium",
    },
    "direction_flip": {
        "label": "Direction Flip", "severity": "high",
    },
    "liquidation_critical": {
        "label": "Liquidation Critical",
        "max_distance_pct": LIQ_DISTANCE_CRITICAL,
        "severity": "critical",
    },
    "high_leverage": {
        "label": "High Leverage",
        "min_leverage": HIGH_LEVERAGE_THRESHOLD,
        "severity": "medium",
    },
    "concentrated_exposure": {
        "label": "Concentrated Exposure",
        "min_value_usd": MASSIVE_POSITION_USD,
        "severity": "medium",
    },
}


def _format_message(alert_type: str, label: str, coin: str,
                    change_type: str = "", value: Optional[float] = None) -> str:
    """Format a human-readable alert message."""
    if alert_type == "direction_flip":
        return f"{label} FLIPPED direction on {coin}: {change_type}"
    elif alert_type == "large_new_position":
        return f"{label} opened LARGE {coin} position: ${value:,.0f}"
    elif alert_type == "large_increase":
        return f"{label} INCREASED {coin} by ${abs(value or 0):,.0f}"
    elif alert_type == "large_decrease":
        return f"{label} REDUCED {coin} by ${abs(value or 0):,.0f}"
    elif alert_type == "liquidation_critical":
        return f"{label} {coin} LIQUIDATION CRITICAL: {(value or 0):+.2f}% from liq"
    elif alert_type == "high_leverage":
        return f"{label} HIGH LEVERAGE {coin}: {(value or 0)}x"
    elif alert_type == "concentrated_exposure":
        return f"{label} CONCENTRATED {coin}: ${value:,.0f}"
    return f"{label} {alert_type}: {coin}"


def generate_alert_candidates(
    snapshots: list[WhaleSnapshot],
    changes: list[WhalePositionChange],
    generated_at_utc: str = "",
) -> list[WhaleAlertCandidate]:
    """Generate alert candidates from position changes and current state.

    Returns list of WhaleAlertCandidate objects, or empty list if none.
    """
    alerts: list[WhaleAlertCandidate] = []
    seen_ids: set[str] = set()

    for change in changes:
        ct = change.change_type
        coin = change.coin
        label = change.label or "Unknown"
        addr_short = (change.address or "")[:10]
        delta = change.delta or {}

        # Direction flip
        if "flip" in ct:
            alert = WhaleAlertCandidate(
                alert_id=WhaleAlertCandidate.compute_id(
                    "direction_flip", change.address, coin, generated_at_utc,
                ),
                alert_type="direction_flip",
                severity=ALERT_RULES["direction_flip"]["severity"],
                coin=coin, label=label,
                address_short=addr_short,
                message=_format_message("direction_flip", label, coin, ct),
                generated_at_utc=generated_at_utc,
            )
            if alert.alert_id not in seen_ids:
                alerts.append(alert)
                seen_ids.add(alert.alert_id)

        # Large new position
        if "open" in ct and change.current:
            pos_value = change.current.get("position_value_usd", 0) or 0
            if pos_value >= ALERT_RULES["large_new_position"]["min_value_usd"]:
                alert = WhaleAlertCandidate(
                    alert_id=WhaleAlertCandidate.compute_id(
                        "large_new_position", change.address, coin, generated_at_utc,
                    ),
                    alert_type="large_new_position",
                    severity=ALERT_RULES["large_new_position"]["severity"],
                    coin=coin, label=label,
                    address_short=addr_short,
                    observed_value=pos_value,
                    message=_format_message("large_new_position", label, coin,
                                            value=pos_value),
                    generated_at_utc=generated_at_utc,
                )
                if alert.alert_id not in seen_ids:
                    alerts.append(alert)
                    seen_ids.add(alert.alert_id)

        # Large increase
        if "increase" in ct:
            val_delta = abs(delta.get("position_value_delta_usd", 0) or 0)
            if val_delta >= ALERT_RULES["large_increase"]["min_delta_usd"]:
                alert = WhaleAlertCandidate(
                    alert_id=WhaleAlertCandidate.compute_id(
                        "large_increase", change.address, coin, generated_at_utc,
                    ),
                    alert_type="large_increase",
                    severity=ALERT_RULES["large_increase"]["severity"],
                    coin=coin, label=label,
                    address_short=addr_short,
                    observed_value=delta.get("position_value_delta_usd", 0),
                    message=_format_message("large_increase", label, coin,
                                            value=delta.get("position_value_delta_usd", 0)),
                    generated_at_utc=generated_at_utc,
                )
                if alert.alert_id not in seen_ids:
                    alerts.append(alert)
                    seen_ids.add(alert.alert_id)

        # Large decrease
        if "reduce" in ct:
            val_delta = abs(delta.get("position_value_delta_usd", 0) or 0)
            if val_delta >= ALERT_RULES["large_decrease"]["min_delta_usd"]:
                alert = WhaleAlertCandidate(
                    alert_id=WhaleAlertCandidate.compute_id(
                        "large_decrease", change.address, coin, generated_at_utc,
                    ),
                    alert_type="large_decrease",
                    severity=ALERT_RULES["large_decrease"]["severity"],
                    coin=coin, label=label,
                    address_short=addr_short,
                    observed_value=delta.get("position_value_delta_usd", 0),
                    message=_format_message("large_decrease", label, coin,
                                            value=delta.get("position_value_delta_usd", 0)),
                    generated_at_utc=generated_at_utc,
                )
                if alert.alert_id not in seen_ids:
                    alerts.append(alert)
                    seen_ids.add(alert.alert_id)

        # Liquidation critical
        if change.current:
            liq_dist = change.current.get("liquidation_distance_pct")
            max_dist = ALERT_RULES["liquidation_critical"]["max_distance_pct"]
            if liq_dist is not None and liq_dist > 0 and liq_dist <= max_dist:
                alert = WhaleAlertCandidate(
                    alert_id=WhaleAlertCandidate.compute_id(
                        "liquidation_critical", change.address, coin, generated_at_utc,
                    ),
                    alert_type="liquidation_critical",
                    severity=ALERT_RULES["liquidation_critical"]["severity"],
                    coin=coin, label=label,
                    address_short=addr_short,
                    observed_value=liq_dist,
                    message=_format_message("liquidation_critical", label, coin,
                                            value=liq_dist),
                    generated_at_utc=generated_at_utc,
                )
                if alert.alert_id not in seen_ids:
                    alerts.append(alert)
                    seen_ids.add(alert.alert_id)

    # Position-level alerts (from current state, not changes)
    for snap in snapshots:
        addr_short = snap.address[:10]
        label = snap.label or "Unknown"
        coin = snap.coin

        # High leverage
        if snap.leverage >= ALERT_RULES["high_leverage"]["min_leverage"]:
            aid = WhaleAlertCandidate.compute_id(
                "high_leverage", snap.address, coin, generated_at_utc,
            )
            if aid not in seen_ids:
                alerts.append(WhaleAlertCandidate(
                    alert_id=aid,
                    alert_type="high_leverage",
                    severity=ALERT_RULES["high_leverage"]["severity"],
                    coin=coin, label=label,
                    address_short=addr_short,
                    observed_value=snap.leverage,
                    message=_format_message("high_leverage", label, coin,
                                            value=snap.leverage),
                    generated_at_utc=generated_at_utc,
                ))
                seen_ids.add(aid)

        # Concentrated exposure
        if snap.position_value_usd >= ALERT_RULES["concentrated_exposure"]["min_value_usd"]:
            aid = WhaleAlertCandidate.compute_id(
                "concentrated_exposure", snap.address, coin, generated_at_utc,
            )
            if aid not in seen_ids:
                alerts.append(WhaleAlertCandidate(
                    alert_id=aid,
                    alert_type="concentrated_exposure",
                    severity=ALERT_RULES["concentrated_exposure"]["severity"],
                    coin=coin, label=label,
                    address_short=addr_short,
                    observed_value=snap.position_value_usd,
                    message=_format_message("concentrated_exposure", label, coin,
                                            value=snap.position_value_usd),
                    generated_at_utc=generated_at_utc,
                ))
                seen_ids.add(aid)

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda a: severity_order.get(a.severity, 99))

    return alerts
