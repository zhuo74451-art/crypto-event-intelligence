"""Portfolio Intelligence Engine — orchestrates all portfolio analysis.

Combines metrics, risk rules, coordinated behavior, and change detection
into a single deterministic pipeline. No network, no I/O, no random.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

from market_radar.whale_domain.models import (
    WhaleSnapshot, WhalePositionChange, extract_snapshot,
    make_position_key,
)
from market_radar.whale_domain.portfolio_models import (
    WhalePortfolioSnapshot, AddressExposureSummary, CoinExposureSummary,
    EntityExposureSummary, CoordinatedAction, PortfolioChange,
    PortfolioRiskFinding, PortfolioIntelligenceSummary,
)
from market_radar.whale_domain.portfolio_metrics import (
    compute_gross_exposure, compute_net_exposure,
    compute_long_exposure, compute_short_exposure,
    compute_top_n_concentration, compute_hhi,
    compute_weighted_leverage, compute_weighted_liquidation_distance,
    compute_exposure_within_liq_pct,
    compute_profitable_exposure, compute_unprofitable_exposure,
    compute_same_coin_opposing_exposure,
    compute_cross_address_same_direction,
    count_addresses, count_coins,
    filter_valid_snapshots, assess_data_quality,
)
from market_radar.whale_domain.portfolio_risk import evaluate_all_rules
from market_radar.whale_domain.portfolio_coordination import (
    detect_all_coordinated_actions,
)
from market_radar.whale_domain.portfolio_change import (
    detect_all_portfolio_changes,
)


def _snapshot_id(captured_at: str, addr_count: int) -> str:
    raw = f"pw:{captured_at}:{addr_count}"
    return "pw:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_address_summaries(
    snapshots: list[WhaleSnapshot],
) -> list[AddressExposureSummary]:
    """Build per-address exposure summaries."""
    addr_map: dict[str, dict] = {}
    for s in snapshots:
        if s.signed_size == 0:
            continue
        if s.address not in addr_map:
            addr_map[s.address] = {
                "address": s.address,
                "label": s.label,
                "gross": 0.0,
                "long": 0.0,
                "short": 0.0,
                "coins": set(),
                "largest": {"symbol": "", "value": 0.0},
                "total_lev_value": 0.0,
                "total_lev_weight": 0.0,
                "closest_liq": None,
                "pnl": 0.0,
                "flags": [],
            }
        a = addr_map[s.address]
        val = abs(s.position_value_usd)
        a["gross"] += val
        if s.signed_size > 0:
            a["long"] += s.position_value_usd
        else:
            a["short"] += abs(s.position_value_usd)
        a["coins"].add(s.coin)
        if val > a["largest"]["value"]:
            a["largest"] = {"symbol": s.coin, "value": val}
        if s.leverage is not None and val > 0:
            a["total_lev_value"] += val
            a["total_lev_weight"] += val * s.leverage
        d = s.liquidation_distance_pct
        if d is not None and d > 0:
            if a["closest_liq"] is None or d < a["closest_liq"]:
                a["closest_liq"] = d
        if s.unrealized_pnl_usd is not None:
            a["pnl"] += s.unrealized_pnl_usd

    summaries = []
    for addr, a in addr_map.items():
        wl = None
        if a["total_lev_weight"] > 0 and a["total_lev_value"] > 0:
            wl = round(a["total_lev_weight"] / a["total_lev_value"], 2)
        summaries.append(AddressExposureSummary(
            address=a["address"],
            label=a["label"],
            gross_exposure_usd=round(a["gross"], 2),
            net_exposure_usd=round(a["long"] - a["short"], 2),
            long_exposure_usd=round(a["long"], 2),
            short_exposure_usd=round(a["short"], 2),
            coin_count=len(a["coins"]),
            largest_position=a["largest"],
            weighted_leverage=wl,
            closest_liquidation_distance_pct=a["closest_liq"],
            risk_flags=a["flags"],
            unrealized_pnl_usd=round(a["pnl"], 2) if a["pnl"] != 0 else None,
        ))
    return summaries


def build_coin_summaries(
    snapshots: list[WhaleSnapshot],
) -> list[CoinExposureSummary]:
    """Build per-coin exposure summaries."""
    coin_map: dict[str, dict] = {}
    for s in snapshots:
        if s.signed_size == 0:
            continue
        coin = s.coin
        if coin not in coin_map:
            coin_map[coin] = {
                "long": 0.0, "short": 0.0,
                "addrs_long": set(), "addrs_short": set(),
                "lev_value": 0.0, "lev_weight": 0.0,
                "liq_2pct": 0, "liq_5pct": 0,
            }
        c = coin_map[coin]
        if s.signed_size > 0:
            c["long"] += s.position_value_usd
            c["addrs_long"].add(s.address)
        else:
            c["short"] += abs(s.position_value_usd)
            c["addrs_short"].add(s.address)
        val = abs(s.position_value_usd)
        if s.leverage is not None and val > 0:
            c["lev_value"] += val
            c["lev_weight"] += val * s.leverage
        d = s.liquidation_distance_pct
        if d is not None and d > 0:
            if d <= 2.0:
                c["liq_2pct"] += 1
            if d <= 5.0:
                c["liq_5pct"] += 1

    summaries = []
    for coin, c in coin_map.items():
        total = c["long"] + c["short"]
        max_side = max(c["long"], c["short"])
        conc_ratio = round(max_side / total, 4) if total > 0 else None
        wl = round(c["lev_weight"] / c["lev_value"], 2) if c["lev_value"] > 0 else None
        summaries.append(CoinExposureSummary(
            coin=coin,
            total_long_usd=round(c["long"], 2),
            total_short_usd=round(c["short"], 2),
            net_exposure_usd=round(c["long"] - c["short"], 2),
            address_count=len(c["addrs_long"] | c["addrs_short"]),
            long_address_count=len(c["addrs_long"]),
            short_address_count=len(c["addrs_short"]),
            concentration_ratio=conc_ratio,
            leverage_weighted=wl,
            liquidation_cluster={"within_2pct_count": c["liq_2pct"],
                                  "within_5pct_count": c["liq_5pct"]},
        ))
    return summaries


def analyze_portfolio(
    current_positions: list[WhaleSnapshot],
    previous_positions: Optional[list[WhaleSnapshot]] = None,
    changes: Optional[list[WhalePositionChange]] = None,
    detected_at_utc: str = "",
) -> WhalePortfolioSnapshot:
    """Run full portfolio intelligence pipeline.

    Args:
        current_positions: Current whale position snapshots.
        previous_positions: Previous snapshots (for change detection).
        changes: Position-level changes (for coordinated behavior).
        detected_at_utc: Timestamp for this analysis run.

    Returns:
        WhalePortfolioSnapshot with all portfolio-level intelligence.
    """
    valid = filter_valid_snapshots(current_positions)
    gross = compute_gross_exposure(valid)
    net = compute_net_exposure(valid)
    long_exp = compute_long_exposure(valid)
    short_exp = compute_short_exposure(valid)
    wl = compute_weighted_leverage(valid)
    addr_count = count_addresses(valid)
    coin_count = count_coins(valid)

    liq_2pct_count, liq_2pct_val = compute_exposure_within_liq_pct(valid, 2.0)
    liq_5pct_count, liq_5pct_val = compute_exposure_within_liq_pct(valid, 5.0)

    # Summaries
    addr_summaries = build_address_summaries(valid)
    coin_summaries = build_coin_summaries(valid)

    # Risk rules
    change_dicts = [c.to_dict() if hasattr(c, 'to_dict') else {}
                    for c in (changes or [])]
    risk_findings_raw = evaluate_all_rules(
        valid, changes=change_dicts,
        previous_gross=compute_gross_exposure(previous_positions)
        if previous_positions else None,
        reference_time=detected_at_utc,
        snapshot_id=_snapshot_id(detected_at_utc, addr_count),
    )
    risk_findings = [
        PortfolioRiskFinding(**f) for f in risk_findings_raw
    ]

    # Coordinated actions
    coord_raw = detect_all_coordinated_actions(
        changes or [], valid,
    )
    coordinated = [
        CoordinatedAction(**c) for c in coord_raw
    ]

    # Portfolio changes
    change_raw = detect_all_portfolio_changes(
        previous_positions, valid, detected_at_utc,
    )
    portfolio_changes = [
        PortfolioChange(**c) for c in change_raw
    ]

    # Determine data quality
    data_quality = assess_data_quality(valid)

    return WhalePortfolioSnapshot(
        snapshot_id=_snapshot_id(detected_at_utc, addr_count),
        captured_at=detected_at_utc,
        addresses=list({s.address for s in valid}),
        positions_count=len(valid),
        gross_exposure_usd=round(gross, 2),
        net_exposure_usd=round(net, 2),
        long_exposure_usd=round(long_exp, 2),
        short_exposure_usd=round(short_exp, 2),
        weighted_leverage=wl,
        liquidation_exposure_usd={
            "within_2pct_count": liq_2pct_count,
            "within_2pct_value": round(liq_2pct_val, 2),
            "within_5pct_count": liq_5pct_count,
            "within_5pct_value": round(liq_5pct_val, 2),
        },
        address_summaries=addr_summaries,
        coin_summaries=coin_summaries,
        entity_summaries=[],
        risk_findings=risk_findings,
        coordinated_actions=coordinated,
        changes_since_previous=portfolio_changes,
        data_quality=data_quality,
    )
