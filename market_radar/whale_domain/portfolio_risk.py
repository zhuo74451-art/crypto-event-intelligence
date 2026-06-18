"""Portfolio risk rules — deterministic, configurable, no AI.

Each rule is a pure function: given snapshots and metrics, returns findings.
No network, no I/O, no random, no system clock.
"""

from __future__ import annotations

import hashlib
from typing import Optional

from market_radar.whale_domain.models import WhaleSnapshot
from market_radar.whale_domain.portfolio_metrics import (
    compute_gross_exposure,
    compute_long_exposure,
    compute_short_exposure,
    compute_top_n_concentration,
    compute_hhi,
    compute_weighted_leverage,
    compute_exposure_within_liq_pct,
    compute_same_coin_opposing_exposure,
    assess_data_quality,
)
from market_radar.whale_domain.portfolio_config import (
    PortfolioThresholds, DEFAULT_THRESHOLDS,
)

SEVERITY_MAP = {
    "PR1": "medium",
    "PR2": "high",
    "PR3": "high",
    "PR4": "medium",
    "PR5": "high",
    "PR6": "critical",
    "PR7": "high",
    "PR8": "info",
    "PR9": "info",
    "PR10": "medium",
    "PR11": "low",
    "PR12": "low",
}


def _make_finding_id(rule_id: str, snapshot_id: str, idx: int) -> str:
    raw = f"pwf:{rule_id}:{snapshot_id}:{idx}"
    return "pwf:" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def rule_pr1_high_gross_exposure(
    gross_exposure: float,
    snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> Optional[dict]:
    """PR1: Gross exposure exceeds high_gross_exposure_usd threshold."""
    t = cfg.high_gross_exposure_usd
    if gross_exposure > t:
        return {
            "finding_id": _make_finding_id("PR1", snapshot_id, 0),
            "rule_id": "PR1_HIGH_GROSS_EXPOSURE",
            "severity": SEVERITY_MAP["PR1"],
            "threshold": f"> ${t:,.0f}",
            "observed_value": gross_exposure,
            "explanation": f"Total portfolio gross exposure ${gross_exposure:,.0f} exceeds "
                           f"${t:,.0f} threshold",
        }
    return None


def rule_pr2_net_direction_concentration(
    long_exposure: float, short_exposure: float, gross_exposure: float,
    snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> Optional[dict]:
    """PR2: Net direction > net_concentration_ratio of gross."""
    t = cfg.net_concentration_ratio
    if gross_exposure == 0:
        return None
    long_ratio = long_exposure / gross_exposure if gross_exposure else 0
    short_ratio = short_exposure / gross_exposure if gross_exposure else 0
    if long_ratio > t or short_ratio > t:
        dominant = "long" if long_ratio > short_ratio else "short"
        ratio = max(long_ratio, short_ratio)
        return {
            "finding_id": _make_finding_id("PR2", snapshot_id, 0),
            "rule_id": "PR2_NET_DIRECTION_CONCENTRATION",
            "severity": SEVERITY_MAP["PR2"],
            "threshold": f"{t * 100:.0f}% in one direction",
            "observed_value": round(ratio * 100, 1),
            "explanation": f"{dominant.upper()} bias: {ratio * 100:.1f}% of gross exposure",
        }
    return None


def rule_pr3_single_coin_concentration(
    snapshots: list[WhaleSnapshot], gross_exposure: float,
    snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    """PR3: Single coin > single_coin_concentration of gross."""
    findings = []
    t = cfg.single_coin_concentration
    if gross_exposure == 0:
        return findings
    coin_values: dict[str, float] = {}
    for s in snapshots:
        coin_values[s.coin] = coin_values.get(s.coin, 0) + abs(s.position_value_usd)
    for coin, value in coin_values.items():
        ratio = value / gross_exposure
        if ratio > t:
            findings.append({
                "finding_id": _make_finding_id("PR3", snapshot_id, len(findings)),
                "rule_id": "PR3_SINGLE_COIN_CONCENTRATION",
                "severity": SEVERITY_MAP["PR3"],
                "threshold": f"> {t * 100:.0f}% in single coin",
                "observed_value": round(ratio * 100, 1),
                "affected_coins": [coin],
                "explanation": f"{coin} represents {ratio * 100:.1f}% of gross exposure",
            })
    return findings


def rule_pr4_single_address_concentration(
    snapshots: list[WhaleSnapshot], gross_exposure: float,
    snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    """PR4: Single address > single_address_concentration of gross."""
    findings = []
    t = cfg.single_address_concentration
    if gross_exposure == 0:
        return findings
    addr_values: dict[str, float] = {}
    for s in snapshots:
        addr_values[s.address] = addr_values.get(s.address, 0) + abs(s.position_value_usd)
    for addr, value in addr_values.items():
        ratio = value / gross_exposure
        if ratio > t:
            findings.append({
                "finding_id": _make_finding_id("PR4", snapshot_id, len(findings)),
                "rule_id": "PR4_SINGLE_ADDRESS_CONCENTRATION",
                "severity": SEVERITY_MAP["PR4"],
                "threshold": f"> {t * 100:.0f}% in single address",
                "observed_value": round(ratio * 100, 1),
                "affected_addresses": [addr],
                "explanation": f"Address {addr[:10]} represents {ratio * 100:.1f}% of gross exposure",
            })
    return findings


def rule_pr5_high_weighted_leverage(
    weighted_leverage: Optional[float],
    snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> Optional[dict]:
    """PR5: Weighted portfolio leverage > high_weighted_leverage."""
    t = cfg.high_weighted_leverage
    if weighted_leverage is not None and weighted_leverage > t:
        return {
            "finding_id": _make_finding_id("PR5", snapshot_id, 0),
            "rule_id": "PR5_HIGH_WEIGHTED_LEVERAGE",
            "severity": SEVERITY_MAP["PR5"],
            "threshold": f"> {t}x weighted leverage",
            "observed_value": weighted_leverage,
            "explanation": f"Portfolio weighted leverage {weighted_leverage:.1f}x exceeds "
                           f"{t:.0f}x threshold",
        }
    return None


def rule_pr6_liquidation_cluster_2pct(
    snapshots: list[WhaleSnapshot], snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> Optional[dict]:
    """PR6: 2+ positions within liq_cluster_2pct % of liquidation."""
    t = cfg.liq_cluster_2pct
    count, total = compute_exposure_within_liq_pct(snapshots, t)
    if count >= 2:
        affected = [s for s in snapshots
                    if s.liquidation_distance_pct is not None
                    and 0 < s.liquidation_distance_pct <= t]
        return {
            "finding_id": _make_finding_id("PR6", snapshot_id, 0),
            "rule_id": "PR6_LIQUIDATION_CLUSTER_2PCT",
            "severity": SEVERITY_MAP["PR6"],
            "threshold": f"2+ positions within {t}% of liquidation",
            "observed_value": count,
            "affected_addresses": [s.address for s in affected],
            "affected_coins": list({s.coin for s in affected}),
            "explanation": f"{count} positions (${total:,.0f}) within {t}% of liquidation",
        }
    return None


def rule_pr7_liquidation_cluster_5pct(
    snapshots: list[WhaleSnapshot], snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> Optional[dict]:
    """PR7: 2+ positions within liq_cluster_5pct % of liquidation."""
    t = cfg.liq_cluster_5pct
    count, total = compute_exposure_within_liq_pct(snapshots, t)
    if count >= 2:
        affected = [s for s in snapshots
                    if s.liquidation_distance_pct is not None
                    and 0 < s.liquidation_distance_pct <= t]
        return {
            "finding_id": _make_finding_id("PR7", snapshot_id, 0),
            "rule_id": "PR7_LIQUIDATION_CLUSTER_5PCT",
            "severity": SEVERITY_MAP["PR7"],
            "threshold": f"2+ positions within {t}% of liquidation",
            "observed_value": count,
            "affected_addresses": [s.address for s in affected],
            "affected_coins": list({s.coin for s in affected}),
            "explanation": f"{count} positions (${total:,.0f}) within {t}% of liquidation",
        }
    return None


def rule_pr8_cross_whale_same_direction(
    snapshots: list[WhaleSnapshot], snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    """PR8: 2+ whales holding same coin in same direction."""
    findings = []
    SAME_DIR_THRESHOLD = 1_000_000  # hard minimum for significance
    coin_dir: dict[str, dict[str, list[WhaleSnapshot]]] = {}
    for s in snapshots:
        if s.signed_size == 0:
            continue
        coin = s.coin
        direction = "long" if s.signed_size > 0 else "short"
        if coin not in coin_dir:
            coin_dir[coin] = {"long": [], "short": []}
        coin_dir[coin][direction].append(s)

    for coin, dirs in coin_dir.items():
        for direction, positions in dirs.items():
            if len(positions) >= 2:
                total = sum(abs(p.position_value_usd) for p in positions)
                if total >= SAME_DIR_THRESHOLD:
                    findings.append({
                        "finding_id": _make_finding_id(
                            "PR8", snapshot_id, len(findings),
                        ),
                        "rule_id": "PR8_CROSS_WHALE_SAME_DIRECTION",
                        "severity": SEVERITY_MAP["PR8"],
                        "threshold": "2+ whales same direction on same coin",
                        "observed_value": len(positions),
                        "affected_addresses": [p.address for p in positions],
                        "affected_coins": [coin],
                        "explanation": f"{len(positions)} whales holding {direction.upper()} "
                                       f"{coin} totaling ${total:,.0f}",
                    })
    return findings


def rule_pr9_cross_whale_direction_flip(
    changes: list[dict], snapshot_id: str = "",
) -> list[dict]:
    """PR9: Multiple whales flipping same coin direction in same window."""
    findings = []
    flip_coins: dict[str, list[str]] = {}
    for c in changes:
        ct = c.get("change_type", "")
        if "flip" in ct:
            coin = c.get("coin", "?")
            addr = c.get("address", "")
            if coin not in flip_coins:
                flip_coins[coin] = []
            flip_coins[coin].append(addr)

    for coin, addrs in flip_coins.items():
        if len(addrs) >= 2:
            findings.append({
                "finding_id": _make_finding_id("PR9", snapshot_id, len(findings)),
                "rule_id": "PR9_CROSS_WHALE_DIRECTION_FLIP",
                "severity": SEVERITY_MAP["PR9"],
                "threshold": "2+ whales flipping same coin",
                "observed_value": len(addrs),
                "affected_addresses": addrs,
                "affected_coins": [coin],
                "explanation": f"{len(addrs)} whales flipped direction on {coin}",
            })
    return findings


def rule_pr10_rapid_exposure_expansion(
    current_gross: float, previous_gross: Optional[float],
    snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> Optional[dict]:
    """PR10: Gross exposure expanded > rapid_expansion_pct since previous."""
    t = cfg.rapid_expansion_pct
    if previous_gross is not None and previous_gross > 0:
        pct_change = ((current_gross - previous_gross) / previous_gross) * 100
        if pct_change > t:
            return {
                "finding_id": _make_finding_id("PR10", snapshot_id, 0),
                "rule_id": "PR10_RAPID_EXPOSURE_EXPANSION",
                "severity": SEVERITY_MAP["PR10"],
                "threshold": f"> {t}% expansion",
                "observed_value": round(pct_change, 1),
                "explanation": f"Gross exposure expanded {pct_change:.1f}% since previous snapshot",
            }
    return None


def rule_pr11_data_stale(
    snapshots: list[WhaleSnapshot], reference_time: str,
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    """PR11: Positions with stale data (older than stale_data_hours from reference)."""
    findings = []
    from market_radar.whale_domain.models import _iso_to_ts
    ref_ts = _iso_to_ts(reference_time)
    if ref_ts == 0:
        return findings
    stale_cutoff = ref_ts - (cfg.stale_data_hours * 3600)
    for s in snapshots:
        snap_ts = _iso_to_ts(s.snapshot_time_utc)
        if snap_ts > 0 and snap_ts < stale_cutoff:
            findings.append({
                "finding_id": _make_finding_id("PR11", snapshot_id="", idx=len(findings)),
                "rule_id": "PR11_DATA_STALE",
                "severity": SEVERITY_MAP["PR11"],
                "threshold": f"> {cfg.stale_data_hours}h old",
                "observed_value": round((ref_ts - snap_ts) / 3600, 1),
                "affected_addresses": [s.address],
                "explanation": f"Position at {s.address[:10]} is stale ({(ref_ts - snap_ts) / 3600:.1f}h old)",
            })
    return findings


def rule_pr12_data_incomplete(
    snapshots: list[WhaleSnapshot],
) -> Optional[dict]:
    """PR12: Data quality is incomplete (missing critical fields)."""
    quality = assess_data_quality(snapshots)
    if quality == "incomplete":
        missing_mark = sum(1 for s in snapshots if s.mark_price is None or s.mark_price <= 0)
        missing_liq = sum(1 for s in snapshots if s.liquidation_distance_pct is None)
        return {
            "finding_id": _make_finding_id("PR12", "", 0),
            "rule_id": "PR12_DATA_INCOMPLETE",
            "severity": SEVERITY_MAP["PR12"],
            "threshold": "Missing critical data fields",
            "observed_value": f"mark_missing={missing_mark}, liq_missing={missing_liq}",
            "explanation": f"{missing_mark} positions missing mark price, "
                           f"{missing_liq} missing liquidation price",
        }
    return None


def evaluate_all_rules(
    snapshots: list[WhaleSnapshot],
    changes: Optional[list[dict]] = None,
    previous_gross: Optional[float] = None,
    reference_time: str = "",
    snapshot_id: str = "",
    cfg: PortfolioThresholds = DEFAULT_THRESHOLDS,
) -> list[dict]:
    """Evaluate all 12 portfolio risk rules. Returns list of finding dicts."""
    gross = compute_gross_exposure(snapshots)
    long_exp = compute_long_exposure(snapshots)
    short_exp = compute_short_exposure(snapshots)

    findings: list[dict] = []

    # PR1
    f = rule_pr1_high_gross_exposure(gross, snapshot_id, cfg)
    if f:
        findings.append(f)

    # PR2
    f = rule_pr2_net_direction_concentration(long_exp, short_exp, gross, snapshot_id, cfg)
    if f:
        findings.append(f)

    # PR3
    findings.extend(rule_pr3_single_coin_concentration(snapshots, gross, snapshot_id, cfg))

    # PR4
    findings.extend(rule_pr4_single_address_concentration(snapshots, gross, snapshot_id, cfg))

    # PR5
    wl = compute_weighted_leverage(snapshots)
    f = rule_pr5_high_weighted_leverage(wl, snapshot_id, cfg)
    if f:
        findings.append(f)

    # PR6
    f = rule_pr6_liquidation_cluster_2pct(snapshots, snapshot_id, cfg)
    if f:
        findings.append(f)

    # PR7
    f = rule_pr7_liquidation_cluster_5pct(snapshots, snapshot_id, cfg)
    if f:
        findings.append(f)

    # PR8
    findings.extend(rule_pr8_cross_whale_same_direction(snapshots, snapshot_id, cfg))

    # PR9
    if changes:
        findings.extend(rule_pr9_cross_whale_direction_flip(changes, snapshot_id))

    # PR10
    f = rule_pr10_rapid_exposure_expansion(gross, previous_gross, snapshot_id, cfg)
    if f:
        findings.append(f)

    # PR11
    if reference_time:
        findings.extend(rule_pr11_data_stale(snapshots, reference_time, cfg))

    # PR12
    f = rule_pr12_data_incomplete(snapshots)
    if f:
        findings.append(f)

    return findings
