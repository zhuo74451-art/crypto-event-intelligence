"""Whale Domain — watchlist filtering.

Configurable watchlist: filters positions by priority addresses,
assets, minimum value, and maximum liquidation distance.
Pure deterministic logic.
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.whale_domain.models import (
    WhaleSnapshot, WhalePositionChange,
    LARGE_POSITION_USD, LIQ_DISTANCE_CRITICAL,
)

DEFAULT_PRIORITY_ADDRESSES = [
    "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
    "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
    "0x082e843a431aef031264dc232693dd710aedca88",
    "0x50b309f78e774a756a2230e1769729094cac9f20",
]

DEFAULT_PRIORITY_ASSETS = ["BTC", "ETH", "SOL", "HYPE"]


def apply_watchlist(
    snapshots: list[WhaleSnapshot],
    changes: list[WhalePositionChange],
    generated_at_utc: str = "",
    priority_addresses: Optional[list[str]] = None,
    priority_assets: Optional[list[str]] = None,
    min_position_value: float = LARGE_POSITION_USD,
    max_liq_distance: float = LIQ_DISTANCE_CRITICAL,
) -> dict:
    """Apply watchlist filters to positions and changes.

    Returns a watchlist report dict with counts and filtered entries.
    """
    if priority_addresses is None:
        priority_addresses = DEFAULT_PRIORITY_ADDRESSES
    if priority_assets is None:
        priority_assets = DEFAULT_PRIORITY_ASSETS

    pa_lower = {a.lower() for a in priority_addresses}
    pa_assets_upper = {a.upper() for a in priority_assets}

    # Priority whale positions
    priority_positions = [
        s for s in snapshots if s.address.lower() in pa_lower
    ]

    # Significant positions above min value
    significant = [
        s for s in snapshots if s.position_value_usd >= min_position_value
    ]

    # Liquidation watch
    liq_watch = [
        {
            "address": s.address[:10],
            "label": s.label,
            "coin": s.coin,
            "liquidation_distance_pct": s.liquidation_distance_pct,
            "position_value_usd": s.position_value_usd,
        }
        for s in snapshots
        if s.liquidation_distance_pct is not None
        and 0 < s.liquidation_distance_pct <= max_liq_distance
    ]

    # Significant changes
    sig_changes = [
        {
            "coin": c.coin,
            "change_type": c.change_type,
            "label": c.label,
            "direction": c.direction,
        }
        for c in changes
        if c.coin.upper() in pa_assets_upper
        or c.coin.upper() in ["ALL"]
    ]

    return {
        "generated_at_utc": generated_at_utc,
        "priority_addresses_tracked": len(priority_addresses),
        "priority_assets_tracked": len(priority_assets),
        "priority_whale_positions": len(priority_positions),
        "significant_positions_count": len(significant),
        "liquidation_watch_count": len(liq_watch),
        "liquidation_watch": liq_watch[:10],
        "significant_changes_count": len(sig_changes),
        "significant_changes": sig_changes[:10],
        "total_positions_monitored": len(snapshots),
    }
