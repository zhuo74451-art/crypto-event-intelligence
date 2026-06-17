"""L2 — Alert Candidate Generator.

Generates alert candidates from position changes and risk analysis.
Only generates — does NOT send. No Telegram, no X, no email.

Alert types:
- large_new_position: Whale opened > $1M position
- large_increase: Whale added > $500K to existing position
- direction_flip: Whale reversed direction
- liquidation_critical: Position within 5% of liquidation
- high_leverage: Whale opened/added at > 10x
- concentrated_exposure: Single position > $5M in one coin
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.l1_hyperliquid_provider.provenance import utc_now_str

ALERT_RULES = {
    "large_new_position": {"label": "Large New Position", "min_value_usd": 1_000_000, "severity": "high"},
    "large_increase": {"label": "Large Increase", "min_delta_usd": 500_000, "severity": "medium"},
    "large_decrease": {"label": "Large Decrease", "min_delta_usd": 500_000, "severity": "medium"},
    "direction_flip": {"label": "Direction Flip", "severity": "high"},
    "liquidation_critical": {"label": "Liquidation Critical", "max_distance_pct": 5.0, "severity": "critical"},
    # Note: liquidation_distance_pct is now positive (distance FROM liquidation).
    # Smaller value = closer to liquidation. <= 5% means within 5% of liq.
    "high_leverage": {"label": "High Leverage", "min_leverage": 10.0, "severity": "medium"},
    "concentrated_exposure": {"label": "Concentrated Exposure", "min_value_usd": 5_000_000, "severity": "medium"},
}


def generate_alert_candidates(
    positions: list[dict],
    changes: list[dict],
    exposure: dict,
) -> list[dict]:
    """Generate alert candidates from current state.

    Returns list of alert candidate dicts, empty if none triggered.
    """
    now = utc_now_str()
    alerts: list[dict] = []
    alert_ids: set[str] = set()

    for change in changes:
        ct = change.get("change_type", "")
        coin = change.get("coin", "")
        label = change.get("label", "Unknown")
        delta = change.get("delta", {})
        risk_flags = change.get("risk_flags", [])
        addr_short = (change.get("address", "") or "")[:10]

        # Direction flip
        if "flip" in ct:
            alert_key = f"flip_{addr_short}_{coin}"
            if alert_key not in alert_ids:
                alerts.append({
                    "alert_id": alert_key,
                    "alert_type": "direction_flip",
                    "rule": ALERT_RULES["direction_flip"],
                    "coin": coin,
                    "label": label,
                    "address_short": addr_short,
                    "change_type": ct,
                    "severity": ALERT_RULES["direction_flip"]["severity"],
                    "generated_at_utc": now,
                })
                alert_ids.add(alert_key)

        # Large new position
        if "open" in ct:
            pos_value = change.get("current", {}).get("position_value_usd", 0) or 0
            min_val = ALERT_RULES["large_new_position"]["min_value_usd"]
            if pos_value >= min_val:
                alert_key = f"large_open_{addr_short}_{coin}"
                if alert_key not in alert_ids:
                    alerts.append({
                        "alert_id": alert_key,
                        "alert_type": "large_new_position",
                        "rule": ALERT_RULES["large_new_position"],
                        "coin": coin,
                        "label": label,
                        "address_short": addr_short,
                        "value_usd": round(pos_value, 2),
                        "severity": ALERT_RULES["large_new_position"]["severity"],
                        "generated_at_utc": now,
                    })
                    alert_ids.add(alert_key)

        # Large increase
        if "increase" in ct:
            val_delta = delta.get("position_value_delta_usd", 0) or 0
            min_delta = ALERT_RULES["large_increase"]["min_delta_usd"]
            if abs(val_delta) >= min_delta:
                alert_key = f"large_inc_{addr_short}_{coin}"
                if alert_key not in alert_ids:
                    alerts.append({
                        "alert_id": alert_key,
                        "alert_type": "large_increase",
                        "rule": ALERT_RULES["large_increase"],
                        "coin": coin,
                        "label": label,
                        "address_short": addr_short,
                        "delta_usd": round(val_delta, 2),
                        "severity": ALERT_RULES["large_increase"]["severity"],
                        "generated_at_utc": now,
                    })
                    alert_ids.add(alert_key)

        # Large decrease
        if "reduce" in ct:
            val_delta = delta.get("position_value_delta_usd", 0) or 0
            min_delta = ALERT_RULES["large_decrease"]["min_delta_usd"]
            if abs(val_delta) >= min_delta:
                alert_key = f"large_dec_{addr_short}_{coin}"
                if alert_key not in alert_ids:
                    alerts.append({
                        "alert_id": alert_key,
                        "alert_type": "large_decrease",
                        "rule": ALERT_RULES["large_decrease"],
                        "coin": coin,
                        "label": label,
                        "address_short": addr_short,
                        "delta_usd": round(val_delta, 2),
                        "severity": ALERT_RULES["large_decrease"]["severity"],
                        "generated_at_utc": now,
                    })
                    alert_ids.add(alert_key)

        # Liquidation critical
        liq_dist = change.get("current", {}).get("liquidation_distance_pct")
        max_dist = ALERT_RULES["liquidation_critical"]["max_distance_pct"]
        if liq_dist is not None and liq_dist > 0 and liq_dist <= max_dist:
            alert_key = f"liq_crit_{addr_short}_{coin}"
            if alert_key not in alert_ids:
                alerts.append({
                    "alert_id": alert_key,
                    "alert_type": "liquidation_critical",
                    "rule": ALERT_RULES["liquidation_critical"],
                    "coin": coin,
                    "label": label,
                    "address_short": addr_short,
                    "liquidation_distance_pct": liq_dist,
                    "severity": ALERT_RULES["liquidation_critical"]["severity"],
                    "generated_at_utc": now,
                })
                alert_ids.add(alert_key)

    # Position-level alerts (from current state, not changes)
    for pos in positions:
        addr_short = (pos.get("address", "") or "")[:10]
        coin = pos.get("coin", "")
        label = pos.get("label", "Unknown")
        leverage = pos.get("leverage", 0) or 0
        pos_value = pos.get("position_value_usd", 0) or 0

        # High leverage
        if leverage >= ALERT_RULES["high_leverage"]["min_leverage"]:
            alert_key = f"high_lev_{addr_short}_{coin}"
            if alert_key not in alert_ids:
                alerts.append({
                    "alert_id": alert_key,
                    "alert_type": "high_leverage",
                    "rule": ALERT_RULES["high_leverage"],
                    "coin": coin,
                    "label": label,
                    "address_short": addr_short,
                    "leverage": leverage,
                    "position_value_usd": round(pos_value, 2),
                    "severity": ALERT_RULES["high_leverage"]["severity"],
                    "generated_at_utc": now,
                })
                alert_ids.add(alert_key)

        # Concentrated exposure
        if pos_value >= ALERT_RULES["concentrated_exposure"]["min_value_usd"]:
            alert_key = f"conc_ex_{addr_short}_{coin}"
            if alert_key not in alert_ids:
                alerts.append({
                    "alert_id": alert_key,
                    "alert_type": "concentrated_exposure",
                    "rule": ALERT_RULES["concentrated_exposure"],
                    "coin": coin,
                    "label": label,
                    "address_short": addr_short,
                    "value_usd": round(pos_value, 2),
                    "severity": ALERT_RULES["concentrated_exposure"]["severity"],
                    "generated_at_utc": now,
                })
                alert_ids.add(alert_key)

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 99))

    return alerts


def format_alert_text(alert: dict) -> str:
    """Format an alert candidate as human-readable text.

    Does NOT send. Returns text string for preview only.
    """
    atype = alert["alert_type"]
    coin = alert.get("coin", "?")
    label = alert.get("label", "Unknown")
    severity = alert.get("severity", "low").upper()

    if atype == "direction_flip":
        return f"[{severity}] {label} FLIPPED direction on {coin}: {alert.get('change_type', '?')}"
    elif atype == "large_new_position":
        return f"[{severity}] {label} opened LARGE {coin} position: ${alert.get('value_usd', 0):,.0f}"
    elif atype == "large_increase":
        return f"[{severity}] {label} INCREASED {coin} by ${alert.get('delta_usd', 0):+,.0f}"
    elif atype == "large_decrease":
        return f"[{severity}] {label} REDUCED {coin} by ${alert.get('delta_usd', 0):+,.0f}"
    elif atype == "liquidation_critical":
        return f"[{severity}] {label} {coin} LIQUIDATION CRITICAL: {alert.get('liquidation_distance_pct', 0):+.2f}%"
    elif atype == "high_leverage":
        return f"[{severity}] {label} HIGH LEVERAGE {coin}: {alert.get('leverage', 0)}x"
    elif atype == "concentrated_exposure":
        return f"[{severity}] {label} CONCENTRATED {coin}: ${alert.get('value_usd', 0):,.0f}"
    return f"[{severity}] {label} {atype}: {coin}"
