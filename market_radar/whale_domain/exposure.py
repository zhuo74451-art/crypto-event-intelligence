"""Whale Domain — exposure aggregation.

Pure deterministic aggregation of whale positions into exposure metrics.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from market_radar.whale_domain.models import (
    WhaleSnapshot, WhaleExposure,
)


def aggregate_exposure(
    snapshots: list[WhaleSnapshot],
    generated_at_utc: str = "",
) -> WhaleExposure:
    """Compute aggregate exposure from a list of snapshots.

    Returns a WhaleExposure with per-coin breakdown, biggest positions,
    nearest liquidation risks, high leverage positions, and liq bands.
    """
    # Per-coin stats
    coin_stats: dict[str, dict] = {}
    for snap in snapshots:
        coin = snap.coin
        value = snap.position_value_usd
        pnl = snap.unrealized_pnl_usd or 0
        lev = snap.leverage

        if coin not in coin_stats:
            coin_stats[coin] = {
                "long_value_usd": 0.0, "short_value_usd": 0.0,
                "long_count": 0, "short_count": 0,
                "total_pnl_usd": 0.0, "max_leverage": 0.0,
            }
        s = coin_stats[coin]
        if snap.direction == "long":
            s["long_value_usd"] += value
            s["long_count"] += 1
        else:
            s["short_value_usd"] += value
            s["short_count"] += 1
        s["total_pnl_usd"] += pnl
        s["max_leverage"] = max(s["max_leverage"], lev)

    # Per-coin exposure
    per_coin = []
    for coin, s in sorted(
        coin_stats.items(),
        key=lambda x: x[1]["long_value_usd"] + x[1]["short_value_usd"],
        reverse=True,
    ):
        net = s["long_value_usd"] - s["short_value_usd"]
        per_coin.append({
            "coin": coin,
            "long_value_usd": round(s["long_value_usd"], 2),
            "short_value_usd": round(s["short_value_usd"], 2),
            "net_exposure_usd": round(net, 2),
            "long_count": s["long_count"],
            "short_count": s["short_count"],
            "total_pnl_usd": round(s["total_pnl_usd"], 2),
            "max_leverage": round(s["max_leverage"], 2),
        })

    # Biggest positions (top 10)
    sorted_by_value = sorted(
        snapshots, key=lambda s: s.position_value_usd, reverse=True,
    )[:10]
    biggest = [
        {
            "address": s.address[:10],
            "label": s.label or "Unknown",
            "coin": s.coin,
            "direction": s.direction,
            "position_value_usd": s.position_value_usd,
            "leverage": s.leverage,
            "liquidation_distance_pct": s.liquidation_distance_pct,
        }
        for s in sorted_by_value
    ]

    # Nearest liquidation (closest to liq, smallest positive distance)
    with_liq = [
        s for s in snapshots
        if s.liquidation_distance_pct is not None
        and s.liquidation_distance_pct > 0
    ]
    with_liq.sort(key=lambda s: s.liquidation_distance_pct)
    nearest = [
        {
            "address": s.address[:10],
            "label": s.label or "Unknown",
            "coin": s.coin,
            "direction": s.direction,
            "position_value_usd": s.position_value_usd,
            "liquidation_price": s.liquidation_price,
            "liquidation_distance_pct": s.liquidation_distance_pct,
        }
        for s in with_liq[:10]
    ]

    # High leverage positions
    high_lev = sorted(
        [s for s in snapshots if s.leverage >= 10],
        key=lambda s: s.leverage, reverse=True,
    )[:10]
    high_lev_list = [
        {
            "address": s.address[:10],
            "label": s.label or "Unknown",
            "coin": s.coin,
            "leverage": s.leverage,
            "position_value_usd": s.position_value_usd,
            "liquidation_distance_pct": s.liquidation_distance_pct,
        }
        for s in high_lev
    ]

    # Liquidation distance bands
    bands = {
        "critical_under_5pct": 0,
        "warning_5_15pct": 0,
        "safe_over_15pct": 0,
        "unknown": 0,
    }
    for s in snapshots:
        d = s.liquidation_distance_pct
        if d is None:
            bands["unknown"] += 1
        elif d <= 5:
            bands["critical_under_5pct"] += 1
        elif d <= 15:
            bands["warning_5_15pct"] += 1
        else:
            bands["safe_over_15pct"] += 1

    # Aggregates
    total_long = sum(s.position_value_usd for s in snapshots if s.direction == "long")
    total_short = sum(s.position_value_usd for s in snapshots if s.direction == "short")
    total_pnl = sum(s.unrealized_pnl_usd or 0 for s in snapshots)

    return WhaleExposure(
        total_positions=len(snapshots),
        total_long_value_usd=round(total_long, 2),
        total_short_value_usd=round(total_short, 2),
        net_exposure_usd=round(total_long - total_short, 2),
        total_unrealized_pnl_usd=round(total_pnl, 2),
        unique_addresses=len({s.address for s in snapshots}),
        unique_coins=len({s.coin for s in snapshots}),
        per_coin_exposure=per_coin,
        biggest_positions=biggest,
        nearest_liquidation=nearest,
        high_leverage_positions=high_lev_list,
        liquidation_distance_bands=bands,
        generated_at_utc=generated_at_utc,
    )
