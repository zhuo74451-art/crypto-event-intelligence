"""Portfolio metrics — deterministic multi-address exposure computation.

All functions are pure: given position snapshots, compute aggregate metrics.
No network, no I/O, no random, no system clock.
"""

from __future__ import annotations

from typing import Optional

from market_radar.whale_domain.models import WhaleSnapshot


def compute_gross_exposure(snapshots: list[WhaleSnapshot]) -> float:
    """Sum of absolute position values across all positions."""
    return sum(abs(s.position_value_usd) for s in snapshots)


def compute_net_exposure(snapshots: list[WhaleSnapshot]) -> float:
    """Net directional exposure: long position value minus short position value."""
    long_val = compute_long_exposure(snapshots)
    short_val = compute_short_exposure(snapshots)
    return long_val - short_val


def compute_long_exposure(snapshots: list[WhaleSnapshot]) -> float:
    """Sum of position values for long positions."""
    return sum(s.position_value_usd for s in snapshots if s.signed_size > 0)


def compute_short_exposure(snapshots: list[WhaleSnapshot]) -> float:
    """Sum of absolute position values for short positions."""
    return sum(abs(s.position_value_usd) for s in snapshots if s.signed_size < 0)


def compute_long_short_ratio(long_usd: float, short_usd: float) -> Optional[float]:
    """Ratio of long to short exposure, or None if short is zero."""
    if short_usd == 0:
        return None if long_usd == 0 else float("inf")
    return round(long_usd / short_usd, 4)


def compute_top_n_concentration(
    snapshots: list[WhaleSnapshot], n: int,
) -> Optional[float]:
    """Concentration ratio: top N positions / gross exposure.

    Formula: sum(top N position values) / gross_exposure
    Returns None if gross is zero.
    """
    gross = compute_gross_exposure(snapshots)
    if gross == 0:
        return None
    values = sorted(
        [abs(s.position_value_usd) for s in snapshots], reverse=True,
    )
    top_n_sum = sum(values[:n])
    return round(top_n_sum / gross, 4)


def compute_hhi(snapshots: list[WhaleSnapshot]) -> Optional[float]:
    """Herfindahl-Hirschman Index for position concentration.

    Formula: sum((pos_value / gross)^2) for each position
    Range: 0 to 1 (1 = single position dominates)
    Returns None if gross is zero.
    """
    gross = compute_gross_exposure(snapshots)
    if gross == 0:
        return None
    hhi = sum(
        (abs(s.position_value_usd) / gross) ** 2 for s in snapshots
    )
    return round(hhi, 4)


def compute_weighted_leverage(snapshots: list[WhaleSnapshot]) -> Optional[float]:
    """Portfolio-weighted average leverage.

    Formula: sum(pos_value * leverage) / sum(pos_value)
    Only non-zero positions count. Returns None if no non-zero positions.
    """
    total_value = 0.0
    total_weighted = 0.0
    for s in snapshots:
        v = abs(s.position_value_usd)
        if v > 0 and s.leverage is not None:
            total_value += v
            total_weighted += v * s.leverage
    if total_value == 0:
        return None
    return round(total_weighted / total_value, 4)


def compute_weighted_liquidation_distance(
    snapshots: list[WhaleSnapshot],
) -> Optional[float]:
    """Portfolio-weighted average liquidation distance.

    Formula: sum(pos_value * liq_dist) / sum(pos_value)
    Only positions with non-null liq distance count.
    Returns None if no eligible positions.
    """
    total_value = 0.0
    total_weighted = 0.0
    for s in snapshots:
        v = abs(s.position_value_usd)
        if v > 0 and s.liquidation_distance_pct is not None:
            total_value += v
            total_weighted += v * s.liquidation_distance_pct
    if total_value == 0:
        return None
    return round(total_weighted / total_value, 4)


def compute_exposure_within_liq_pct(
    snapshots: list[WhaleSnapshot], threshold_pct: float,
) -> tuple[int, float]:
    """Count and total value of positions within threshold_pct of liquidation.

    Returns (count, total_exposure_usd).
    Only positive distances <= threshold are counted (negative = anomalous).
    """
    count = 0
    total = 0.0
    for s in snapshots:
        d = s.liquidation_distance_pct
        if d is not None and 0 < d <= threshold_pct:
            count += 1
            total += abs(s.position_value_usd)
    return count, total


