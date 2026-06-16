"""L2 — Whale Watchlist.

Configurable filters for monitoring specific whales and assets.
Stateless — outputs filtering rules applied to current positions.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from market_radar.l1_hyperliquid_provider.provenance import utc_now_str

_WL_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WATCHLIST_CONFIG_PATH = os.path.join(
    os.path.abspath(os.path.join(_WL_SCRIPT_DIR, *[os.pardir] * 3)),
    "config", "mvpplus_watchlist_config.json",
)


def default_watchlist_config() -> dict:
    return {
        "version": "v1",
        "generated_at_utc": utc_now_str(),
        "priority_whales": {
            "description": "Addresses to always monitor regardless of position size",
            "addresses": [
                "0x6c8512516ce5669d35113a11ca8b8de322fd84f6",
                "0x8def9f50456c6c4e37fa5d3d57f108ed23992dae",
                "0x082e843a431aef031264dc232693dd710aedca88",
                "0x50b309f78e774a756a2230e1769729094cac9f20",
            ],
        },
        "priority_assets": {
            "description": "Assets to always monitor for whale activity",
            "assets": ["BTC", "ETH", "SOL", "HYPE"],
        },
        "filters": {
            "minimum_position_value_usd": 100_000,
            "maximum_liquidation_distance_pct": -10.0,
            "minimum_change_usd": 50_000,
            "size_change_threshold_pct": 5.0,
        },
    }


def load_watchlist_config(path: Optional[str] = None) -> dict:
    if path is None:
        path = WATCHLIST_CONFIG_PATH
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            pass
    cfg = default_watchlist_config()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except IOError:
        pass
    return cfg


def apply_watchlist(positions: list[dict], changes: list[dict]) -> dict:
    """Apply watchlist filters and return watchlist results."""
    config = load_watchlist_config()
    filters = config.get("filters", {})
    min_value = filters.get("minimum_position_value_usd", 100_000)
    max_liq_dist = filters.get("maximum_liquidation_distance_pct", -10.0)
    priority_addresses = config.get("priority_whales", {}).get("addresses", [])
    priority_assets = config.get("priority_assets", {}).get("assets", [])

    now = utc_now_str()

    # Priority whales
    priority_positions = [
        p for p in positions
        if p.get("address", "").lower() in {a.lower() for a in priority_addresses}
    ]

    # Positions above minimum value
    significant_positions = [
        p for p in positions
        if (p.get("position_value_usd") or 0) >= min_value
    ]

    # Critical liquidation watch
    liq_watch = [
        {
            "address": p.get("address", "")[:10],
            "label": p.get("label"),
            "coin": p.get("coin"),
            "liquidation_distance_pct": p.get("liquidation_distance_pct"),
            "position_value_usd": p.get("position_value_usd"),
        }
        for p in positions
        if p.get("liquidation_distance_pct") is not None
        and p["liquidation_distance_pct"] <= max_liq_dist
    ]

    # Significant changes
    significant_changes = [
        c for c in changes
        if c.get("change_type") not in ("no_change", "baseline_open_position")
        and c.get("coin", "").upper() in {a.upper() for a in priority_assets + ["ALL"]}
    ]

    return {
        "generated_at_utc": now,
        "config_version": config.get("version", "v1"),
        "filters_applied": filters,
        "priority_whales_tracked": len(priority_addresses),
        "priority_assets_tracked": len(priority_assets),
        "priority_whale_positions": len(priority_positions),
        "significant_positions_count": len(significant_positions),
        "liquidation_watch_count": len(liq_watch),
        "liquidation_watch": liq_watch,
        "significant_changes_count": len(significant_changes),
        "significant_changes": [
            {
                "coin": c.get("coin"),
                "change_type": c.get("change_type"),
                "label": c.get("label"),
            }
            for c in significant_changes[:10]
        ],
        "total_positions_monitored": len(positions),
    }
