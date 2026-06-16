"""L2 — Whale Behavior Summary.

Computes trading behavior metrics from available position snapshots.
With insufficient history, outputs insufficient_history markers.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from market_radar.l1_hyperliquid_provider.provenance import utc_now_str


def compute_behavior(positions: list[dict], changes: list[dict]) -> dict:
    """Compute behavior summary from current positions and change history.

    Returns dict with metrics, or insufficient_history flags when
    sample size is too small for meaningful conclusions.
    """
    now = utc_now_str()
    address_positions: dict[str, list[dict]] = defaultdict(list)
    address_changes: dict[str, list[dict]] = defaultdict(list)

    for p in positions:
        address_positions[p.get("address", "")].append(p)
    for c in changes:
        address_changes[c.get("address", "")].append(c)

    per_address: list[dict] = []
    for address, pos_list in address_positions.items():
        label = pos_list[0].get("label", "Unknown")
        coin_set = set(p.get("coin", "") for p in pos_list)
        total_value = sum(p.get("position_value_usd", 0) or 0 for p in pos_list)
        total_pnl = sum(p.get("unrealized_pnl_usd", 0) or 0 for p in pos_list)

        avg_leverage = (
            sum(p.get("leverage", 0) or 0 for p in pos_list) / len(pos_list)
        ) if pos_list else 0

        long_count = sum(1 for p in pos_list if p.get("direction") == "long")
        short_count = sum(1 for p in pos_list if p.get("direction") == "short")

        # Most traded assets (sorted by value)
        coin_values = defaultdict(float)
        for p in pos_list:
            coin_values[p.get("coin", "")] += p.get("position_value_usd", 0) or 0
        most_traded = sorted(coin_values.items(), key=lambda x: x[1], reverse=True)[:5]

        # Largest observed position
        largest = max(pos_list, key=lambda p: p.get("position_value_usd", 0) or 0) if pos_list else None

        addr_changes = address_changes.get(address, [])
        real_changes = [c for c in addr_changes if c.get("change_type") not in ("no_change", "baseline_open_position")]
        change_frequency = len(real_changes)

        liq_events = [c for c in real_changes if any("liquidation" in f for f in c.get("risk_flags", []))]
        liq_risk_count = len(liq_events)

        entry: dict = {
            "address_short": address[:10] if address else "?",
            "label": label,
            "asset_count": len(coin_set),
            "most_traded_assets": [{"coin": c, "value_usd": round(v, 2)} for c, v in most_traded],
            "long_short_ratio": {
                "long_count": long_count,
                "short_count": short_count,
                "bias": "long" if long_count > short_count else ("short" if short_count > long_count else "neutral"),
            },
            "typical_leverage": round(avg_leverage, 2),
            "largest_position": {
                "coin": largest.get("coin") if largest else None,
                "value_usd": largest.get("position_value_usd") if largest else None,
                "direction": largest.get("direction") if largest else None,
            } if largest else None,
            "total_value_usd": round(total_value, 2),
            "total_pnl_usd": round(total_pnl, 2),
            "position_change_count": change_frequency,
            "liquidation_risk_count": liq_risk_count,
        }

        # Insufficient history checks
        if change_frequency == 0:
            entry["change_history_note"] = "insufficient_history: no changes detected yet"
        if len(pos_list) <= 1:
            entry["diversification_note"] = "insufficient_history: need more positions"
        if coin_set:
            entry["most_traded_note"] = f"tracking {len(coin_set)} assets" if len(coin_set) >= 2 else "single_asset_focus"

        per_address.append(entry)

    # Aggregate
    has_sufficient_data = len(per_address) >= 1 and sum(e.get("position_change_count", 0) for e in per_address) > 0

    return {
        "generated_at_utc": now,
        "data_sufficiency": "sufficient" if has_sufficient_data else "insufficient_history",
        "total_addresses_analyzed": len(per_address),
        "per_address": sorted(per_address, key=lambda e: e["total_value_usd"], reverse=True),
        "aggregate": {
            "total_value_usd": round(sum(e["total_value_usd"] for e in per_address), 2),
            "total_pnl_usd": round(sum(e["total_pnl_usd"] for e in per_address), 2),
            "avg_leverage": round(
                sum(e["typical_leverage"] for e in per_address) / len(per_address), 2
            ) if per_address else 0,
            "long_bias_count": sum(1 for e in per_address if e["long_short_ratio"]["bias"] == "long"),
            "short_bias_count": sum(1 for e in per_address if e["long_short_ratio"]["bias"] == "short"),
        } if per_address else None,
        "metadata": {
            "note": "Behavior summary computed from single snapshot. Multi-snapshot history required for trend analysis."
        },
    }