def compute_profitable_exposure(
    snapshots: list[WhaleSnapshot],
) -> float:
    """Sum of position values with positive unrealized PnL."""
    return sum(
        abs(s.position_value_usd) for s in snapshots
        if s.unrealized_pnl_usd is not None and s.unrealized_pnl_usd > 0
    )


def compute_unprofitable_exposure(
    snapshots: list[WhaleSnapshot],
) -> float:
    """Sum of position values with negative unrealized PnL."""
    return sum(
        abs(s.position_value_usd) for s in snapshots
        if s.unrealized_pnl_usd is not None and s.unrealized_pnl_usd < 0
    )


def compute_same_coin_opposing_exposure(
    snapshots: list[WhaleSnapshot],
) -> dict[str, dict]:
    """For each coin, compute long vs short from different addresses.

    Returns dict keyed by coin:
      {"coin": {"long_usd": X, "short_usd": Y, "net_usd": Z, "has_opposing": bool}}
    Only coins with both long and short positions are flagged.
    """
    coin_map: dict[str, dict] = {}
    for s in snapshots:
        coin = s.coin
        if coin not in coin_map:
            coin_map[coin] = {"long_usd": 0.0, "short_usd": 0.0}
        if s.signed_size > 0:
            coin_map[coin]["long_usd"] += s.position_value_usd
        elif s.signed_size < 0:
            coin_map[coin]["short_usd"] += abs(s.position_value_usd)

    result = {}
    for coin, v in coin_map.items():
        v["net_usd"] = round(v["long_usd"] - v["short_usd"], 2)
        v["has_opposing"] = v["long_usd"] > 0 and v["short_usd"] > 0
        result[coin] = v
    return result


def compute_cross_address_same_direction(
    snapshots: list[WhaleSnapshot],
) -> list[dict]:
    """Find coins where 2+ addresses hold the same direction.

    Returns list of {coin, direction, address_count, total_exposure_usd}.
    """
    coin_dir: dict[str, dict[str, set]] = {}
    coin_exposure: dict[str, dict[str, float]] = {}
    for s in snapshots:
        coin = s.coin
        direction = "long" if s.signed_size > 0 else "short"
        if coin not in coin_dir:
            coin_dir[coin] = {"long": set(), "short": set()}
            coin_exposure[coin] = {"long": 0.0, "short": 0.0}
        coin_dir[coin][direction].add(s.address)
        coin_exposure[coin][direction] += abs(s.position_value_usd)

    result = []
    for coin, dirs in coin_dir.items():
        for direction in ("long", "short"):
            count = len(dirs[direction])
            if count >= 2:
                result.append({
                    "coin": coin,
                    "direction": direction,
                    "address_count": count,
                    "total_exposure_usd": round(
                        coin_exposure[coin][direction], 2,
                    ),
                })
    return result


def count_addresses(snapshots: list[WhaleSnapshot]) -> int:
    """Count unique addresses with non-zero positions."""
    return len({s.address for s in snapshots if s.signed_size != 0})


def count_coins(snapshots: list[WhaleSnapshot]) -> int:
    """Count unique coins with non-zero positions."""
    return len({s.coin for s in snapshots if s.signed_size != 0})


def filter_valid_snapshots(
    snapshots: list[WhaleSnapshot],
) -> list[WhaleSnapshot]:
    """Filter out zero-size and stale-quality snapshots."""
    return [s for s in snapshots if s.signed_size != 0]


def assess_data_quality(snapshots: list[WhaleSnapshot]) -> str:
    """Assess overall data quality: complete/partial/stale/incomplete."""
    if not snapshots:
        return "incomplete"
    missing_mark = sum(1 for s in snapshots if s.mark_price is None or s.mark_price <= 0)
    missing_liq = sum(1 for s in snapshots if s.liquidation_distance_pct is None)
    total = len(snapshots)
    if missing_mark == 0 and missing_liq == 0:
        return "complete"
    if missing_mark / total < 0.3 and missing_liq / total < 0.3:
        return "partial"
    return "incomplete"
