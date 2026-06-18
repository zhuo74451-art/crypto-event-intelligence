"""Coordinated whale behavior detection.

Identifies time-correlated actions across addresses WITHOUT claiming collusion.
All detection is deterministic and based on observable on-chain patterns only.
No network, no I/O, no random.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional

from market_radar.whale_domain.models import (
    WhaleSnapshot, WhalePositionChange, _iso_to_ts,
)
from market_radar.whale_domain.portfolio_config import (
    PortfolioThresholds, DEFAULT_THRESHOLDS,
)

MIN_COORD_ADDRESSES = 2


def _make_action_id(action_type: str, coin: str, direction: str,
                    start: str, end: str) -> str:
    raw = f"coord:{action_type}:{coin}:{direction}:{start}:{end}"
    return "pw:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def detect_coordinated_direction_build(
    changes: list[WhalePositionChange],
    window_hours: Optional[float] = None,
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    if window_hours is None:
        window_hours = cfg.coordination_window_hours
    """Detect 2+ addresses increasing same coin in same direction within window.

    Returns list of coordinated action dicts.
    """
    # Group increases by (coin, direction)
    builds: dict[tuple[str, str], list[WhalePositionChange]] = {}
    for c in changes:
        ct = c.change_type
        if "increase" in ct:
            key = (c.coin, c.direction)
            if key not in builds:
                builds[key] = []
            builds[key].append(c)

    results = []
    for (coin, direction), group in builds.items():
        if len(group) >= MIN_COORD_ADDRESSES:
            addrs = list({c.address for c in group})
            entities = list({c.label or "unknown" for c in group})
            total_delta = sum(
                abs(c.delta.get("size_delta", 0) * 65000)
                for c in group if c.delta
            )
            timestamps = [
                _iso_to_ts(c.detected_at_utc) for c in group
            ]
            ts_window = max(timestamps) - min(timestamps) if timestamps else 0
            if ts_window <= window_hours * 3600:
                results.append({
                    "action_id": _make_action_id(
                        "coordinated_build", coin, direction,
                        group[0].detected_at_utc,
                        group[-1].detected_at_utc,
                    ),
                    "action_type": "coordinated_build",
                    "coin": coin,
                    "direction": direction,
                    "address_count": len(addrs),
                    "entity_count": len(set(entities)),
                    "total_delta_usd": round(total_delta, 2),
                    "time_window_start": min(c.detected_at_utc for c in group),
                    "time_window_end": max(c.detected_at_utc for c in group),
                    "confidence": "medium",
                    "reason_codes": ["same_direction_increase", "multi_address"],
                    "addresses": addrs,
                })
    return results


def detect_coordinated_reduction(
    changes: list[WhalePositionChange],
    window_hours: Optional[float] = None,
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    if window_hours is None:
        window_hours = cfg.coordination_window_hours
    """Detect 2+ addresses reducing same coin in same direction within window."""
    reductions: dict[tuple[str, str], list[WhalePositionChange]] = {}
    for c in changes:
        ct = c.change_type
        if "reduce" in ct:
            key = (c.coin, c.direction)
            if key not in reductions:
                reductions[key] = []
            reductions[key].append(c)

    results = []
    for (coin, direction), group in reductions.items():
        if len(group) >= MIN_COORD_ADDRESSES:
            addrs = list({c.address for c in group})
            entities = list({c.label or "unknown" for c in group})
            total_delta = sum(
                abs(c.delta.get("size_delta", 0) * 65000)
                for c in group if c.delta
            )
            timestamps = [
                _iso_to_ts(c.detected_at_utc) for c in group
            ]
            ts_window = max(timestamps) - min(timestamps) if timestamps else 0
            if ts_window <= window_hours * 3600:
                results.append({
                    "action_id": _make_action_id(
                        "coordinated_reduction", coin, direction,
                        group[0].detected_at_utc,
                        group[-1].detected_at_utc,
                    ),
                    "action_type": "coordinated_reduction",
                    "coin": coin,
                    "direction": direction,
                    "address_count": len(addrs),
                    "entity_count": len(set(entities)),
                    "total_delta_usd": round(total_delta, 2),
                    "time_window_start": min(c.detected_at_utc for c in group),
                    "time_window_end": max(c.detected_at_utc for c in group),
                    "confidence": "medium",
                    "reason_codes": ["same_direction_reduce", "multi_address"],
                    "addresses": addrs,
                })
    return results


def detect_coordinated_flip(
    changes: list[WhalePositionChange],
    window_hours: Optional[float] = None,
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    if window_hours is None:
        window_hours = cfg.coordination_window_hours
    """Detect 2+ addresses flipping same coin direction within window."""
    flips: dict[str, list[WhalePositionChange]] = {}
    for c in changes:
        ct = c.change_type
        if "flip" in ct:
            coin = c.coin
            if coin not in flips:
                flips[coin] = []
            flips[coin].append(c)

    results = []
    for coin, group in flips.items():
        if len(group) >= MIN_COORD_ADDRESSES:
            addrs = list({c.address for c in group})
            entities = list({c.label or "unknown" for c in group})
            directions = list({c.direction for c in group})
            timestamps = [
                _iso_to_ts(c.detected_at_utc) for c in group
            ]
            ts_window = max(timestamps) - min(timestamps) if timestamps else 0
            if ts_window <= window_hours * 3600:
                results.append({
                    "action_id": _make_action_id(
                        "coordinated_flip", coin, "_".join(directions),
                        group[0].detected_at_utc,
                        group[-1].detected_at_utc,
                    ),
                    "action_type": "coordinated_flip",
                    "coin": coin,
                    "direction": "_".join(directions),
                    "address_count": len(addrs),
                    "entity_count": len(set(entities)),
                    "total_delta_usd": 0.0,
                    "time_window_start": min(c.detected_at_utc for c in group),
                    "time_window_end": max(c.detected_at_utc for c in group),
                    "confidence": "low",
                    "reason_codes": ["same_coin_flip", "multi_address"],
                    "addresses": addrs,
                })
    return results


def detect_divergent_behavior(
    changes: list[WhalePositionChange],
    window_hours: Optional[float] = None,
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    if window_hours is None:
        window_hours = cfg.coordination_window_hours
    """Detect opposing direction actions on same coin within window."""
    by_coin: dict[str, list[WhalePositionChange]] = {}
    for c in changes:
        ct = c.change_type
        if "increase" in ct or "reduce" in ct or "flip" in ct:
            coin = c.coin
            if coin not in by_coin:
                by_coin[coin] = []
            by_coin[coin].append(c)

    results = []
    for coin, group in by_coin.items():
        longs = [c for c in group if c.direction == "long"]
        shorts = [c for c in group if c.direction == "short"]
        if longs and shorts:
            addrs = list({c.address for c in longs + shorts})
            timestamps = [_iso_to_ts(c.detected_at_utc) for c in group]
            ts_window = max(timestamps) - min(timestamps) if timestamps else 0
            if ts_window <= window_hours * 3600:
                results.append({
                    "action_id": _make_action_id(
                        "divergent_behavior", coin, "mixed",
                        min(c.detected_at_utc for c in group),
                        max(c.detected_at_utc for c in group),
                    ),
                    "action_type": "divergent_behavior",
                    "coin": coin,
                    "direction": "mixed",
                    "address_count": len(addrs),
                    "entity_count": 0,
                    "total_delta_usd": 0.0,
                    "time_window_start": min(c.detected_at_utc for c in group),
                    "time_window_end": max(c.detected_at_utc for c in group),
                    "confidence": "medium",
                    "reason_codes": ["opposing_directions", "same_coin"],
                    "addresses": addrs,
                })
    return results


def detect_liquidation_cluster_formation(
    snapshots: list[WhaleSnapshot],
    threshold_pct: float = 5.0,
) -> list[dict]:
    """Detect 2+ addresses within threshold_pct of liquidation."""
    clustered = [
        s for s in snapshots
        if s.liquidation_distance_pct is not None
        and 0 < s.liquidation_distance_pct <= threshold_pct
    ]
    if len(clustered) >= MIN_COORD_ADDRESSES:
        addrs = list({s.address for s in clustered})
        coins = list({s.coin for s in clustered})
        return [{
            "action_id": _make_action_id(
                "liquidation_cluster", "_".join(coins),
                "mixed", "", "",
            ),
            "action_type": "liquidation_cluster",
            "coin": "_".join(coins[:3]),
            "direction": "mixed",
            "address_count": len(addrs),
            "entity_count": 0,
            "total_delta_usd": 0.0,
            "time_window_start": "",
            "time_window_end": "",
            "confidence": "high",
            "reason_codes": ["liquidation_cluster", "multi_address"],
            "addresses": addrs,
        }]
    return []


def detect_all_coordinated_actions(
    changes: list[WhalePositionChange],
    snapshots: list[WhaleSnapshot],
    window_hours: Optional[float] = None,
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    """Run all coordination detectors and return combined results."""
    if window_hours is None:
        window_hours = cfg.coordination_window_hours
    results: list[dict] = []
    results.extend(detect_coordinated_direction_build(changes, window_hours, cfg))
    results.extend(detect_coordinated_reduction(changes, window_hours, cfg))
    results.extend(detect_coordinated_flip(changes, window_hours, cfg))
    results.extend(detect_divergent_behavior(changes, window_hours, cfg))
    results.extend(detect_liquidation_cluster_formation(snapshots))
    return results
