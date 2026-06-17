"""Portfolio-level change detection between snapshots.

Compares previous and current portfolio states to identify aggregate shifts.
All functions are deterministic. No network, no I/O, no random.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from market_radar.whale_domain.models import WhaleSnapshot
from market_radar.whale_domain.portfolio_metrics import (
    compute_gross_exposure,
    compute_net_exposure,
    compute_long_exposure,
    compute_short_exposure,
    compute_weighted_leverage,
    compute_top_n_concentration,
    compute_hhi,
    compute_exposure_within_liq_pct,
)


def _change_id(change_type: str, snapshot_time: str, idx: int) -> str:
    raw = f"pc:{change_type}:{snapshot_time}:{idx}"
    return "pc:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _pct_change(prev: Optional[float], curr: float) -> Optional[float]:
    if prev is None or prev == 0:
        return None
    return round(((curr - prev) / prev) * 100, 2)


def detect_gross_exposure_change(
    prev_gross: Optional[float], curr_gross: float,
    snapshot_time: str,
) -> Optional[dict]:
    """Detect significant gross exposure change (>20% or absolute >$1M)."""
    pct = _pct_change(prev_gross, curr_gross)
    if pct is not None and abs(pct) > 20:
        direction = "expanded" if pct > 0 else "reduced"
        return {
            "change_id": _change_id("gross_exposure", snapshot_time, 0),
            "change_type": f"gross_exposure_{direction}",
            "description": f"Gross exposure {direction} by {abs(pct):.1f}% "
                           f"(prev=${prev_gross:,.0f}, curr=${curr_gross:,.0f})",
            "previous_value": prev_gross,
            "current_value": curr_gross,
            "delta": round(curr_gross - (prev_gross or 0), 2),
            "affected_addresses": [],
            "affected_coins": [],
        }
    return None


def detect_net_direction_shift(
    prev_net: Optional[float], curr_net: float,
    prev_long: Optional[float], curr_long: float,
    prev_short: Optional[float], curr_short: float,
    snapshot_time: str,
) -> Optional[dict]:
    """Detect net direction shift (flip from net long to net short or vice versa)."""
    if prev_net is None:
        return None
    if (prev_net >= 0 and curr_net < 0) or (prev_net < 0 and curr_net >= 0):
        direction = "long_to_short" if prev_net >= 0 else "short_to_long"
        return {
            "change_id": _change_id("net_direction_shift", snapshot_time, 0),
            "change_type": f"net_direction_shift_{direction}",
            "description": f"Net exposure flipped from ${prev_net:,.0f} to ${curr_net:,.0f}",
            "previous_value": prev_net,
            "current_value": curr_net,
            "delta": round(curr_net - prev_net, 2),
            "affected_addresses": [],
            "affected_coins": [],
        }
    return None


def detect_concentration_change(
    prev_t1: Optional[float], curr_t1: float,
    prev_hhi: Optional[float], curr_hhi: float,
    snapshot_time: str,
) -> list[dict]:
    """Detect concentration increase or decrease."""
    results = []
    t1_pct = _pct_change(prev_t1, curr_t1)
    if t1_pct is not None and abs(t1_pct) > 10:
        direction = "increased" if t1_pct > 0 else "decreased"
        results.append({
            "change_id": _change_id("concentration_change", snapshot_time, 0),
            "change_type": f"concentration_{direction}",
            "description": f"Top-1 concentration {direction} by {abs(t1_pct):.1f}%",
            "previous_value": prev_t1,
            "current_value": curr_t1,
            "delta": round(curr_t1 - (prev_t1 or 0), 4),
            "affected_addresses": [],
            "affected_coins": [],
        })
    return results


def detect_leverage_change(
    prev_lev: Optional[float], curr_lev: float,
    snapshot_time: str,
) -> Optional[dict]:
    """Detect weighted leverage change >20%."""
    pct = _pct_change(prev_lev, curr_lev)
    if pct is not None and abs(pct) > 20:
        direction = "increased" if pct > 0 else "decreased"
        return {
            "change_id": _change_id("leverage_change", snapshot_time, 0),
            "change_type": f"leverage_{direction}",
            "description": f"Weighted leverage {direction} by {abs(pct):.1f}% "
                           f"(prev={prev_lev:.1f}x, curr={curr_lev:.1f}x)",
            "previous_value": prev_lev,
            "current_value": curr_lev,
            "delta": round(curr_lev - (prev_lev or 0), 2),
            "affected_addresses": [],
            "affected_coins": [],
        }
    return None


def detect_liquidation_cluster_change(
    prev_2pct: Optional[tuple[int, float]],
    curr_2pct: tuple[int, float],
    prev_5pct: Optional[tuple[int, float]],
    curr_5pct: tuple[int, float],
    snapshot_time: str,
) -> list[dict]:
    """Detect liquidation cluster formation or clearance."""
    results = []
    prev_count_2 = prev_2pct[0] if prev_2pct else 0
    if prev_count_2 < 2 and curr_2pct[0] >= 2:
        results.append({
            "change_id": _change_id("liq_cluster_formed_2pct", snapshot_time, 0),
            "change_type": "liq_cluster_formed_2pct",
            "description": f"Liquidation cluster formed: {curr_2pct[0]} positions within 2%",
            "previous_value": prev_count_2,
            "current_value": curr_2pct[0],
            "delta": curr_2pct[0] - prev_count_2,
            "affected_addresses": [],
            "affected_coins": [],
        })
    if prev_count_2 >= 2 and curr_2pct[0] < 2:
        results.append({
            "change_id": _change_id("liq_cluster_cleared_2pct", snapshot_time, 0),
            "change_type": "liq_cluster_cleared_2pct",
            "description": f"Liquidation cluster cleared at 2%",
            "previous_value": prev_count_2,
            "current_value": curr_2pct[0],
            "delta": curr_2pct[0] - prev_count_2,
            "affected_addresses": [],
            "affected_coins": [],
        })
    return results


def detect_new_and_exited_coins(
    prev_snapshots: Optional[list[WhaleSnapshot]],
    curr_snapshots: list[WhaleSnapshot],
    snapshot_time: str,
) -> list[dict]:
    """Detect new coins entered and coins fully exited."""
    results = []
    prev_coins = {s.coin for s in prev_snapshots or []}
    curr_coins = {s.coin for s in curr_snapshots}

    new_coins = curr_coins - prev_coins
    for coin in new_coins:
        results.append({
            "change_id": _change_id("new_coin_exposure", snapshot_time, len(results)),
            "change_type": "new_coin_exposure",
            "description": f"New coin exposure: {coin}",
            "previous_value": None,
            "current_value": None,
            "delta": None,
            "affected_addresses": [],
            "affected_coins": [coin],
        })

    exited_coins = prev_coins - curr_coins
    for coin in exited_coins:
        results.append({
            "change_id": _change_id("coin_exited", snapshot_time, len(results)),
            "change_type": "coin_exited",
            "description": f"Coin fully exited: {coin}",
            "previous_value": None,
            "current_value": None,
            "delta": None,
            "affected_addresses": [],
            "affected_coins": [coin],
        })

    return results


def detect_all_portfolio_changes(
    prev_snapshots: Optional[list[WhaleSnapshot]],
    curr_snapshots: list[WhaleSnapshot],
    snapshot_time: str = "",
) -> list[dict]:
    """Run all portfolio change detectors."""
    if not prev_snapshots:
        return []

    prev_gross = compute_gross_exposure(prev_snapshots)
    curr_gross = compute_gross_exposure(curr_snapshots)
    prev_net = compute_net_exposure(prev_snapshots)
    curr_net = compute_net_exposure(curr_snapshots)
    prev_long = compute_long_exposure(prev_snapshots)
    curr_long = compute_long_exposure(curr_snapshots)
    prev_short = compute_short_exposure(prev_snapshots)
    curr_short = compute_short_exposure(curr_snapshots)
    prev_lev = compute_weighted_leverage(prev_snapshots)
    curr_lev = compute_weighted_leverage(curr_snapshots)
    prev_t1 = compute_top_n_concentration(prev_snapshots, 1)
    curr_t1 = compute_top_n_concentration(curr_snapshots, 1)
    prev_hhi = compute_hhi(prev_snapshots)
    curr_hhi = compute_hhi(curr_snapshots)

    changes: list[dict] = []

    f = detect_gross_exposure_change(prev_gross, curr_gross, snapshot_time)
    if f:
        changes.append(f)

    f = detect_net_direction_shift(
        prev_net, curr_net,
        prev_long, curr_long,
        prev_short, curr_short,
        snapshot_time,
    )
    if f:
        changes.append(f)

    changes.extend(detect_concentration_change(prev_t1, curr_t1, prev_hhi, curr_hhi, snapshot_time))

    f = detect_leverage_change(prev_lev, curr_lev, snapshot_time)
    if f:
        changes.append(f)

    prev_2pct = compute_exposure_within_liq_pct(prev_snapshots, 2.0)
    curr_2pct = compute_exposure_within_liq_pct(curr_snapshots, 2.0)
    prev_5pct = compute_exposure_within_liq_pct(prev_snapshots, 5.0)
    curr_5pct = compute_exposure_within_liq_pct(curr_snapshots, 5.0)
    changes.extend(detect_liquidation_cluster_change(
        prev_2pct, curr_2pct, prev_5pct, curr_5pct, snapshot_time,
    ))

    changes.extend(detect_new_and_exited_coins(prev_snapshots, curr_snapshots, snapshot_time))

    return changes
