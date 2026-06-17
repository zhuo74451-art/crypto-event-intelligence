"""L2 — Exposure Aggregator and Risk Overview.

Aggregates whale positions to provide:
- Biggest positions (top-N by USD value)
- Nearest liquidation risks (closest to liq price)
- Long exposure per coin (total USD)
- Short exposure per coin (total USD)
- Net whale exposure per coin
- High leverage positions
- Concentrated asset risk
- Liquidation distance bands
"""

from __future__ import annotations

from typing import Any, Optional

from market_radar.l1_hyperliquid_provider.provenance import utc_now_str


def aggregate_exposure(positions: list[dict]) -> dict:
    """Compute aggregate exposure metrics from WhalePosition list."""
    now = utc_now_str()

    # Per-coin aggregation
    coin_stats: dict[str, dict] = {}
    for p in positions:
        coin = p.get("coin", "???")
        direction = p.get("direction", "long")
        value = p.get("position_value_usd") or 0
        pnl = p.get("unrealized_pnl_usd") or 0
        leverage = p.get("leverage") or 0

        if coin not in coin_stats:
            coin_stats[coin] = {
                "long_value_usd": 0.0,
                "short_value_usd": 0.0,
                "long_count": 0,
                "short_count": 0,
                "total_pnl_usd": 0.0,
                "max_leverage": 0.0,
            }

        s = coin_stats[coin]
        if direction == "long":
            s["long_value_usd"] += value
            s["long_count"] += 1
        else:
            s["short_value_usd"] += value
            s["short_count"] += 1
        s["total_pnl_usd"] += pnl
        s["max_leverage"] = max(s["max_leverage"], leverage)

    # Per-coin net exposure
    per_coin: list[dict] = []
    for coin, s in sorted(coin_stats.items(), key=lambda x: x[1]["long_value_usd"] + x[1]["short_value_usd"], reverse=True):
        net_exposure = s["long_value_usd"] - s["short_value_usd"]
        per_coin.append({
            "coin": coin,
            "long_value_usd": round(s["long_value_usd"], 2),
            "short_value_usd": round(s["short_value_usd"], 2),
            "net_exposure_usd": round(net_exposure, 2),
            "long_count": s["long_count"],
            "short_count": s["short_count"],
            "total_pnl_usd": round(s["total_pnl_usd"], 2),
            "max_leverage": round(s["max_leverage"], 2),
        })

    # Biggest positions (top 10)
    sorted_by_value = sorted(
        positions,
        key=lambda p: p.get("position_value_usd", 0) or 0,
        reverse=True,
    )[:10]
    biggest_positions: list[dict] = []
    for p in sorted_by_value:
        biggest_positions.append({
            "address": p.get("address", "")[:10],
            "label": p.get("label", "Unknown"),
            "coin": p.get("coin"),
            "direction": p.get("direction"),
            "position_value_usd": p.get("position_value_usd"),
            "leverage": p.get("leverage"),
            "liquidation_distance_pct": p.get("liquidation_distance_pct"),
        })

    # Nearest liquidation risks (closest to liq, where distance is negative)
    liq_risks = [
        p for p in positions
        if p.get("liquidation_distance_pct") is not None
        and p["liquidation_distance_pct"] < 0
    ]
    liq_risks.sort(key=lambda p: p["liquidation_distance_pct"])  # most negative first
    nearest_liquidation: list[dict] = []
    for p in liq_risks[:10]:
        nearest_liquidation.append({
            "address": p.get("address", "")[:10],
            "label": p.get("label", "Unknown"),
            "coin": p.get("coin"),
            "direction": p.get("direction"),
            "position_value_usd": p.get("position_value_usd"),
            "liquidation_price": p.get("liquidation_price"),
            "liquidation_distance_pct": p.get("liquidation_distance_pct"),
        })

    # High leverage positions
    high_lev = [
        p for p in positions
        if (p.get("leverage") or 0) >= 10
    ]
    high_lev.sort(key=lambda p: p.get("leverage", 0), reverse=True)

    # Liquidation distance bands
    bands = {"critical_under_5pct": 0, "warning_5_15pct": 0, "safe_over_15pct": 0, "unknown": 0}
    for p in positions:
        d = p.get("liquidation_distance_pct")
        if d is None:
            bands["unknown"] += 1
        elif d < -5:
            bands["critical_under_5pct"] += 1
        elif d < -15:
            bands["warning_5_15pct"] += 1
        else:
            bands["safe_over_15pct"] += 1

    # Totals
    total_long_value = sum(p.get("position_value_usd", 0) or 0 for p in positions if p.get("direction") == "long")
    total_short_value = sum(p.get("position_value_usd", 0) or 0 for p in positions if p.get("direction") == "short")
    total_pnl = sum(p.get("unrealized_pnl_usd", 0) or 0 for p in positions)

    return {
        "generated_at_utc": now,
        "data_mode": positions[0].get("_provenance", {}).get("data_mode", "live") if positions else "unknown",
        "summary": {
            "total_positions": len(positions),
            "total_long_value_usd": round(total_long_value, 2),
            "total_short_value_usd": round(total_short_value, 2),
            "net_exposure_usd": round(total_long_value - total_short_value, 2),
            "total_unrealized_pnl_usd": round(total_pnl, 2),
            "unique_addresses": len(set(p.get("address", "") for p in positions)),
            "unique_coins": len(set(p.get("coin", "") for p in positions)),
        },
        "per_coin_exposure": per_coin,
        "biggest_positions": biggest_positions,
        "nearest_liquidation": nearest_liquidation,
        "high_leverage_positions": [
            {
                "address": p.get("address", "")[:10],
                "label": p.get("label", "Unknown"),
                "coin": p.get("coin"),
                "leverage": p.get("leverage"),
                "position_value_usd": p.get("position_value_usd"),
                "liquidation_distance_pct": p.get("liquidation_distance_pct"),
            }
            for p in high_lev[:10]
        ],
        "liquidation_distance_bands": bands,
    }
