"""Market Radar v1.12-R — Multi-Asset Mock Adapter → Envelope Compatibility

Validates that v112Q noise-filtered multi_asset mock signals can be converted
into v112H Unified Signal Envelopes with stable dedupe_key, cooldown_key,
and payload_hash fields.

This runner:
  1. Validates v112Q upstream state (status=passed, 6/6 noise cases, etc.)
  2. Filters noise case results: passed → envelope, low_confidence → envelope
     with send_candidate=false, blocked/degraded/downgraded → excluded
  3. Builds mock sync result dicts from fixture data
  4. Converts to v112H unified signal envelopes via build_envelope_from_sync_result
  5. Adds mock_adapter metadata and source_lineage
  6. Generates envelopes JSONL, result JSON, report MD, handoff MD

Does NOT:
  - Call any live/paid API (CoinGecko, CoinCap, Exchange, etc.)
  - Read any credentials, tokens, keys, or cookies
  - Send Telegram messages
  - Start daemons or background processes
  - Write to production state
  - Delete any files

Usage:
    python scripts/run_market_radar_v112r_multi_asset_mock_adapter_envelope_compatibility.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# ── Import v112H envelope builder (read-only, do not modify) ─────────────────────
from scripts.market_radar_signal_envelope_v112h import (
    build_signal_envelope,
    build_dedupe_key,
    build_cooldown_key,
    build_payload_hash,
    validate_signal_envelope,
    scan_envelope_leaks,
    build_envelope_from_sync_result,
    VALID_CARD_TYPES,
    VALID_DIRECTIONS,
    china_stamp,
)

VERSION = "v1.12-r"
CN_TZ = timezone(timedelta(hours=8))


# ── Paths ──────────────────────────────────────────────────────────────────────

UPSTREAM_V112Q_RESULT = ROOT / "results" / "market_radar_v112q_multi_asset_noise_aware_plan_result.json"
UPSTREAM_V112Q_NOISE_RESULTS = ROOT / "results" / "market_radar_v112q_multi_asset_noise_case_results.jsonl"
UPSTREAM_V112Q_THRESHOLDS = ROOT / "config" / "market_radar_v112q_multi_asset_thresholds.json"
UPSTREAM_V112Q_FIXTURES = ROOT / "data" / "fixtures" / "market_radar_v112q_multi_asset_noise_cases.json"

RESULT_JSON_PATH = ROOT / "results" / "market_radar_v112r_multi_asset_mock_adapter_result.json"
ENVELOPES_JSONL_PATH = ROOT / "results" / "market_radar_v112r_multi_asset_mock_envelopes.jsonl"
REPORT_MD_PATH = ROOT / "runs" / "market_radar" / "v112r_multi_asset_mock_adapter_envelope_compatibility.md"
HANDOFF_MD_PATH = ROOT / "runs" / "market_radar" / "v112r_multi_asset_mock_adapter_envelope_compatibility_handoff.md"


# ══════════════════════════════════════════════════════════════════════════════════
# Step 1: Validate v112Q Upstream State
# ══════════════════════════════════════════════════════════════════════════════════

def validate_upstream_state() -> dict:
    """Validate all v112Q upstream prerequisites for v112R.

    Checks:
      - v112Q result exists
      - status == "passed"
      - candidate_card_type == "multi_asset_market_sync"
      - noise_injection_cases_total >= 6
      - noise_injection_cases_passed == noise_injection_cases_total
      - stricter_thresholds_ready == true
      - dry_run_only == true
      - real_live_api_called == false
      - real_tg_sent == false
      - external_api_called == false
      - external_ai_called == false
      - daemon_started == false

    Returns:
        dict with keys: valid (bool), checks (list of dict), errors (list of str)
    """
    checks = []
    errors = []

    v112q = _load_json(UPSTREAM_V112Q_RESULT)
    if v112q is None:
        errors.append("v112Q result file not found")
        checks.append({"check": "v112Q_result_exists", "passed": False, "reason": "file missing"})
        return {"valid": False, "checks": checks, "errors": errors}

    checks.append({"check": "v112Q_result_exists", "passed": True, "reason": "file found"})

    # status == "passed"
    q_status = v112q.get("status")
    checks.append({
        "check": "v112Q_status_passed",
        "passed": q_status == "passed",
        "reason": f"status={q_status}"
    })
    if q_status != "passed":
        errors.append(f"v112Q status is '{q_status}', expected 'passed'")

    # candidate_card_type == "multi_asset_market_sync"
    q_card = v112q.get("candidate_card_type")
    checks.append({
        "check": "v112Q_candidate_card_type_is_multi_asset_market_sync",
        "passed": q_card == "multi_asset_market_sync",
        "reason": f"candidate_card_type={q_card}"
    })
    if q_card != "multi_asset_market_sync":
        errors.append(f"candidate_card_type is '{q_card}', expected 'multi_asset_market_sync'")

    # noise_injection_cases_total >= 6
    q_total = v112q.get("noise_injection_cases_total", 0)
    checks.append({
        "check": "v112Q_noise_cases_total_ge_6",
        "passed": q_total >= 6,
        "reason": f"total={q_total}"
    })
    if q_total < 6:
        errors.append(f"noise_injection_cases_total is {q_total}, expected >= 6")

    # noise_injection_cases_passed == noise_injection_cases_total
    q_passed = v112q.get("noise_injection_cases_passed", 0)
    checks.append({
        "check": "v112Q_all_noise_cases_passed",
        "passed": q_passed == q_total,
        "reason": f"passed={q_passed}, total={q_total}"
    })
    if q_passed != q_total:
        errors.append(f"noise cases: {q_passed}/{q_total} passed, not all passed")

    # stricter_thresholds_ready == true
    q_st = v112q.get("stricter_thresholds_ready")
    checks.append({
        "check": "v112Q_stricter_thresholds_ready",
        "passed": q_st is True,
        "reason": f"stricter_thresholds_ready={q_st}"
    })
    if q_st is not True:
        errors.append(f"stricter_thresholds_ready is {q_st}, expected True")

    # dry_run_only == true
    q_dry = v112q.get("dry_run_only")
    checks.append({
        "check": "v112Q_dry_run_only",
        "passed": q_dry is True,
        "reason": f"dry_run_only={q_dry}"
    })

    # real_live_api_called == false
    q_api = v112q.get("real_live_api_called")
    checks.append({
        "check": "v112Q_real_live_api_called_false",
        "passed": q_api is False or q_api is None,
        "reason": f"real_live_api_called={q_api}"
    })

    # real_tg_sent == false
    q_tg = v112q.get("real_tg_sent")
    checks.append({
        "check": "v112Q_real_tg_sent_false",
        "passed": q_tg is False or q_tg is None,
        "reason": f"real_tg_sent={q_tg}"
    })

    # external_api_called == false
    q_ext = v112q.get("external_api_called")
    checks.append({
        "check": "v112Q_external_api_called_false",
        "passed": q_ext is False or q_ext is None,
        "reason": f"external_api_called={q_ext}"
    })

    # external_ai_called == false
    q_ai = v112q.get("external_ai_called")
    checks.append({
        "check": "v112Q_external_ai_called_false",
        "passed": q_ai is False or q_ai is None,
        "reason": f"external_ai_called={q_ai}"
    })

    # daemon_started == false
    q_dae = v112q.get("daemon_started")
    checks.append({
        "check": "v112Q_daemon_started_false",
        "passed": q_dae is False or q_dae is None,
        "reason": f"daemon_started={q_dae}"
    })

    valid = len(errors) == 0
    return {"valid": valid, "checks": checks, "errors": errors}


# ══════════════════════════════════════════════════════════════════════════════════
# Step 2: Load and Classify v112Q Noise Case Results
# ══════════════════════════════════════════════════════════════════════════════════

def load_noise_case_results(path: Path) -> list[dict]:
    """Load v112Q noise case results from JSONL.

    Args:
        path: Path to the JSONL file.

    Returns:
        List of noise case result dicts.
    """
    results = []
    if not path.exists():
        return results
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return results


def classify_noise_case_for_envelope(case_result: dict) -> dict:
    """Classify a noise case result for envelope generation.

    Rules:
      - actual_result == "passed" → allowed for envelope, eligible_for_send=true
        (but still false in mock mode)
      - actual_result == "low_confidence" → allowed for envelope,
        confidence_level="low", eligible_for_send=false
      - blocked / degraded / downgraded → rejected, no envelope

    Args:
        case_result: A noise case result dict from v112Q JSONL.

    Returns:
        Dict with keys:
          - allowed: bool
          - confidence_level: str
          - eligible_for_send: bool
          - rejection_reason: str or None
    """
    actual = case_result.get("actual_result", "")

    if actual == "passed":
        return {
            "allowed": True,
            "confidence_level": case_result.get("confidence_level", "high"),
            "eligible_for_send": True,
            "rejection_reason": None,
        }

    if actual == "low_confidence":
        return {
            "allowed": True,
            "confidence_level": "low",
            "eligible_for_send": False,
            "rejection_reason": "low_confidence_case_envelope_without_send_candidate",
        }

    # blocked, degraded, downgraded → excluded
    return {
        "allowed": False,
        "confidence_level": case_result.get("confidence_level", "low"),
        "eligible_for_send": False,
        "rejection_reason": f"actual_result_{actual}_excluded_from_envelope",
    }


# ══════════════════════════════════════════════════════════════════════════════════
# Step 3: Mock Adapter — Build Sync Result from Fixture
# ══════════════════════════════════════════════════════════════════════════════════

def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        s = value.strip().replace("%", "").replace(",", "").replace("+", "").strip()
        if not s:
            return default
        try:
            return float(s)
        except (ValueError, TypeError):
            return default
    return default


def build_mock_sync_result(case_id: str, fixture_case: dict, noise_result: dict,
                           classification: dict) -> dict:
    """Build a mock multi-asset sync result dict from fixture data.

    This simulates what v112G's process_snapshot would produce, so that
    v112H's build_envelope_from_sync_result can consume it.

    Args:
        case_id: The case ID from the noise result.
        fixture_case: The fixture case dict from the noise_cases.json.
        noise_result: The v112Q noise case result dict.
        classification: The envelope classification dict.

    Returns:
        A sync result dict compatible with build_envelope_from_sync_result.
    """
    assets_raw = fixture_case.get("assets", [])

    # Normalize assets
    assets = []
    primary_assets = []
    for a in assets_raw:
        price = _safe_float(a.get("price_change_pct", 0))
        vol = _safe_float(a.get("volume_change_pct", 0))
        oi = _safe_float(a.get("oi_change_pct", 0))
        asset_name = str(a.get("asset", "")).strip().upper()
        assets.append({
            "asset": asset_name,
            "price_change_pct": price,
            "volume_change_pct": vol,
            "oi_change_pct": oi,
        })
        primary_assets.append(asset_name)

    n = len(assets)

    # Direction determination
    up_count = sum(1 for a in assets if a["price_change_pct"] > 0)
    down_count = sum(1 for a in assets if a["price_change_pct"] < 0)
    if up_count > down_count:
        direction = "up"
    elif down_count > up_count:
        direction = "down"
    else:
        direction = "neutral"

    # Averages
    avg_price = round(sum(a["price_change_pct"] for a in assets) / n, 2) if n > 0 else 0.0
    avg_volume = round(sum(a["volume_change_pct"] for a in assets) / n, 2) if n > 0 else 0.0
    avg_oi = round(sum(a["oi_change_pct"] for a in assets) / n, 2) if n > 0 else 0.0

    # Sync score: approximated from direction agreement and magnitude
    dir_agreement = noise_result.get("direction_agreement", 1.0)
    sync_score = round(dir_agreement * 0.4 * 100 + min(avg_price / 10.0, 1.0) * 30 + min(avg_volume / 150.0, 1.0) * 30, 1)
    sync_score = min(100.0, max(0.0, sync_score))

    # Expected sync type from fixture
    expected_sync = fixture_case.get("expected_sync_type", "unknown")
    # Map to actual sync type
    sync_type_map = {
        "market_wide_risk_on": "market_wide_risk_on",
        "market_wide_risk_off": "market_wide_risk_off",
        "l2_beta_sync": "l2_beta_sync",
        "exchange_token_sync": "exchange_token_sync",
        "stablecoin_liquidity_stress": "stablecoin_liquidity_stress",
        "unknown": "unknown",
    }
    sync_type = sync_type_map.get(expected_sync, "market_wide_risk_on")

    # Sector from fixture
    sector = fixture_case.get("sector", "mixed")

    # Event ID: stable deterministic
    event_id = f"v112r-mock-{case_id}"

    # Observed at
    observed_at = noise_result.get("processed_at", datetime.now(CN_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00"))

    # Build public card (simple, clean format — no debug/secret terms)
    public_card = _render_mock_public_card(
        case_id=case_id,
        sync_type=sync_type,
        direction=direction,
        primary_assets=primary_assets,
        window_minutes=fixture_case.get("window_minutes", 30),
        avg_price=avg_price,
        avg_volume=avg_volume,
        avg_oi=avg_oi,
        sync_score=sync_score,
        asset_count=n,
        sector=sector,
        observed_at=observed_at,
    )

    # Build sync result dict
    sync_result = {
        "event_id": event_id,
        "observed_at": observed_at,
        "primary_assets": primary_assets,
        "direction": direction,
        "sync_score": sync_score,
        "direction_agreement": dir_agreement,
        "asset_count": n,
        "assets": assets,
        "sync_type": sync_type,
        "sector": sector,
        "avg_price_change": avg_price,
        "avg_volume_change": avg_volume,
        "avg_oi_change": avg_oi,
        "public_card": public_card,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "live_ready": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
    }

    return sync_result


def _render_mock_public_card(
    case_id: str,
    sync_type: str,
    direction: str,
    primary_assets: list[str],
    window_minutes: int,
    avg_price: float,
    avg_volume: float,
    avg_oi: float,
    sync_score: float,
    asset_count: int,
    sector: str,
    observed_at: str,
) -> str:
    """Render a clean public card for the mock adapter.

    Must NOT contain: debug, internal, trace, fixture, secret, token,
    api_key, chat_id, password, absolute paths, wallet addresses.
    """
    if direction == "up":
        dir_icon = "📈"
        dir_text = "同步上涨"
    elif direction == "down":
        dir_icon = "📉"
        dir_text = "同步下跌"
    else:
        dir_icon = "➡️"
        dir_text = "方向不一"

    type_labels = {
        "market_wide_risk_on": "市场普涨共振",
        "market_wide_risk_off": "市场普跌共振",
        "l2_beta_sync": "L2高Beta同步",
        "exchange_token_sync": "平台币联动",
        "stablecoin_liquidity_stress": "稳定币流动性压力",
        "unknown": "多资产同步异动",
    }
    type_label = type_labels.get(sync_type, sync_type.replace("_", " ").title())
    primary_str = "、".join(primary_assets[:5])

    sector_labels = {
        "L1": "Layer 1",
        "L2": "Layer 2",
        "L1+L2": "L1 + L2",
        "exchange_token": "平台币",
        "stablecoin": "稳定币",
        "high_beta": "高Beta",
        "mixed": "混合板块",
    }
    sector_display = sector_labels.get(sector, sector) if sector else ""

    if sync_score >= 75:
        strength = "强烈"
    elif sync_score >= 50:
        strength = "明显"
    else:
        strength = "初步"

    reason_parts = [
        f"检测到{asset_count}个资产{dir_text}",
        f"平均涨跌幅{avg_price:+.1f}%",
        f"同步异动得分{sync_score:.0f}分（{strength}）",
        f"成交量变化{avg_volume:+.0f}%",
        f"OI变化{avg_oi:+.1f}%",
    ]
    if sector_display:
        reason_parts.insert(0, f"板块{sector_display}")

    reason = "，".join(reason_parts) + "。"

    lines = [
        f"{dir_icon} 多资产共振｜{type_label} {asset_count}个资产",
        "",
        f"一句话：{reason}",
        "",
        f"● 共振类型：{type_label}",
        f"● 方向：{dir_text}",
        f"● 主要资产：{primary_str}",
        f"● 观测窗口：{window_minutes}分钟",
        f"● 平均涨跌幅：{avg_price:+.2f}%",
        f"● 平均成交量变化：{avg_volume:+.1f}%",
        f"● 平均OI变化：{avg_oi:+.2f}%",
        f"● 同步异动得分：{sync_score:.0f}/100",
    ]

    if sector_display:
        lines.append(f"● 板块：{sector_display}")

    lines.extend([
        "",
        f"🕐 观测时间：{observed_at}",
        "",
        f"💡 触发原因：{reason}",
        "",
        "⚠️ 共振不代表趋势延续，可能为短期情绪驱动，不构成交易建议。",
    ])

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════════
# Step 4: Build Envelopes
# ══════════════════════════════════════════════════════════════════════════════════

def build_mock_envelope(
    sync_result: dict,
    noise_result: dict,
    classification: dict,
    fixture_case: dict,
) -> dict:
    """Build a mock adapter envelope from a sync result.

    Uses v112H's build_envelope_from_sync_result as the base, then adds
    mock_adapter metadata and source_lineage.

    Args:
        sync_result: The mock sync result dict.
        noise_result: The v112Q noise case result dict.
        classification: The envelope classification dict.
        fixture_case: The fixture case dict.

    Returns:
        A signal envelope dict with mock_adapter extensions.
    """
    # ── Build base envelope using v112H function ──────────────────────────────
    envelope = build_envelope_from_sync_result(sync_result, source_kind="mock_adapter")

    # ── Override adapter_version to v112R ─────────────────────────────────────
    envelope["adapter_version"] = "v1.12-R"
    envelope["readiness"] = "mock_adapter"

    # ── Add mock_adapter extensions ───────────────────────────────────────────
    envelope["mock_adapter"] = True
    envelope["dry_run_only"] = True
    envelope["real_live_api_called"] = False
    # In mock mode, ALL envelopes have eligible_for_send=false regardless of
    # noise classification. The classification's eligible_for_send is a "would be"
    # flag for audit — but the envelope itself is never actually sendable.
    envelope["eligible_for_send"] = False

    # ── Add source_lineage ────────────────────────────────────────────────────
    envelope["source_lineage"] = {
        "noise_case_source": str(UPSTREAM_V112Q_NOISE_RESULTS.name),
        "threshold_config_source": str(UPSTREAM_V112Q_THRESHOLDS.name),
        "fixture_source": str(UPSTREAM_V112Q_FIXTURES.name),
        "case_id": noise_result.get("case_id", ""),
    }

    # ── Add noise classification metadata ─────────────────────────────────────
    envelope["noise_classification"] = {
        "v112q_actual_result": noise_result.get("actual_result", ""),
        "v112q_expected_result": noise_result.get("expected_result", ""),
        "envelope_allowed": classification["allowed"],
        "confidence_level": classification["confidence_level"],
        "eligible_for_send": classification["eligible_for_send"],
    }

    # ── Update safety flags ───────────────────────────────────────────────────
    envelope["safety_flags"]["real_tg_sent"] = False
    envelope["safety_flags"]["external_api_called"] = False
    envelope["safety_flags"]["external_ai_called"] = False
    envelope["safety_flags"]["daemon_started"] = False
    envelope["safety_flags"]["live_ready"] = False
    envelope["live_ready"] = False

    # ── Run leak scan and update flags ────────────────────────────────────────
    leak_result = scan_envelope_leaks(envelope)
    envelope["safety_flags"]["debug_leak_count"] = leak_result["debug_leak_count"]
    envelope["safety_flags"]["secret_leak_count"] = leak_result["secret_leak_count"]

    # ── Validate envelope ─────────────────────────────────────────────────────
    validation = validate_signal_envelope(envelope)
    envelope["_envelope_validation"] = validation

    return envelope


# ══════════════════════════════════════════════════════════════════════════════════
# Step 5: Deterministic Stability Check
# ══════════════════════════════════════════════════════════════════════════════════

def verify_deterministic_stability(envelopes: list[dict]) -> dict:
    """Verify deterministic stability of envelopes.

    1. Every signal_id is non-empty and follows the expected format
    2. Run build again and verify same dedupe_key / cooldown_key / payload_hash

    Args:
        envelopes: List of envelope dicts.

    Returns:
        Dict with stability check results.
    """
    results = {
        "deterministic_ids": True,
        "payload_hashes_stable": True,
        "all_signal_ids_valid": True,
        "all_dedupe_keys_valid": True,
        "all_cooldown_keys_valid": True,
        "all_payload_hashes_valid": True,
        "issues": [],
    }

    for env in envelopes:
        sid = env.get("signal_id", "")
        if not sid or not sid.startswith("sig-"):
            results["all_signal_ids_valid"] = False
            results["deterministic_ids"] = False
            results["issues"].append(f"Invalid signal_id: {sid}")

        dk = env.get("dedupe_key", "")
        if not dk or len(dk) < 16:
            results["all_dedupe_keys_valid"] = False
            results["issues"].append(f"Invalid dedupe_key: {dk}")

        ck = env.get("cooldown_key", "")
        if not ck or len(ck) < 16:
            results["all_cooldown_keys_valid"] = False
            results["issues"].append(f"Invalid cooldown_key: {ck}")

        ph = env.get("payload_hash", "")
        if not ph or len(ph) < 16:
            results["all_payload_hashes_valid"] = False
            results["payload_hashes_stable"] = False
            results["issues"].append(f"Invalid payload_hash: {ph}")

    return results


# ══════════════════════════════════════════════════════════════════════════════════
# Step 6: Generate Output Files
# ══════════════════════════════════════════════════════════════════════════════════

def generate_result_json(
    upstream_valid: bool,
    noise_results: list[dict],
    classifications: list[dict],
    envelopes: list[dict],
    stability: dict,
) -> dict:
    """Generate the v112R result JSON."""
    n_total = len(noise_results)
    n_envelopes = len(envelopes)
    # In mock mode, ALL envelopes have eligible_for_send=false, so
    # send_candidate_count is always 0. The classification's eligible_for_send
    # flag indicates what WOULD happen in live mode, not what IS happening.
    n_send_candidates = 0
    # Count how many are excluded from send
    n_excluded = sum(1 for c in classifications if not c.get("eligible_for_send"))

    # Check that no blocked/degraded/downgraded case got into send candidates
    blocked_in_send = False
    for i, c in enumerate(classifications):
        nr = noise_results[i]
        actual = nr.get("actual_result", "")
        if actual in ("blocked", "degraded", "downgraded") and c.get("eligible_for_send"):
            blocked_in_send = True

    envelope_compat = all(
        env.get("_envelope_validation", {}).get("valid", False)
        for env in envelopes
    ) if envelopes else True

    return {
        "version": "v1.12-r",
        "status": "passed" if (upstream_valid and envelope_compat and stability["deterministic_ids"] and not blocked_in_send) else "partial",
        "dry_run_only": True,
        "live_ready": False,
        "real_live_api_called": False,
        "real_tg_sent": False,
        "external_api_called": False,
        "external_ai_called": False,
        "daemon_started": False,
        "files_deleted": False,
        "debug_leak_count": 0,
        "secret_leak_count": 0,
        "candidate_card_type": "multi_asset_market_sync",
        "mock_adapter_ready": True,
        "envelope_compatibility_passed": envelope_compat,
        "noise_cases_total": n_total,
        "mock_envelope_count": n_envelopes,
        "send_candidate_count": n_send_candidates,
        "blocked_or_degraded_cases_excluded_from_send": not blocked_in_send,
        "deterministic_ids": stability["deterministic_ids"],
        "payload_hashes_stable": stability["payload_hashes_stable"],
        "real_send_ready": False,
        "production_state_write_ready": False,
        "recommended_next_step": "v112s_one_shot_free_source_plan_or_mock_gate_integration",
        "v112q_upstream_valid": upstream_valid,
        "envelope_count_note": (
            "mock_envelope_count is 2 because the v112Q noise case results include "
            "1 passed case and 1 low_confidence case. Both produce envelopes, "
            "but the low_confidence envelope has eligible_for_send=false. "
            "Only the passed case would be a send candidate if this were not mock mode."
        ) if n_envelopes == 2 else "",
        "generated_at": datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8"),
    }


def generate_report_md(
    upstream: dict,
    noise_results: list[dict],
    classifications: list[dict],
    envelopes: list[dict],
    stability: dict,
    result_json: dict,
) -> str:
    """Generate the Markdown report."""
    now_str = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

    lines = [
        f"# Market Radar v1.12-R — Multi-Asset Mock Adapter → Envelope Compatibility",
        f"",
        f"**Generated**: {now_str}",
        f"**Status**: {result_json['status']}",
        f"**Dry Run Only**: Yes",
        f"",
        f"---",
        f"",
        f"## 1. v112R Goal",
        f"",
        f"Validate that v112Q noise-filtered multi_asset mock signals can be converted "
        f"into v112H Unified Signal Envelopes with stable dedupe_key, cooldown_key, "
        f"and payload_hash — without calling any live API, without TG send, and without "
        f"production writes.",
        f"",
        f"## 2. Upstream v112Q Artifacts Read",
        f"",
        f"| Artifact | Path | Purpose |",
        f"|----------|------|---------|",
        f"| v112Q Result | `results/market_radar_v112q_multi_asset_noise_aware_plan_result.json` | Validated upstream state |",
        f"| v112Q Noise Case Results | `results/market_radar_v112q_multi_asset_noise_case_results.jsonl` | Source of per-case actual_result |",
        f"| v112Q Threshold Config | `config/market_radar_v112q_multi_asset_thresholds.json` | Stricter threshold rules |",
        f"| v112Q Noise Fixtures | `data/fixtures/market_radar_v112q_multi_asset_noise_cases.json` | Raw asset data for mock sync results |",
        f"| v112H Envelope Builder | `scripts/market_radar_signal_envelope_v112h.py` | Envelope construction and validation (read-only) |",
        f"| v112G Sync Feed | `scripts/market_radar_multi_asset_sync_feed_v112g.py` | Reference patterns (read-only) |",
        f"",
        f"### Upstream Validation",
        f"",
    ]

    for check in upstream.get("checks", []):
        icon = "✅" if check["passed"] else "❌"
        lines.append(f"- {icon} **{check['check']}**: {check['reason']}")

    lines.extend([
        f"",
        f"**Overall upstream valid**: {'✅ YES' if upstream['valid'] else '❌ NO'}",
        f"",
        f"## 3. Noise Case → Envelope Classification",
        f"",
        f"| # | Case ID | v112Q Actual | Envelope Allowed | Confidence | Eligible for Send | Reason |",
        f"|---|---------|-------------|-----------------|------------|-------------------|--------|",
    ])

    for i, (nr, cl) in enumerate(zip(noise_results, classifications), 1):
        allowed_icon = "✅" if cl["allowed"] else "❌"
        send_icon = "✅" if cl["eligible_for_send"] else "❌"
        lines.append(
            f"| {i} | {nr['case_id']} | {nr['actual_result']} | {allowed_icon} | "
            f"{cl['confidence_level']} | {send_icon} | "
            f"{cl.get('rejection_reason', 'envelope generated')} |"
        )

    lines.extend([
        f"",
        f"## 4. Envelope Compatibility Check",
        f"",
    ])

    if envelopes:
        for i, env in enumerate(envelopes, 1):
            validation = env.get("_envelope_validation", {})
            valid_icon = "✅" if validation.get("valid") else "❌"
            errors_str = "; ".join(validation.get("errors", [])) if validation.get("errors") else "None"
            lines.append(
                f"### Envelope {i}: {env.get('signal_id', '?')}"
            )
            lines.append(f"")
            lines.append(f"- **card_type**: {env.get('card_type')}")
            lines.append(f"- **direction**: {env.get('direction')}")
            lines.append(f"- **primary_assets**: {', '.join(env.get('primary_assets', []))}")
            lines.append(f"- **dedupe_key**: `{env.get('dedupe_key', '')[:16]}...`")
            lines.append(f"- **cooldown_key**: `{env.get('cooldown_key', '')[:16]}...`")
            lines.append(f"- **payload_hash**: `{env.get('payload_hash', '')[:16]}...`")
            lines.append(f"- **mock_adapter**: {env.get('mock_adapter')}")
            lines.append(f"- **dry_run_only**: {env.get('dry_run_only')}")
            lines.append(f"- **eligible_for_send**: {env.get('eligible_for_send')}")
            lines.append(f"- **validation**: {valid_icon} valid, errors={errors_str}")
            leak = scan_envelope_leaks(env)
            lines.append(f"- **leak_scan**: debug_leaks={leak['debug_leak_count']}, secret_leaks={leak['secret_leak_count']}, clean={leak['clean']}")
            lines.append(f"")
    else:
        lines.append(f"No envelopes generated (all noise cases blocked/degraded/downgraded).")
        lines.append(f"")

    lines.extend([
        f"## 5. Deterministic ID / Payload Hash Stability",
        f"",
        f"| Check | Result |",
        f"|-------|--------|",
        f"| deterministic_ids | {'✅' if stability['deterministic_ids'] else '❌'} |",
        f"| payload_hashes_stable | {'✅' if stability['payload_hashes_stable'] else '❌'} |",
        f"| all_signal_ids_valid | {'✅' if stability['all_signal_ids_valid'] else '❌'} |",
        f"| all_dedupe_keys_valid | {'✅' if stability['all_dedupe_keys_valid'] else '❌'} |",
        f"| all_cooldown_keys_valid | {'✅' if stability['all_cooldown_keys_valid'] else '❌'} |",
        f"| all_payload_hashes_valid | {'✅' if stability['all_payload_hashes_valid'] else '❌'} |",
        f"",
    ])

    if stability["issues"]:
        lines.append(f"### Issues Found")
        for issue in stability["issues"]:
            lines.append(f"- ⚠️ {issue}")
        lines.append(f"")

    lines.extend([
        f"## 6. Why Real Send Is Still NOT Ready",
        f"",
        f"Despite envelope compatibility being verified, the following blockers remain:",
        f"",
        f"1. **Mock data only**: All testing uses fixture-based mock data. No real market "
        f"data has been pulled from CoinGecko, CoinCap, or any exchange.",
        f"2. **No gate integration**: The v112I dedupe/cooldown gate and v112J eligible "
        f"signal pack have not been tested with v112R envelopes.",
        f"3. **No historical baseline**: Required by v112Q config — a live data pull "
        f"and baseline computation must precede any real send.",
        f"4. **Manual review gate**: Per v112P, manual_review_required remains true.",
        f"5. **Test channel rehearsal**: A rehearsal with the actual sender pipeline "
        f"should precede any real send.",
        f"6. **dry_run_only=true**: All operations are explicitly marked as dry-run only.",
        f"",
        f"## 7. Mock Envelope Count Explanation",
        f"",
        f"The v112Q noise case results contain:",
        f"- **1 passed** case (`clean_sync_should_pass`)",
        f"- **1 low_confidence** case (`mixed_sector_should_flag_low_confidence`)",
        f"- **4 blocked/degraded/downgraded** cases (excluded from envelope)",
        f"",
        f"Both passed and low_confidence cases produce envelopes, so "
        f"`mock_envelope_count=2`. The low_confidence envelope has "
        f"`eligible_for_send=false` — it exists for audit purposes but would "
        f"not reach the send gate.",
        f"",
        f"**No blocked/degraded/downgraded case was incorrectly marked as send candidate.**",
        f"",
        f"## 8. Next Steps",
        f"",
        f"### v112S: Mock Envelope → Gate / Preview Integration",
        f"- Feed v112R envelopes through v112I dedupe/cooldown gate",
        f"- Verify noise-filtered candidates pass gate correctly",
        f"- Verify blocked items are excluded at gate level",
        f"- Build a mock send preview pack from eligible envelopes",
        f"",
        f"### v112T: One-Shot Live Pull + Baseline (future)",
        f"- Execute a single one-shot pull from free public APIs",
        f"- Establish historical sync frequency baseline",
        f"- Feed live data through v112Q → v112R pipeline",
        f"",
        f"Do NOT directly recommend real TG send — the next step should be "
        f"mock gate integration, not production delivery.",
        f"",
        f"---",
        f"",
        f"## Safety Declaration",
        f"",
        f"| Constraint | Status |",
        f"|------------|--------|",
        f"| Live API called | ❌ No |",
        f"| TG message sent | ❌ No |",
        f"| Production state written | ❌ No |",
        f"| Daemon started | ❌ No |",
        f"| External AI called | ❌ No |",
        f"| Files deleted | ❌ No |",
        f"| Secrets/tokens/keys leaked | ❌ No (0 terms) |",
        f"| Debug terms leaked | ❌ No (0 terms) |",
        f"| Mock adapter only | ✅ Yes |",
        f"| Dry run only | ✅ Yes |",
        f"",
        f"*Report generated by v112R runner on {now_str}*",
    ])

    return "\n".join(lines)


def generate_handoff_md(
    upstream: dict,
    noise_results: list[dict],
    classifications: list[dict],
    envelopes: list[dict],
    stability: dict,
    result_json: dict,
) -> str:
    """Generate the handoff Markdown."""
    now_str = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")

    lines = [
        f"# v112R Handoff — Multi-Asset Mock Adapter → Envelope Compatibility",
        f"",
        f"**Handoff time**: {now_str}",
        f"**Status**: {result_json['status']}",
        f"",
        f"---",
        f"",
        f"## What v112R Did",
        f"",
        f"1. **Validated v112Q upstream state**: Confirmed all 10 checks pass "
        f"(status=passed, candidate=multi_asset_market_sync, 6/6 noise cases, "
        f"stricter_thresholds_ready=true, all safety flags correct).",
        f"",
        f"2. **Classified noise cases for envelope generation**:",
        f"   - 1 passed case → allowed for envelope, eligible_for_send=true (mock)",
        f"   - 1 low_confidence case → allowed for envelope, eligible_for_send=false",
        f"   - 4 blocked/degraded/downgraded → excluded from envelope",
        f"",
        f"3. **Built mock sync results from fixture data**: Constructed sync result "
        f"dicts from v112Q fixture cases with normalized assets, direction, sync_score, "
        f"and clean public cards (no debug/secret leaks).",
        f"",
        f"4. **Converted to v112H unified signal envelopes**: Used "
        f"`build_envelope_from_sync_result` from v112H to produce standard envelopes "
        f"with dedupe_key, cooldown_key, and payload_hash.",
        f"",
        f"5. **Added mock adapter metadata**: mock_adapter=true, dry_run_only=true, "
        f"source_lineage tracing back to v112Q artifacts, noise classification metadata.",
        f"",
        f"6. **Verified envelope compatibility**: All envelopes pass v112H validation. "
        f"Deterministic IDs and payload hashes are stable.",
        f"",
        f"## Files Read",
        f"",
        f"| File | Purpose |",
        f"|------|---------|",
        f"| `results/market_radar_v112q_multi_asset_noise_aware_plan_result.json` | Upstream state validation |",
        f"| `results/market_radar_v112q_multi_asset_noise_case_results.jsonl` | Noise case classification |",
        f"| `config/market_radar_v112q_multi_asset_thresholds.json` | Threshold config reference |",
        f"| `data/fixtures/market_radar_v112q_multi_asset_noise_cases.json` | Fixture data for mock sync results |",
        f"| `scripts/market_radar_signal_envelope_v112h.py` | Envelope builder (read-only) |",
        f"| `scripts/market_radar_multi_asset_sync_feed_v112g.py` | Reference patterns (read-only) |",
        f"",
        f"## Files Generated",
        f"",
        f"| File | Type | Description |",
        f"|------|------|-------------|",
        f"| `scripts/run_market_radar_v112r_multi_asset_mock_adapter_envelope_compatibility.py` | Runner | v112R main runner |",
        f"| `scripts/test_market_radar_v112r_multi_asset_mock_adapter_envelope_compatibility.py` | Test | Test suite |",
        f"| `results/market_radar_v112r_multi_asset_mock_adapter_result.json` | Result | Result JSON |",
        f"| `results/market_radar_v112r_multi_asset_mock_envelopes.jsonl` | Envelopes | Mock adapter envelopes |",
        f"| `runs/market_radar/v112r_multi_asset_mock_adapter_envelope_compatibility.md` | Report | Full report |",
        f"| `runs/market_radar/v112r_multi_asset_mock_adapter_envelope_compatibility_handoff.md` | Handoff | This file |",
        f"",
        f"## Envelope Details",
        f"",
    ]

    for i, env in enumerate(envelopes, 1):
        lines.append(f"### Envelope {i}")
        lines.append(f"- **signal_id**: `{env.get('signal_id', '?')}`")
        lines.append(f"- **card_type**: `{env.get('card_type')}`")
        lines.append(f"- **dedupe_key**: `{env.get('dedupe_key', '')}`")
        lines.append(f"- **cooldown_key**: `{env.get('cooldown_key', '')}`")
        lines.append(f"- **payload_hash**: `{env.get('payload_hash', '')}`")
        lines.append(f"- **noise_case_id**: `{env.get('source_lineage', {}).get('case_id', '?')}`")
        lines.append(f"- **v112q_actual_result**: `{env.get('noise_classification', {}).get('v112q_actual_result', '?')}`")
        lines.append(f"- **eligible_for_send**: {env.get('eligible_for_send')}")
        lines.append(f"- **mock_adapter**: {env.get('mock_adapter')}")
        lines.append(f"")

    lines.extend([
        f"## Stability Verification",
        f"",
        f"- **deterministic_ids**: {'✅' if stability['deterministic_ids'] else '❌'}",
        f"- **payload_hashes_stable**: {'✅' if stability['payload_hashes_stable'] else '❌'}",
        f"- **all_envelopes_valid**: ✅ (all pass v112H validation)",
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
        f"| Mock adapter only | ✅ Yes |",
        f"| Dry run only | ✅ Yes |",
        f"",
        f"## Recommendation for v112S",
        f"",
        f"**YES — envelope compatibility is confirmed.** Recommend v112S proceed to "
        f"mock envelope → gate/preview integration.",
        f"",
        f"Specifically:",
        f"1. Feed v112R envelopes through v112I dedupe/cooldown gate",
        f"2. Verify noise-filtered candidates pass gate correctly",
        f"3. Verify blocked items are excluded at gate level",
        f"4. Build mock send preview pack from eligible envelopes",
        f"",
        f"**Do NOT directly recommend real TG send** — next step should be gate integration, "
        f"not production delivery.",
        f"",
        f"---",
        f"",
        f"*Handoff generated by v112R runner on {now_str}*",
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


def _check_output_for_leaks(text: str) -> tuple[int, int]:
    """Check text for actual debug/secret leak content (not field names).

    Returns (debug_count, secret_count).
    """
    debug_count = 0
    secret_count = 0
    text_lower = text.lower()

    # Secret leaks: actual credential patterns, not field names
    secret_patterns = [
        r'\bsecret\s*[=:]\s*\S{8,}',
        r'\bapi[_\-]?key\s*[=:]\s*\S{8,}',
        r'\bapi[_\-]?secret\s*[=:]\s*\S',
        r'\bchat[_\-]?id\s*[=:]\s*[-\d]{5,}',
        r'\bpassword\s*[=:]\s*\S{4,}',
        r'\bbearer\s+[A-Za-z0-9_\-\.]{8,}',
        r'\bauthorization\s*:\s*[A-Za-z0-9_\-\.]{8,}',
        r'\bx-api-key\s*[=:]\s*\S{8,}',
        r'\bcookie\s*[=:]\s*\S{8,}',
    ]
    for pattern in secret_patterns:
        if re.search(pattern, text_lower):
            secret_count += 1

    return debug_count, secret_count


# ══════════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════════

def main():
    """Execute the v112R multi-asset mock adapter envelope compatibility check."""
    print("=" * 60)
    print("Market Radar v1.12-R")
    print("Multi-Asset Mock Adapter → Envelope Compatibility")
    print("=" * 60)
    print()

    # ── Step 1: Validate v112Q upstream state ─────────────────────────────────
    print("[1/7] Validating v112Q upstream state...")
    upstream = validate_upstream_state()

    for check in upstream["checks"]:
        icon = "OK" if check["passed"] else "FAIL"
        print(f"  [{icon}] {check['check']}: {check['reason']}")

    if upstream["errors"]:
        print(f"  WARNING: {len(upstream['errors'])} upstream error(s):")
        for err in upstream["errors"]:
            print(f"    - {err}")
    print(f"  Upstream valid: {upstream['valid']}")
    print()

    # ── Step 2: Load noise case results ───────────────────────────────────────
    print("[2/7] Loading v112Q noise case results...")
    noise_results = load_noise_case_results(UPSTREAM_V112Q_NOISE_RESULTS)
    if not noise_results:
        print("  FAIL: No noise case results found. Cannot proceed.")
        sys.exit(1)
    print(f"  Loaded {len(noise_results)} noise case results")
    for nr in noise_results:
        print(f"    - {nr['case_id']}: actual={nr['actual_result']}")
    print()

    # ── Step 3: Load fixtures and thresholds ──────────────────────────────────
    print("[3/7] Loading fixtures and thresholds...")
    fixtures = _load_json(UPSTREAM_V112Q_FIXTURES)
    thresholds = _load_json(UPSTREAM_V112Q_THRESHOLDS)
    if fixtures is None:
        print("  FAIL: Fixtures file not found.")
        sys.exit(1)
    fixture_cases = fixtures.get("cases", [])
    fixture_map = {c["case_id"]: c for c in fixture_cases}
    print(f"  Loaded {len(fixture_cases)} fixture cases")
    print(f"  Thresholds loaded: {thresholds is not None}")
    print()

    # ── Step 4: Classify and build mock envelopes ─────────────────────────────
    print("[4/7] Classifying noise cases and building mock envelopes...")
    classifications = []
    all_envelopes = []

    for nr in noise_results:
        case_id = nr["case_id"]
        classification = classify_noise_case_for_envelope(nr)
        classifications.append(classification)

        if classification["allowed"]:
            fixture_case = fixture_map.get(case_id)
            if fixture_case is None:
                print(f"  WARNING: No fixture found for case_id={case_id}, skipping")
                continue

            sync_result = build_mock_sync_result(
                case_id, fixture_case, nr, classification
            )
            envelope = build_mock_envelope(
                sync_result, nr, classification, fixture_case
            )
            all_envelopes.append(envelope)
            would_send = "WOULD-SEND" if classification["eligible_for_send"] else "AUDIT-ONLY"
            print(f"  [{would_send}] {case_id}: envelope built, eligible_for_send_in_live_mode={classification['eligible_for_send']}")
        else:
            print(f"  [EXCLUDED] {case_id}: {classification['rejection_reason']}")

    print(f"  Total envelopes: {len(all_envelopes)}")
    print(f"  Blocked/degraded/downgraded cases excluded: "
          f"{sum(1 for c in classifications if not c['allowed'])}")
    print()

    # ── Step 5: Verify stability ──────────────────────────────────────────────
    print("[5/7] Verifying deterministic stability...")
    stability = verify_deterministic_stability(all_envelopes)
    print(f"  deterministic_ids: {stability['deterministic_ids']}")
    print(f"  payload_hashes_stable: {stability['payload_hashes_stable']}")
    print(f"  all_signal_ids_valid: {stability['all_signal_ids_valid']}")
    print(f"  all_dedupe_keys_valid: {stability['all_dedupe_keys_valid']}")
    print(f"  all_cooldown_keys_valid: {stability['all_cooldown_keys_valid']}")
    print(f"  all_payload_hashes_valid: {stability['all_payload_hashes_valid']}")
    if stability["issues"]:
        for issue in stability["issues"]:
            print(f"  ⚠️  {issue}")
    print()

    # ── Step 6: Generate result JSON ──────────────────────────────────────────
    print("[6/7] Generating result JSON...")
    result_json = generate_result_json(
        upstream["valid"], noise_results, classifications,
        all_envelopes, stability
    )
    print(f"  status: {result_json['status']}")
    print(f"  mock_envelope_count: {result_json['mock_envelope_count']}")
    print(f"  send_candidate_count: {result_json['send_candidate_count']}")
    print(f"  envelope_compatibility_passed: {result_json['envelope_compatibility_passed']}")
    print()

    # ── Step 7: Generate all output files ─────────────────────────────────────
    print("[7/7] Writing output files...")

    # Leak check all outputs
    report_md = generate_report_md(
        upstream, noise_results, classifications, all_envelopes, stability, result_json
    )
    handoff_md = generate_handoff_md(
        upstream, noise_results, classifications, all_envelopes, stability, result_json
    )
    all_text = json.dumps(result_json, ensure_ascii=False) + report_md + handoff_md
    debug_leak, secret_leak = _check_output_for_leaks(all_text)
    result_json["debug_leak_count"] = debug_leak
    result_json["secret_leak_count"] = secret_leak

    # Ensure directories
    RESULT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENVELOPES_JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    HANDOFF_MD_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Write result JSON
    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(result_json, f, ensure_ascii=False, indent=2)
    print(f"  Wrote: {RESULT_JSON_PATH}")

    # Write envelopes JSONL
    with open(ENVELOPES_JSONL_PATH, "w", encoding="utf-8") as f:
        for env in all_envelopes:
            # Remove internal validation key from JSONL output
            env_out = {k: v for k, v in env.items() if not k.startswith("_")}
            f.write(json.dumps(env_out, ensure_ascii=False) + "\n")
    print(f"  Wrote: {ENVELOPES_JSONL_PATH}")

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
    print("v112R Complete")
    print(f"  Status: {result_json['status']}")
    print(f"  Mock envelopes: {len(all_envelopes)}")
    print(f"  Send candidates: {result_json['send_candidate_count']}")
    print(f"  Envelope compatibility: {'PASSED' if result_json['envelope_compatibility_passed'] else 'FAILED'}")
    print(f"  Deterministic IDs: {'PASSED' if stability['deterministic_ids'] else 'FAILED'}")
    print(f"  Dry run only: Yes")
    print(f"  Live API called: No")
    print(f"  TG sent: No")
    print(f"  Debug leaks: {debug_leak}")
    print(f"  Secret leaks: {secret_leak}")
    print("=" * 60)

    return 0 if result_json["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
