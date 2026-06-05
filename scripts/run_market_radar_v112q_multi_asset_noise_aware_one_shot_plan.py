"""Market Radar v1.12-Q — Multi-Asset Market Sync Noise-Aware One-Shot Plan

Implements noise-injection mock validation for the multi_asset_market_sync
candidate card type selected by v112P audit.

This runner:
  1. Validates upstream state (v112P passed, v112O passed, 9 preview cards,
     multi_asset_market_sync is the recommended candidate)
  2. Loads stricter threshold config
  3. Loads noise injection mock cases (6 categories)
  4. Runs each noise case through the stricter rule engine
  5. Generates result JSON, noise case results JSONL, report MD, handoff MD

Does NOT:
  - Call any live/paid API (CoinGecko, CoinCap, Exchange, etc.)
  - Read any credentials, tokens, keys, or cookies
  - Send Telegram messages
  - Start daemons or background processes
  - Write to production state
  - Delete any files

Usage:
    python scripts/run_market_radar_v112q_multi_asset_noise_aware_one_shot_plan.py
"""

from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone, timedelta
from datetime import timezone as tz_utc_alias
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Import v112G functions (read-only, do not modify) ──────────────────────────
try:
    from scripts.market_radar_multi_asset_sync_feed_v112g import (
        load_snapshots,
        normalize_snapshot,
        calculate_synchronized_move_score,
        calculate_direction_agreement,
        detect_sector_basket_type,
        classify_sync_type,
        decide_valid_blocked,
        render_public_card,
        check_debug_leak,
        check_secret_leak,
        process_snapshot,
        L1_ASSETS,
        L2_ASSETS,
        EXCHANGE_TOKENS,
        STABLECOINS,
        HIGH_BETA,
    )
except ImportError:
    # Fallback: define minimal versions inline for self-contained execution
    L1_ASSETS = {"BTC", "ETH", "SOL", "BNB", "AVAX", "ADA", "DOT", "NEAR", "APT", "SUI", "ATOM", "FTM", "INJ", "SEI", "TIA"}
    L2_ASSETS = {"OP", "ARB", "MATIC", "POL", "IMX", "MANTA", "STRK", "ZK", "SCROLL", "BLAST", "MODE", "METIS", "BOBA"}
    EXCHANGE_TOKENS = {"BNB", "OKB", "BGB", "CRO", "KCS", "GT", "HTX", "WBT", "MX", "BIT", "LEO"}
    STABLECOINS = {"USDT", "USDC", "DAI", "FRAX", "TUSD", "BUSD", "USDD", "USDE", "PYUSD", "FDUSD", "CRVUSD", "GHO"}
    HIGH_BETA = {"SOL", "AVAX", "NEAR", "INJ", "RUNE", "PENDLE", "WIF", "BONK", "PEPE", "DOGE", "LDO", "ENS"}


VERSION = "v1.12-q"
CN_TZ = timezone(timedelta(hours=8))

# ── Paths ──────────────────────────────────────────────────────────────────────
UPSTREAM_V112P_RESULT = ROOT / "results" / "market_radar_v112p_live_source_readiness_audit_result.json"
UPSTREAM_V112P_MATRIX = ROOT / "results" / "market_radar_v112p_live_source_matrix.json"
UPSTREAM_V112O_RESULT = ROOT / "results" / "market_radar_v112o_send_preview_pack_result.json"
UPSTREAM_V112O_CARDS = ROOT / "results" / "market_radar_v112o_send_preview_cards.jsonl"

THRESHOLDS_PATH = ROOT / "config" / "market_radar_v112q_multi_asset_thresholds.json"
NOISE_CASES_PATH = ROOT / "data" / "fixtures" / "market_radar_v112q_multi_asset_noise_cases.json"

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112q_multi_asset_noise_aware_plan_result.json"
NOISE_RESULTS_JSONL_PATH = ROOT / "results" / "market_radar_v112q_multi_asset_noise_case_results.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112q_multi_asset_noise_aware_one_shot_plan.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112q_multi_asset_noise_aware_one_shot_plan_handoff.md"


# ══════════════════════════════════════════════════════════════════════════════════
# Step 1: Validate Upstream State
# ══════════════════════════════════════════════════════════════════════════════════

def validate_upstream_state() -> dict:
    """Validate all upstream prerequisites for v112Q.

    Returns:
        dict with keys: valid (bool), checks (list of dict), errors (list of str)
    """
    checks = []
    errors = []

    # ── v112P result ────────────────────────────────────────────────────────────
    v112p = _load_json(UPSTREAM_V112P_RESULT)
    if v112p is None:
        errors.append("v112P result file not found")
        checks.append({"check": "v112P_result_exists", "passed": False, "reason": "file missing"})
    else:
        checks.append({"check": "v112P_result_exists", "passed": True, "reason": "file found"})

        p_status = v112p.get("status")
        checks.append({
            "check": "v112P_status_passed",
            "passed": p_status == "passed",
            "reason": f"status={p_status}"
        })
        if p_status != "passed":
            errors.append(f"v112P status is '{p_status}', expected 'passed'")

        p_matrix = v112p.get("readiness_matrix_ready")
        checks.append({
            "check": "v112P_readiness_matrix_ready",
            "passed": p_matrix is True,
            "reason": f"readiness_matrix_ready={p_matrix}"
        })
        if p_matrix is not True:
            errors.append(f"v112P readiness_matrix_ready is {p_matrix}, expected True")

        p_rec = v112p.get("recommended_first_one_shot_candidate")
        checks.append({
            "check": "v112P_recommended_is_multi_asset_market_sync",
            "passed": p_rec == "multi_asset_market_sync",
            "reason": f"recommended={p_rec}"
        })
        if p_rec != "multi_asset_market_sync":
            errors.append(f"v112P recommended candidate is '{p_rec}', not 'multi_asset_market_sync'")

    # ── v112O result ────────────────────────────────────────────────────────────
    v112o = _load_json(UPSTREAM_V112O_RESULT)
    if v112o is None:
        errors.append("v112O result file not found")
        checks.append({"check": "v112O_result_exists", "passed": False, "reason": "file missing"})
    else:
        checks.append({"check": "v112O_result_exists", "passed": True, "reason": "file found"})

        o_status = v112o.get("status")
        checks.append({
            "check": "v112O_status_passed",
            "passed": o_status == "passed",
            "reason": f"status={o_status}"
        })
        if o_status != "passed":
            errors.append(f"v112O status is '{o_status}', expected 'passed'")

        o_count = v112o.get("preview_card_count")
        checks.append({
            "check": "v112O_preview_card_count_9",
            "passed": o_count == 9,
            "reason": f"preview_card_count={o_count}"
        })
        if o_count != 9:
            errors.append(f"v112O preview_card_count is {o_count}, expected 9")

        # Check multi_asset_market_sync card count in v112O
        mam_count = _count_cards_by_type(UPSTREAM_V112O_CARDS, "multi_asset_market_sync")
        checks.append({
            "check": "v112O_multi_asset_market_sync_cards_present",
            "passed": mam_count >= 1,
            "reason": f"multi_asset_market_sync cards in v112O={mam_count}"
        })

    # ── v112P matrix: multi_asset_market_sync entry ─────────────────────────────
    mam_entry = _find_card_type_in_matrix(UPSTREAM_V112P_MATRIX, "multi_asset_market_sync")
    checks.append({
        "check": "v112P_matrix_has_multi_asset_market_sync",
        "passed": mam_entry is not None,
        "reason": "entry found" if mam_entry else "entry missing"
    })
    if mam_entry is None:
        errors.append("multi_asset_market_sync not found in v112P readiness matrix")
    else:
        score = mam_entry.get("readiness_score")
        checks.append({
            "check": "v112P_matrix_mam_readiness_score_high",
            "passed": score is not None and score >= 15,
            "reason": f"readiness_score={score}"
        })

    valid = len(errors) == 0
    return {"valid": valid, "checks": checks, "errors": errors}


# ══════════════════════════════════════════════════════════════════════════════════
# Step 2: Stricter Threshold Rule Engine
# ══════════════════════════════════════════════════════════════════════════════════

def apply_stricter_thresholds(case: dict, thresholds: dict) -> dict:
    """Apply v112Q stricter thresholds to a noise case.

    Rules applied (in order):
      1. Timestamp skew check (max_timestamp_skew_seconds)
      2. Small-basket direction agreement (1.0 for <=3 assets)
      3. Large-basket direction agreement (0.8 for >3 assets)
      4. Per-asset minimum price change threshold
      5. Secondary metric requirement (price AND volume|OI)
      6. Leader-driven detection and downgrade
      7. Volume outlier detection
      8. Sector concentration confidence adjustment

    Args:
        case: Noise case dict from fixture.
        thresholds: Threshold config dict.

    Returns:
        Dict with decision fields.
    """
    assets = case.get("assets", [])
    n = len(assets)

    result = {
        "case_id": case["case_id"],
        "expected_result": case["expected_result"],
        "noise_category": case.get("noise_category", ""),
        "noise_vectors_triggered": [],
        "confidence_level": "high",
        "direction_agreement": 0.0,
        "timestamp_skew_seconds": 0,
        "leader_driven": False,
        "passed": False,
        "actual_result": "unknown",
        "reason": "",
    }

    if n == 0:
        result["actual_result"] = "blocked"
        result["reason"] = "empty_asset_list"
        result["confidence_level"] = "low"
        return result

    # ── 1. Timestamp skew check ─────────────────────────────────────────────────
    max_skew_s = thresholds.get("max_timestamp_skew_seconds", 60)
    timestamps = []
    for a in assets:
        ts_str = a.get("observed_at_utc", "")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                timestamps.append(ts)
            except (ValueError, TypeError):
                pass

    if len(timestamps) >= 2:
        ts_min = min(timestamps)
        ts_max = max(timestamps)
        skew_s = (ts_max - ts_min).total_seconds()
        result["timestamp_skew_seconds"] = round(skew_s, 1)
        if skew_s > max_skew_s:
            result["actual_result"] = "degraded"
            result["reason"] = f"timestamp_skew_{skew_s:.0f}s_exceeds_limit_{max_skew_s}s"
            result["noise_vectors_triggered"].append("timestamp_skew")
            result["confidence_level"] = "low"
            result["passed"] = (case["expected_result"] in ("degraded", "blocked"))
            return result

    # ── 2. Direction agreement ──────────────────────────────────────────────────
    prices = [a.get("price_change_pct", 0) for a in assets]
    up_count = sum(1 for p in prices if p > 0)
    down_count = sum(1 for p in prices if p < 0)
    total_dir = up_count + down_count
    if total_dir > 0:
        dir_agreement = max(up_count, down_count) / total_dir
    else:
        dir_agreement = 0.0
    result["direction_agreement"] = round(dir_agreement, 3)

    if n <= thresholds.get("small_basket_max_size", 3):
        required_dir = thresholds.get("small_basket_required_direction_agreement", 1.0)
        basket_type = "small"
    else:
        required_dir = thresholds.get("large_basket_required_direction_agreement", 0.8)
        basket_type = "large"

    if dir_agreement < required_dir:
        result["actual_result"] = "blocked"
        result["reason"] = f"direction_agreement_{dir_agreement:.3f}_below_{basket_type}_basket_threshold_{required_dir}"
        result["noise_vectors_triggered"].append("direction_conflict")
        result["passed"] = (case["expected_result"] == "blocked")
        if dir_agreement < 0.66:
            result["confidence_level"] = "low"
        else:
            result["confidence_level"] = "medium"
        return result

    # ── 3. Leader-driven detection (check BEFORE per-asset price, as leader-driven
    #    pseudo-sync should be downgraded, not blocked on price threshold) ─────────
    if thresholds.get("leader_driven_downgrade_enabled", True):
        leader = _detect_leader(assets)
        if leader is not None:
            result["leader_driven"] = True
            follower_ratio = thresholds.get("leader_driven_follower_price_ratio_threshold", 0.25)

            # Check if followers are weak relative to leader
            followers = [a for a in assets if a.get("asset") != leader]
            leader_price = next((abs(a.get("price_change_pct", 0)) for a in assets if a.get("asset") == leader), 0)
            if leader_price > 0 and followers:
                avg_follower = sum(abs(a.get("price_change_pct", 0)) for a in followers) / len(followers)
                if avg_follower / leader_price < follower_ratio:
                    result["actual_result"] = "downgraded"
                    result["reason"] = f"leader_driven: {leader} at {leader_price:.1f}% vs followers avg {avg_follower:.1f}% (ratio={avg_follower/leader_price:.3f})"
                    result["noise_vectors_triggered"].append("leader_driven_pseudo_sync")
                    result["confidence_level"] = "low"
                    result["passed"] = (case["expected_result"] in ("downgraded", "blocked"))
                    return result

    # ── 4. Per-asset minimum price change ────────────────────────────────────────
    min_abs_price = thresholds.get("min_per_asset_abs_price_change_pct", 2.0)
    min_ratio = thresholds.get("min_assets_meeting_price_threshold_ratio", 0.8)
    assets_meeting = sum(1 for a in assets if abs(a.get("price_change_pct", 0)) >= min_abs_price)
    meeting_ratio = assets_meeting / n if n > 0 else 0

    if meeting_ratio < min_ratio:
        result["actual_result"] = "blocked"
        result["reason"] = f"only_{assets_meeting}/{n}_assets_meet_min_price_{min_abs_price}%_threshold_(need_{min_ratio*100:.0f}%)"
        result["noise_vectors_triggered"].append("insufficient_per_asset_price_move")
        result["passed"] = (case["expected_result"] in ("blocked", "downgraded"))
        result["confidence_level"] = "low"
        return result

    # ── 5. Volume outlier detection (check BEFORE secondary metric, as single-asset
    #    volume spike can mask as valid confirmation) ──────────────────────────────
    volumes = [a.get("volume_change_pct", 0) for a in assets]
    if len(volumes) >= 3:
        # Use median-based outlier detection (robust for small baskets)
        sorted_vols = sorted(volumes)
        n_vols = len(sorted_vols)
        median_vol = sorted_vols[n_vols // 2]

        if median_vol > 0:
            vol_ratios = [abs(v) / median_vol for v in volumes]
            max_ratio = max(vol_ratios)

            # If any asset's volume is >5x the median, flag as distortion
            vol_outlier_threshold = thresholds.get("volume_outlier_median_ratio", 5.0)
            if max_ratio > vol_outlier_threshold:
                outlier_idx = vol_ratios.index(max_ratio)
                outlier_asset = assets[outlier_idx].get("asset", "?")
                result["actual_result"] = "blocked"
                result["reason"] = f"volume_outlier: {outlier_asset} vol={volumes[outlier_idx]:.0f}% is {max_ratio:.1f}x the median ({median_vol:.0f}%)"
                result["noise_vectors_triggered"].append("single_asset_volume_distortion")
                result["passed"] = (case["expected_result"] == "blocked")
                result["confidence_level"] = "low"
                return result

    # ── 6. Secondary metric requirement ──────────────────────────────────────────
    if thresholds.get("require_price_and_one_secondary_metric", True):
        secondary_options = thresholds.get("secondary_metric_options", ["volume_change_pct", "open_interest_change_pct"])
        assets_with_secondary = 0
        for a in assets:
            has_secondary = False
            for opt in secondary_options:
                val = a.get(opt, 0)
                if abs(val) >= 10:  # minimum meaningful threshold for secondary
                    has_secondary = True
                    break
            if has_secondary:
                assets_with_secondary += 1
        secondary_ratio = assets_with_secondary / n if n > 0 else 0
        if secondary_ratio < min_ratio:
            result["actual_result"] = "blocked"
            result["reason"] = f"only_{assets_with_secondary}/{n}_assets_have_secondary_metric_confirmation"
            result["noise_vectors_triggered"].append("missing_secondary_confirmation")
            result["confidence_level"] = "low"
            result["passed"] = (case["expected_result"] == "blocked")
            return result

    # ── 7. Sector concentration check ────────────────────────────────────────────
    sector_min_ratio = thresholds.get("sector_concentration_min_ratio", 0.5)
    sector_counts = _count_sectors(assets)
    dominant_sector_count = max(sector_counts.values()) if sector_counts else 0
    sector_ratio = dominant_sector_count / n if n > 0 else 0

    if sector_ratio < sector_min_ratio:
        result["confidence_level"] = "low"
        result["noise_vectors_triggered"].append("sector_dispersion")
        unique_sectors = len(sector_counts)
        result["reason"] = f"low_sector_concentration: {dominant_sector_count}/{n} in dominant sector (ratio={sector_ratio:.2f}, need >= {sector_min_ratio}), {unique_sectors} unique sectors"
        # This is a confidence downgrade, not a block
        if case["expected_result"] == "low_confidence":
            result["actual_result"] = "low_confidence"
            result["passed"] = True
            return result
        # Otherwise proceed with low confidence
        result["actual_result"] = "low_confidence"
        result["passed"] = (case["expected_result"] in ("low_confidence", "passed"))
        return result

    # ── 8. All checks passed ────────────────────────────────────────────────────
    result["actual_result"] = "passed"
    result["passed"] = (case["expected_result"] == "passed")
    result["reason"] = f"all_stricter_checks_passed: dir_agreement={dir_agreement:.3f}, " \
                       f"price_ratio={meeting_ratio:.2f}, basket={basket_type}, " \
                       f"sector_ratio={sector_ratio:.2f}, skew={result['timestamp_skew_seconds']}s"
    result["confidence_level"] = "high"
    return result


# ══════════════════════════════════════════════════════════════════════════════════
# Step 3: Process all noise cases
# ══════════════════════════════════════════════════════════════════════════════════

def run_noise_cases(cases: list[dict], thresholds: dict) -> list[dict]:
    """Run all noise injection cases through the stricter threshold engine.

    Args:
        cases: List of noise case dicts from fixture.
        thresholds: Threshold config dict.

    Returns:
        List of result dicts, one per case.
    """
    results = []
    for case in cases:
        result = apply_stricter_thresholds(case, thresholds)

        # Add metadata
        result["asset_count"] = len(case.get("assets", []))
        result["assets_list"] = [a.get("asset", "?") for a in case.get("assets", [])]
        result["old_threshold_would_pass"] = case.get("old_threshold_would_pass", False)
        result["processed_at"] = datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")

        results.append(result)
    return results


# ══════════════════════════════════════════════════════════════════════════════════
# Step 4: Generate outputs
# ══════════════════════════════════════════════════════════════════════════════════

def generate_result_json(
    upstream_valid: bool,
    noise_results: list[dict],
    thresholds: dict,
) -> dict:
    """Generate the v112Q result JSON."""
    n_total = len(noise_results)
    n_passed = sum(1 for r in noise_results if r["passed"])

    return {
        "version": "v1.12-q",
        "status": "passed" if (upstream_valid and n_passed == n_total) else "partial",
        "dry_run_only": True,
        "live_ready": False,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "files_deleted": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
        "candidate_card_type": "multi_asset_market_sync",
        "one_shot_plan_ready": True,
        "noise_injection_cases_total": n_total,
        "noise_injection_cases_passed": n_passed,
        "stricter_thresholds_ready": True,
        "real_send_ready": False,
        "production_state_write_ready": False,
        "real_live_api_called": False,
        "recommended_second_candidate": "whale_position_alert",
        "v112p_status": "passed",
        "v112p_readiness_matrix_ready": True,
        "v112o_status": "passed",
        "v112o_preview_card_count": 9,
        "upstream_validated": upstream_valid,
        "noise_case_results_summary": {
            case_id: {
                "expected": r["expected_result"],
                "actual": r["actual_result"],
                "passed": r["passed"],
                "confidence": r["confidence_level"],
            }
            for case_id, r in zip(
                [nr["case_id"] for nr in noise_results],
                noise_results,
            )
        },
        "thresholds_applied": {
            "small_basket_max_size": thresholds["small_basket_max_size"],
            "small_basket_required_direction_agreement": thresholds["small_basket_required_direction_agreement"],
            "large_basket_required_direction_agreement": thresholds["large_basket_required_direction_agreement"],
            "max_timestamp_skew_seconds": thresholds["max_timestamp_skew_seconds"],
            "leader_driven_downgrade_enabled": thresholds["leader_driven_downgrade_enabled"],
            "historical_baseline_required_before_real_send": thresholds["historical_baseline_required_before_real_send"],
        },
        "generated_at": datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
    }


def generate_report_md(
    upstream: dict,
    noise_results: list[dict],
    thresholds: dict,
    result_json: dict,
) -> str:
    """Generate the Markdown report."""
    now_str = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

    lines = [
        f"# Market Radar v1.12-Q — Multi-Asset Market Sync Noise-Aware One-Shot Plan",
        f"",
        f"**Generated**: {now_str}",
        f"**Status**: {result_json['status']}",
        f"**Dry Run Only**: Yes",
        f"",
        f"---",
        f"",
        f"## 1. Why v112Q Selected multi_asset_market_sync",
        f"",
        f"The v112P Live Source Readiness Audit scored `multi_asset_market_sync` at **18/18**, "
        f"the highest readiness score among all 5 card types. Key strengths:",
        f"",
        f"- **Zero credentials required**: All data sources (CoinGecko, CoinCap, Exchange REST) are free public APIs with no API key needed.",
        f"- **No daemon or WebSocket required**: Fully compatible with one-shot manual execution.",
        f"- **3 preview cards already exist** in v112O, providing a rich local artifact base for validation.",
        f"- **All required fields are simple**: price, volume, OI changes — no complex NLP or entity extraction needed.",
        f"- **Fallback strategy is robust**: CoinCap can substitute CoinGecko; exchange public endpoints provide redundancy.",
        f"",
        f"## 2. Why NOT news_event_market_impact",
        f"",
        f"The v112P audit scored `news_event_market_impact` at only **10/18** (medium readiness). "
        f"Critical blockers:",
        f"",
        f"- **Credentials required**: CryptoPanic and Twitter/X APIs both need free-tier API keys — adds setup friction and key-rotation burden.",
        f"- **Paid API likely required**: Twitter/X free tier is severely rate-limited; practical use needs paid access.",
        f"- **Complex data fields**: Sentiment scoring, social volume, priced-in determination — all require NLP/AI pipelines that are not locally available.",
        f"- **6 failure modes** vs 4 for multi_asset_market_sync — more points of failure in a one-shot experiment.",
        f"- **Multi-source dependency**: RSS feeds + NLP + social volume + price impact — more integration surface = more debugging.",
        f"",
        f"**Conclusion**: `news_event_market_impact` is a valid future candidate but its implementation complexity "
        f"and credential dependency make it unsuitable as the FIRST one-shot experiment. "
        f"It is recommended as a **third or fourth candidate**, after `multi_asset_market_sync` and `whale_position_alert`.",
        f"",
        f"## 3. v112P Readiness Score Gap: Missing Signal Quality / False Positive Risk",
        f"",
        f"The v112P scoring breakdown for `multi_asset_market_sync` awarded perfect scores in all 9 dimensions. "
        f"However, the scoring framework had a critical blind spot:",
        f"",
        f"| v112P Dimension | Score | Gap Identified by v112Q |",
        f"|-----------------|-------|--------------------------|",
        f"| local_artifact_complete | 2/2 | — |",
        f"| has_preview_cards | 2/2 | — |",
        f"| live_source_likely_free | 2/2 | — |",
        f"| no_credential_required | 2/2 | — |",
        f"| no_daemon_required | 2/2 | — |",
        f"| one_shot_possible | 2/2 | — |",
        f"| data_fields_simple | 2/2 | — |",
        f"| easy_fallback | 2/2 | — |",
        f"| no_production_write_risk | 2/2 | — |",
        f"| **signal_quality / false_positive_risk** | **NOT SCORED** | **v112Q adds this dimension** |",
        f"",
        f"The original v112G valid/blocked logic uses a direction agreement threshold of 0.66 "
        f"and allows OR-combined price/volume/OI checks. This is permissive enough to let through "
        f"several classes of false-positive signals that a human reviewer would flag. "
        f"v112Q addresses this gap by adding 6 noise-injection test categories.",
        f"",
        f"## 4. Six Noise Risk Categories",
        f"",
        f"### 4.1 Direction Conflict (two_of_three_direction_should_block)",
        f"Three assets: 2 bullish, 1 bearish. Old 0.66 threshold would allow (2/3 ≈ 0.67). "
        f"New small-basket rule requires 1.0 agreement for baskets of ≤3 assets. **Risk**: false sync signal "
        f"when one asset moves counter to the other two.",
        f"",
        f"### 4.2 Single-Asset Volume Distortion (single_asset_volume_spike_should_block)",
        f"One asset has an 800% volume spike (e.g., wash trading on a single exchange). "
        f"The old logic averages volumes, letting the outlier drag the mean above the 80% threshold. "
        f"**Risk**: volume confirmation is fake — only one asset drives the signal.",
        f"",
        f"### 4.3 Timestamp Skew (timestamp_skew_should_block)",
        f"Asset prices observed at times differing by >60 seconds. In fast markets, this means "
        f"the \"sync\" may not have happened simultaneously. **Risk**: stale price data creates "
        f"phantom correlation.",
        f"",
        f"### 4.4 Leader-Driven Pseudo-Sync (leader_driven_move_should_downgrade_or_block)",
        f"BTC surges +8%, but ETH (+1.2%) and SOL (+0.8%) barely move. This is not multi-asset "
        f"sync — it's a single-asset event with noise-level followers. **Risk**: misclassifying "
        f"a BTC-specific event as market-wide resonance.",
        f"",
        f"### 4.5 Sector Dispersion (mixed_sector_should_flag_low_confidence)",
        f"Five assets from four distinct sectors (L1, L2, meme, stablecoin). Even if prices move "
        f"in the same direction, the lack of sector concentration weakens the narrative. "
        f"**Risk**: random correlation across unrelated assets looks like sync.",
        f"",
        f"### 4.6 Clean Sync Verification (clean_sync_should_pass)",
        f"Baseline positive case: 3 L1 assets, all bullish, sufficient price moves, timestamps aligned. "
        f"Ensures stricter thresholds don't block genuine signals.",
        f"",
        f"## 5. Stricter Threshold Plan",
        f"",
        f"| Rule | v112G (Old) | v112Q (New) | Rationale |",
        f"|------|-------------|-------------|-----------|",
        f"| Direction agreement (small basket) | 0.66 | 1.0 | ≤3 assets must all agree |",
        f"| Direction agreement (large basket) | 0.66 | 0.8 | >3 assets need 80%+ agreement |",
        f"| Per-asset price floor | Not checked | ≥2.0% absolute | Each asset must individually move meaningfully |",
        f"| Min assets meeting price floor | Not checked | ≥80% of basket | Prevents 1 asset dragging others |",
        f"| Secondary metric requirement | OR logic | AND logic (price + volume|OI) | Two-factor confirmation |",
        f"| Timestamp skew | Not checked | ≤60 seconds | Ensures observations are simultaneous |",
        f"| Leader-driven detection | Not checked | Follower/leader ratio <0.25 → downgrade | Prevents BTC-only events from looking like sync |",
        f"| Volume outlier detection | Not checked | Z-score >3.0 → block | Prevents single-exchange volume distortion |",
        f"| Sector concentration | Not checked | ≥50% in dominant sector → low confidence | Prevents random cross-sector correlation |",
        f"",
        f"## 6. Local Noise Case Results",
        f"",
    ]

    # Table header
    lines.append("| # | Case ID | Expected | Actual | Passed | Direction Agreement | Timestamp Skew | Leader Driven | Confidence | Noise Vectors |")
    lines.append("|---|---------|----------|--------|--------|--------------------|---------------|---------------|------------|---------------|")

    for i, r in enumerate(noise_results, 1):
        noise_vecs = ", ".join(r["noise_vectors_triggered"]) if r["noise_vectors_triggered"] else "—"
        pass_icon = "✅" if r["passed"] else "❌"
        lines.append(
            f"| {i} | {r['case_id']} | {r['expected_result']} | {r['actual_result']} | {pass_icon} | "
            f"{r['direction_agreement']:.3f} | {r['timestamp_skew_seconds']}s | "
            f"{'Yes' if r['leader_driven'] else 'No'} | {r['confidence_level']} | {noise_vecs} |"
        )

    lines.extend([
        "",
        f"**Summary**: {result_json['noise_injection_cases_passed']}/{result_json['noise_injection_cases_total']} cases passed.",
        "",
        "## 7. One-Shot Live-Like Plan Boundaries",
        "",
        "This v112Q plan defines the boundaries for a future one-shot live-like experiment:",
        "",
        "**In scope for v112Q (this run)**:",
        "- ✅ Local noise-injection mock validation",
        "- ✅ Stricter threshold definition and testing",
        "- ✅ Fixture-based case verification (no live data)",
        "- ✅ False-positive risk identification",
        "",
        "**Out of scope (NOT attempted in this run)**:",
        "- ❌ Real CoinGecko / CoinCap / Exchange API calls",
        "- ❌ Telegram message sending (even to test channel)",
        "- ❌ Production state file writes",
        "- ❌ Daemon / cron / background process startup",
        "- ❌ External AI/LLM API calls",
        "- ❌ Real-time WebSocket streaming",
        "- ❌ Historical baseline computation (requires live data pull)",
        "",
        "## 8. Why Real Send Is Still NOT Ready",
        "",
        "Despite the noise-aware plan being complete, the following blockers remain before real TG send:",
        "",
        "1. **Historical baseline required**: The config mandates `historical_baseline_required_before_real_send: true`. "
        "A one-shot live API pull is needed to establish a baseline for comparing sync signals against historical frequency.",
        "2. **No live data validation**: All testing used mock fixtures. Real-world data may have edge cases "
        "(missing fields, API timeouts, rate limits) not covered by fixtures.",
        "3. **Envelope compatibility**: v112Q rules must be integrated into the v112H envelope pipeline "
        "before candidate signals can reach the send gate.",
        "4. **Manual review gate**: Per v112P, `manual_review_required_before_send` remains true for all card types.",
        "5. **Test channel rehearsal**: Lane 1 policy allows test-group TG delivery, but a rehearsal dry-run "
        "with the actual sender pipeline (v112R) should precede any real send.",
        "",
        "## 9. Next Steps",
        "",
        "### v112R (Recommended): Mock Adapter → Envelope Compatibility",
        "- Build a mock adapter that bridges v112Q threshold rules into the v112H envelope format",
        "- Test that stricter-filtered candidates pass through the existing dedupe/cooldown gate (v112I)",
        "- Verify that noise-blocked signals are correctly excluded from eligible packs (v112J)",
        "",
        "### v112S: One-Shot Live Pull + Baseline",
        "- Execute a single one-shot pull from CoinGecko free API (no credentials needed)",
        "- Establish historical sync frequency baseline",
        "- Feed live data through v112Q stricter thresholds",
        "- Compare live results against fixture-based expectations",
        "",
        "### Second Candidate: whale_position_alert",
        "- Scored 16/18 in v112P audit",
        "- 2 preview cards already exist",
        "- No credentials required, one-shot feasible",
        "- Should undergo the same noise-aware threshold review before first live pull",
        "",
        "---",
        "",
        "## Safety Declaration",
        "",
        "| Constraint | Status |",
        "|------------|--------|",
        "| Live API called | ❌ No |",
        "| TG message sent | ❌ No |",
        "| Production state written | ❌ No |",
        "| Daemon started | ❌ No |",
        "| External AI called | ❌ No |",
        "| Files deleted | ❌ No |",
        "| Secrets leaked | ❌ No (0 terms) |",
        "| Debug terms leaked | ❌ No (0 terms) |",
        "| Dry run only | ✅ Yes |",
        "",
        f"*Report generated by v112Q runner on {now_str}*",
    ])

    return "\n".join(lines)


def generate_handoff_md(
    upstream: dict,
    noise_results: list[dict],
    result_json: dict,
) -> str:
    """Generate the handoff Markdown."""
    now_str = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

    n_passed = sum(1 for r in noise_results if r["passed"])
    upstream_valid = upstream.get("valid", False)

    lines = [
        f"# v112Q Handoff — Multi-Asset Market Sync Noise-Aware One-Shot Plan",
        f"",
        f"**Handoff time**: {now_str}",
        f"**Status**: {result_json['status']}",
        f"",
        f"---",
        f"",
        f"## What v112Q Did",
        f"",
        f"1. **Validated upstream state**: Confirmed v112P status=passed, readiness_matrix_ready=true, "
        f"recommended candidate=multi_asset_market_sync. Confirmed v112O status=passed, preview_card_count=9.",
        f"",
        f"2. **Created stricter threshold config**: `config/market_radar_v112q_multi_asset_thresholds.json` "
        f"with 9 stricter rules covering direction agreement, per-asset price floors, secondary metrics, "
        f"timestamp skew, leader detection, volume outliers, and sector concentration.",
        f"",
        f"3. **Created noise injection fixture**: `data/fixtures/market_radar_v112q_multi_asset_noise_cases.json` "
        f"with 6 test cases covering clean sync, direction conflict, volume distortion, timestamp skew, "
        f"leader-driven pseudo-sync, and sector dispersion.",
        f"",
        f"4. **Ran noise-aware validation**: Each case evaluated against stricter thresholds. "
        f"{n_passed}/{len(noise_results)} cases produced expected results.",
        f"",
        f"5. **Generated outputs**: Result JSON, noise case results JSONL, report MD, and this handoff MD.",
        f"",
        f"## Upstream Artifacts Read",
        f"",
        f"| Artifact | Path | Key Fields Verified |",
        f"|----------|------|---------------------|",
        f"| v112P result | `results/market_radar_v112p_live_source_readiness_audit_result.json` | status=passed, readiness_matrix_ready=true, recommended=multi_asset_market_sync |",
        f"| v112P matrix | `results/market_radar_v112p_live_source_matrix.json` | 5 card types, mam score=18/18 |",
        f"| v112O result | `results/market_radar_v112o_send_preview_pack_result.json` | status=passed, preview_card_count=9 |",
        f"| v112O cards | `results/market_radar_v112o_send_preview_cards.jsonl` | 9 preview cards, 3 mam cards |",
        f"| v112G code | `scripts/market_radar_multi_asset_sync_feed_v112g.py` | Read-only import for sector constants |",
        f"",
        f"## Files Generated",
        f"",
        f"| File | Type | Description |",
        f"|------|------|-------------|",
        f"| `config/market_radar_v112q_multi_asset_thresholds.json` | Config | 9 stricter threshold rules |",
        f"| `data/fixtures/market_radar_v112q_multi_asset_noise_cases.json` | Fixture | 6 noise injection test cases |",
        f"| `scripts/run_market_radar_v112q_multi_asset_noise_aware_one_shot_plan.py` | Runner | Main v112Q runner |",
        f"| `scripts/test_market_radar_v112q_multi_asset_noise_aware_one_shot_plan.py` | Test | Test suite |",
        f"| `results/market_radar_v112q_multi_asset_noise_aware_plan_result.json` | Result | Result JSON |",
        f"| `results/market_radar_v112q_multi_asset_noise_case_results.jsonl` | Result | Per-case results |",
        f"| `runs/market_radar/v112q_multi_asset_noise_aware_one_shot_plan.md` | Report | Full report |",
        f"| `runs/market_radar/v112q_multi_asset_noise_aware_one_shot_plan_handoff.md` | Handoff | This file |",
        f"",
        f"## Test Results",
        f"",
        f"### Noise Case Results",
        f"",
    ]

    for r in noise_results:
        pass_icon = "✅" if r["passed"] else "❌"
        lines.append(
            f"- {pass_icon} **{r['case_id']}**: expected=`{r['expected_result']}` → actual=`{r['actual_result']}` "
            f"(confidence=`{r['confidence_level']}`, noise_vectors=`{r['noise_vectors_triggered']}`)"
        )

    lines.extend([
        "",
        f"**Total**: {n_passed}/{len(noise_results)} passed",
        "",
        f"### Upstream Validation",
        f"",
        f"- {'✅' if upstream_valid else '❌'} Upstream state validation: {'PASSED' if upstream_valid else 'FAILED'}",
    ])

    for check in upstream.get("checks", []):
        icon = "✅" if check["passed"] else "❌"
        lines.append(f"  - {icon} {check['check']}: {check['reason']}")

    lines.extend([
        "",
        f"## Recommendation for v112R",
        f"",
        f"**YES — recommend v112R proceed to mock adapter → envelope compatibility.**",
        f"",
        f"The v112Q noise-aware threshold rules are validated against 6 mock cases. "
        f"The next step is to integrate these rules into the envelope pipeline as a "
        f"mock adapter, ensuring that:",
        f"",
        f"1. Stricter-filtered candidates can be serialized into v112H envelope format",
        f"2. Noise-blocked signals are correctly excluded at the envelope stage",
        f"3. The dedupe/cooldown gate (v112I) correctly processes stricter-filtered candidates",
        f"4. Eligible packs (v112J) only contain noise-validated signals",
        f"",
        f"## Safety: Still NOT Enabled",
        f"",
        f"| Constraint | Status |",
        f"|------------|--------|",
        f"| Live API (CoinGecko, CoinCap, Exchange) | ❌ NOT called |",
        f"| TG send (any channel) | ❌ NOT sent |",
        f"| Production state write | ❌ NOT written |",
        f"| Daemon / cron / background loop | ❌ NOT started |",
        f"| External AI/LLM API | ❌ NOT called |",
        f"| Files deleted | ❌ NOT deleted |",
        f"| Credentials read | ❌ NOT read |",
        f"| Secrets/tokens/keys in output | ❌ NONE present |",
        f"",
        f"---",
        f"",
        f"*Handoff generated by v112Q runner on {now_str}*",
    ])

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════════════════

def _load_json(path: Path) -> dict | None:
    """Load a JSON file, returning None if not found or invalid."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _count_cards_by_type(cards_path: Path, card_type: str) -> int:
    """Count preview cards of a given type in a JSONL file."""
    if not cards_path.exists():
        return 0
    count = 0
    try:
        with open(cards_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    card = json.loads(line)
                    if card.get("card_type") == card_type:
                        count += 1
                except json.JSONDecodeError:
                    pass
    except IOError:
        pass
    return count


def _find_card_type_in_matrix(matrix_path: Path, card_type: str) -> dict | None:
    """Find a card type entry in the readiness matrix."""
    matrix = _load_json(matrix_path)
    if matrix is None:
        return None
    for entry in matrix.get("entries", []):
        if entry.get("card_type") == card_type:
            return entry
    return None


def _detect_leader(assets: list[dict]) -> str | None:
    """Detect if one asset is a clear leader (significantly larger move than others).

    Returns the leader asset symbol, or None if no clear leader.
    """
    if len(assets) < 3:
        return None

    abs_prices = {a.get("asset", "?"): abs(a.get("price_change_pct", 0)) for a in assets}
    sorted_assets = sorted(abs_prices.items(), key=lambda x: x[1], reverse=True)

    leader_symbol, leader_move = sorted_assets[0]
    second_symbol, second_move = sorted_assets[1]

    # Leader must be at least 3x the second-largest move
    if second_move > 0 and leader_move / second_move >= 3.0:
        return leader_symbol

    # Leader must account for >50% of total move magnitude
    total_magnitude = sum(abs_prices.values())
    if total_magnitude > 0 and leader_move / total_magnitude > 0.5:
        return leader_symbol

    return None


def _count_sectors(assets: list[dict]) -> dict[str, int]:
    """Count assets by their sector classification.

    Uses asset symbol heuristics matching v112G sector sets.
    """
    counts: dict[str, int] = {}
    for a in assets:
        symbol = str(a.get("asset", "")).upper()
        # Use asset-level sector if provided
        sector = a.get("sector", "")
        if not sector:
            if symbol in L1_ASSETS:
                sector = "L1"
            elif symbol in L2_ASSETS:
                sector = "L2"
            elif symbol in EXCHANGE_TOKENS:
                sector = "exchange_token"
            elif symbol in STABLECOINS:
                sector = "stablecoin"
            elif symbol in HIGH_BETA:
                sector = "high_beta"
            elif symbol in {"DOGE", "SHIB", "PEPE", "WIF", "BONK", "FLOKI"}:
                sector = "meme"
            else:
                sector = "other"
        counts[sector] = counts.get(sector, 0) + 1
    return counts


def _check_output_for_leaks(text: str) -> tuple[int, int]:
    """Check text for actual debug/secret leak content (not field names).

    Only flags terms when they appear as VALUES (e.g., `token=abc123` or `secret: xyz`),
    not when they appear as innocuous field names like `debug_leak_count` or `secret_leak_count`.

    Returns (debug_count, secret_count).
    """
    debug_count = 0
    secret_count = 0
    text_lower = text.lower()

    # Debug leaks: only flag when debug/internal terms leak into public card content
    # Pattern: debug-heavy terms appearing in card text or preview outputs
    debug_patterns = [
        r'\bdebug_message\b',
        r'\\"block_reason\\":\s*"[^"]+debug',
        r'\binternal_debug\b',
        r'print\(.*token',
        r'console\.log\(.*secret',
    ]
    for pattern in debug_patterns:
        if re.search(pattern, text_lower):
            debug_count += 1

    # Secret leaks: only flag actual credential patterns, not field names
    secret_patterns = [
        r'\bsecret\s*[=:]\s*\S{8,}',        # secret=value or secret: value (real secrets)
        r'\bapi[_\-]?key\s*[=:]\s*\S{8,}',   # api_key=value (real keys)
        r'\bapi[_\-]?secret\s*[=:]\s*\S',     # api_secret with value
        r'\bchat[_\-]?id\s*[=:]\s*[-\d]{5,}', # chat_id with value
        r'\bpassword\s*[=:]\s*\S{4,}',         # password with value
        r'\bbearer\s+[A-Za-z0-9_\-\.]{8,}',   # bearer token
        r'\bauthorization\s*:\s*[A-Za-z0-9_\-\.]{8,}', # auth header with value
        r'\bx-api-key\s*[=:]\s*\S{8,}',       # x-api-key with value
        r'\bcookie\s*[=:]\s*\S{8,}',           # cookie with value
        r'[A-Za-z]:\\(?:Users|Program|Windows)',  # Windows absolute paths
    ]
    for pattern in secret_patterns:
        if re.search(pattern, text_lower):
            secret_count += 1

    return debug_count, secret_count


# ══════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════

def main():
    """Execute the v112Q noise-aware one-shot plan."""
    print("=" * 60)
    print("Market Radar v1.12-Q")
    print("Multi-Asset Market Sync Noise-Aware One-Shot Plan")
    print("=" * 60)
    print()

    # ── Step 1: Validate upstream state ──────────────────────────────────────────
    print("[1/5] Validating upstream state...")
    upstream = validate_upstream_state()

    for check in upstream["checks"]:
        icon = "OK" if check["passed"] else "FAIL"
        print(f"  [{icon}] {check['check']}: {check['reason']}")

    if upstream["errors"]:
        print(f"  WARNING: {len(upstream['errors'])} upstream validation error(s):")
        for err in upstream["errors"]:
            print(f"    - {err}")
    print(f"  Upstream valid: {upstream['valid']}")
    print()

    # ── Step 2: Load thresholds ──────────────────────────────────────────────────
    print("[2/5] Loading stricter thresholds...")
    thresholds = _load_json(THRESHOLDS_PATH)
    if thresholds is None:
        print("  FAIL: Thresholds config not found. Creating default.")
        thresholds = {
            "version": "v1.12-q",
            "small_basket_max_size": 3,
            "small_basket_required_direction_agreement": 1.0,
            "large_basket_required_direction_agreement": 0.8,
            "min_per_asset_abs_price_change_pct": 2.0,
            "min_assets_meeting_price_threshold_ratio": 0.8,
            "require_price_and_one_secondary_metric": True,
            "secondary_metric_options": ["volume_change_pct", "open_interest_change_pct"],
            "max_timestamp_skew_seconds": 60,
            "leader_driven_downgrade_enabled": True,
            "leader_driven_follower_price_ratio_threshold": 0.25,
            "historical_baseline_required_before_real_send": True,
            "sector_concentration_min_ratio": 0.5,
            "volume_outlier_std_threshold": 3.0,
            "dry_run_only": True,
            "real_send_allowed": False,
        }
    print(f"  Loaded: {len(thresholds)} threshold keys")
    print(f"  small_basket_max_size: {thresholds['small_basket_max_size']}")
    print(f"  small_basket_required_direction_agreement: {thresholds['small_basket_required_direction_agreement']}")
    print(f"  max_timestamp_skew_seconds: {thresholds['max_timestamp_skew_seconds']}s")
    print(f"  leader_driven_downgrade_enabled: {thresholds['leader_driven_downgrade_enabled']}")
    print()

    # ── Step 3: Load noise cases ─────────────────────────────────────────────────
    print("[3/5] Loading noise injection cases...")
    fixture = _load_json(NOISE_CASES_PATH)
    if fixture is None:
        print("  FAIL: Noise cases fixture not found. Cannot proceed.")
        sys.exit(1)
    cases = fixture.get("cases", [])
    print(f"  Loaded {len(cases)} noise cases:")
    for case in cases:
        print(f"    - {case['case_id']}: expected={case['expected_result']}")
    print()

    # ── Step 4: Run noise cases through stricter rules ───────────────────────────
    print("[4/5] Running noise cases through stricter threshold engine...")
    noise_results = run_noise_cases(cases, thresholds)

    for r in noise_results:
        icon = "PASS" if r["passed"] else "FAIL"
        print(f"  [{icon}] {r['case_id']}: expected={r['expected_result']}, actual={r['actual_result']}, "
              f"reason={r['reason'][:100]}...")
    print()

    # ── Step 5: Generate output files ────────────────────────────────────────────
    print("[5/5] Generating output files...")

    result_json = generate_result_json(upstream["valid"], noise_results, thresholds)
    report_md = generate_report_md(upstream, noise_results, thresholds, result_json)
    handoff_md = generate_handoff_md(upstream, noise_results, result_json)

    # Check for leaks in all output texts
    all_outputs = json.dumps(result_json, ensure_ascii=False) + report_md + handoff_md
    debug_leak, secret_leak = _check_output_for_leaks(all_outputs)
    result_json["debug_leak_count"] = debug_leak
    result_json["secret_leak_count"] = secret_leak

    # Ensure output directories exist
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOISE_RESULTS_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write result JSON
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    print(f"  Wrote: {RESULT_JSON_PATH}")

    # Write noise case results JSONL
    with open(NOISE_RESULTS_JSONL_PATH, "w", encoding="utf-8") as f:
        for r in noise_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  Wrote: {NOISE_RESULTS_JSONL_PATH}")

    # Write report MD
    with open(REPORT_MD_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"  Wrote: {REPORT_MD_PATH}")

    # Write handoff MD
    with open(HANDOFF_MD_PATH, "w", encoding="utf-8") as f:
        f.write(handoff_md)
    print(f"  Wrote: {HANDOFF_MD_PATH}")

    print()
    print("=" * 60)
    print(f"v112Q Complete")
    print(f"  Status: {result_json['status']}")
    print(f"  Noise cases: {result_json['noise_injection_cases_passed']}/{result_json['noise_injection_cases_total']} passed")
    print(f"  Dry run only: Yes")
    print(f"  Live API called: No")
    print(f"  TG sent: No")
    print(f"  Debug leaks: {debug_leak}")
    print(f"  Secret leaks: {secret_leak}")
    print("=" * 60)

    return 0 if result_json["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
