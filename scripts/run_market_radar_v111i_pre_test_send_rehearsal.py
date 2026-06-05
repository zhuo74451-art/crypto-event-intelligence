"""Market Radar v1.11-I — Pre-Test-Send Rehearsal (Dry Run, No TG Send)

Chains the complete pipeline from v1.11-H (SignalValueGate → CooldownGate →
REAL render_card_payload → pre_send_gate) and classifies every signal into:
  ready_to_test_send / needs_editor_review / observe_only / blocked

This is the FINAL rehearsal before v1.11-J actual test-channel delivery.
No TG send, no secrets loaded, no formal channel touched.

Pipeline layers:
  1. SignalValueGate (v1.11-D): value check — allow / observe / block
  2. CooldownGate (v1.11-F): rate-limit check — allow / suppress / upgrade_override
  3. Real render_card_payload() — actual TG card text with MarkdownV2 escaping
  4. pre_send_gate (v1.10-G): safety check — pass / block

Classification rules:
  ready_to_test_send: value=allow, cooldown=allow|upgrade_override,
    pre_send=pass, payload rendered successfully, not pure price noise,
    has OI/volume/multi-asset/upgrade support.
  needs_editor_review: technical gates pass but text quality or value
    explanation needs human review.
  observe_only: value=observe, or signal has potential but doesn't meet
    test-send criteria yet.
  blocked: value=block, cooldown=suppress, pre_send=block, or payload/format
    failure.

No TG send, no formal channel, no secrets, no paid APIs, no loop/daemon.

Usage:
    python scripts/run_market_radar_v111i_pre_test_send_rehearsal.py

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
    - Does NOT send to Telegram.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Fix Windows GBK encoding for emoji output
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
CN_TZ = timezone(timedelta(hours=8))

sys.path.insert(0, str(ROOT))

from scripts.market_radar_signal_value_gate_v111b import (
    evaluate_signal_value,
    GATE_VERSION as VALUE_GATE_VERSION,
)
from scripts.market_radar_same_asset_cooldown_gate_v111f import (
    evaluate_cooldown,
    CooldownState,
    COOLDOWN_GATE_VERSION,
    DEFAULT_COOLDOWN_WINDOW_MINUTES,
    DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA,
)
from scripts.market_radar_pre_send_gate import pre_send_gate
from scripts.market_radar_card_router import render_card_payload, classify_signal_type

PIPELINE_VERSION = "v1.11-I"


# ── CLI ─────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Market Radar v1.11-I — Pre-Test-Send Rehearsal (Dry Run)"
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "market_radar_v111i_pre_test_send_rehearsal_result.json"),
        help="Output path for rehearsal result JSON",
    )
    return parser.parse_args()


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def _now_iso() -> str:
    return datetime.now(CN_TZ).isoformat()


# ── Real payload builder ────────────────────────────────────────────────────────

def _render_payload_for_rehearsal(signal: dict) -> dict:
    """Render a real TG card payload via render_card_payload() and return
    structured payload info for the audit record.
    """
    result: dict = {
        "type": "real",
        "success": False,
        "fallback": False,
        "parse_mode": None,
        "text_preview": "",
        "text_full": "",
        "text_length": 0,
        "card_type": "unknown",
        "render_error": None,
        "warnings": [],
    }

    try:
        payload = render_card_payload(signal, prefer_markdown=True)
        text = payload.get("text", "")
        result["success"] = True
        result["fallback"] = payload.get("fallback_used", False)
        result["parse_mode"] = payload.get("parse_mode")
        result["text_full"] = text
        result["text_preview"] = text[:300] if len(text) > 300 else text
        result["text_length"] = len(text)
        result["card_type"] = payload.get("card_type", classify_signal_type(signal))
        result["warnings"] = payload.get("warnings", [])
    except Exception as exc:
        error_msg = str(exc)[:200]
        result["render_error"] = error_msg
        result["fallback"] = True
        result["warnings"].append(f"render_card_payload raised: {error_msg}")
        # Build minimal fallback
        asset = signal.get("asset", "unknown")
        trigger = signal.get("trigger_reason", f"{asset} signal")
        fallback_text = (
            f"⚠️ 卡片渲染异常\\n\\n"
            f"资产: {asset}\\n"
            f"触发: {trigger}\\n\\n"
            f"⚠️ 仅供观察，不构成交易建议。"
        )
        result["text_full"] = fallback_text
        result["text_preview"] = fallback_text[:300]
        result["text_length"] = len(fallback_text)
        result["parse_mode"] = None
        result["card_type"] = "error"

    return result


# ── Format check ────────────────────────────────────────────────────────────────

def _check_format(text: str, parse_mode: str | None) -> dict:
    """Check MarkdownV2 / HTML format safety of the card text."""
    issues: list[str] = []

    if not text or not text.strip():
        issues.append("text is empty or whitespace-only")
        return {"markdown_or_html_safe": False, "issues": issues}

    # MarkdownV2 character checks
    if parse_mode == "MarkdownV2":
        # Check for unbalanced special chars
        special_chars = ['*', '_', '~', '`', '[', ']', '(', ')']
        for char in special_chars:
            count = text.count(char)
            if count % 2 != 0:
                issues.append(f"unbalanced '{char}' ({count} occurrences) — may break MarkdownV2")

        # Check for common MarkdownV2 pitfalls
        if text.count('```') % 2 != 0:
            issues.append("unbalanced code fences (```) — may break MarkdownV2")
        if '\\' in text:
            # Check for unescaped special chars that could break
            for ch in ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']:
                # Count raw occurrences vs escaped ones
                raw_count = text.count(ch)
                escaped_count = text.count(f'\\{ch}')
                # This is a heuristic — if raw > 2*escaped, might have issues
                if raw_count > 0 and escaped_count == 0:
                    # Not necessarily a problem if the char isn't used in a MarkdownV2 position
                    pass

    # General checks
    if len(text) > 4096:
        issues.append(f"text length {len(text)} exceeds TG 4096 char limit")

    # Check for potentially problematic sequences
    if '\x00' in text:
        issues.append("null byte found in text")

    return {
        "markdown_or_html_safe": len([i for i in issues if "exceeds" in i or "null byte" in i or "empty" in i]) == 0,
        "issues": issues,
    }


# ── Content quality classifier ──────────────────────────────────────────────────

def _classify_content_quality(
    signal: dict,
    value_result: dict,
    cooldown_result: dict,
    pre_send_result: dict | None,
    payload_render: dict,
    format_check: dict,
) -> dict:
    """Classify each signal into one of four categories and assess content quality."""

    val_decision = value_result["gate_decision"]
    cool_decision = cooldown_result["decision"]
    cool_allowed = cooldown_result["allowed"]
    pre_send_allowed = pre_send_result["allowed"] if pre_send_result else None
    pre_send_blocked = pre_send_result["blocked_reason"] if pre_send_result and not pre_send_result["allowed"] else None

    # Factor analysis
    factor_hits = value_result.get("factor_hits", {})
    has_price = factor_hits.get("price_move", False)
    has_oi = factor_hits.get("oi_confirmation", False)
    has_volume = factor_hits.get("volume_confirmation", False)
    has_funding = factor_hits.get("funding_extreme", False)
    has_multi_asset = factor_hits.get("multi_asset_sync", False)

    is_price_only_noise = has_price and not has_oi and not has_volume and not has_funding
    has_oi_or_volume_support = has_oi or has_volume
    has_multi_factor_support = (
        (has_price and has_oi) or
        (has_price and has_volume) or
        (has_price and has_oi and has_volume) or
        (has_oi and has_volume and has_multi_asset)
    )
    has_upgrade_signal = cool_decision == "upgrade_override"

    # Build reasons and classification
    reasons: list[str] = []
    classification = "blocked"
    reason_text = ""

    # ── BLOCKED ──
    if val_decision == "block":
        classification = "blocked"
        reasons = value_result.get("reasons", ["value gate blocked"])
        reason_text = f"SignalValueGate blocked: score={value_result['value_score']}, tier={value_result['value_tier']}"
    elif val_decision == "allow" and not cool_allowed:
        classification = "blocked"
        reasons = [cooldown_result.get("cooldown_reason", "cooldown suppressed")]
        reason_text = f"CooldownGate suppressed: {cooldown_result.get('cooldown_reason', '')}"
    elif pre_send_result and not pre_send_allowed:
        classification = "blocked"
        reasons = [pre_send_blocked or "pre_send gate blocked"]
        reason_text = f"Pre-send gate blocked: {pre_send_blocked}"
    elif not payload_render.get("success", False):
        classification = "blocked"
        reasons = [f"Payload render failed: {payload_render.get('render_error', 'unknown')}"]
        reason_text = "Payload render failed"
    elif not format_check.get("markdown_or_html_safe", True) and any(
        i for i in format_check.get("issues", []) if "exceeds" in i or "empty" in i
    ):
        classification = "blocked"
        reasons = format_check.get("issues", [])
        reason_text = "Format check failed with critical issues"

    # ── OBSERVE ONLY ──
    elif val_decision == "observe":
        classification = "observe_only"
        reasons = value_result.get("reasons", ["observe decision"])
        reason_text = f"SignalValueGate=observe: score={value_result['value_score']}, insufficient confirmation factors"

    # ── READY or EDITOR REVIEW ──
    elif (
        val_decision == "allow"
        and cool_allowed
        and pre_send_allowed
        and payload_render.get("success", False)
    ):
        payload_text = payload_render.get("text_full", "")
        text_len = payload_render.get("text_length", 0)

        # Check if needs editor review
        needs_review_reasons: list[str] = []

        # Text too short — not informative enough
        if text_len < 80:
            needs_review_reasons.append("card text very short (< 80 chars), may lack context")

        # Price-only — needs editor to assess if worth sending
        if is_price_only_noise:
            needs_review_reasons.append("price-only signal without OI/volume confirmation")

        # Only one weak factor — borderline
        if has_price and not has_oi and not has_volume and not has_funding:
            if has_multi_asset:
                pass  # multi_asset might compensate
            else:
                needs_review_reasons.append("only price move as factor, no OI/volume/funding support")

        # Render warnings present
        if payload_render.get("warnings"):
            needs_review_reasons.append(f"render warnings: {payload_render['warnings']}")

        # Fallback used
        if payload_render.get("fallback"):
            needs_review_reasons.append("MarkdownV2→plaintext fallback was used")

        # Format issues (non-critical)
        fmt_issues = format_check.get("issues", [])
        if fmt_issues and all("exceeds" not in i and "empty" not in i and "null" not in i for i in fmt_issues):
            needs_review_reasons.append(f"format issues: {fmt_issues}")

        if needs_review_reasons:
            classification = "needs_editor_review"
            reasons = needs_review_reasons
            reason_text = "Technical gates pass, but content needs editor review: " + "; ".join(needs_review_reasons)
        else:
            classification = "ready_to_test_send"
            supporting_reasons: list[str] = []
            if has_oi_or_volume_support:
                supporting_reasons.append("OI/volume support")
            if has_multi_factor_support:
                supporting_reasons.append("multi-factor confirmation")
            if has_upgrade_signal:
                supporting_reasons.append(f"upgrade signal (score Δ ≥ {DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA})")
            if not is_price_only_noise:
                supporting_reasons.append("not price-only noise")

            reason_text = (
                f"All gates pass. Value score={value_result['value_score']} "
                f"(tier={value_result['value_tier']}), "
                f"cooldown={cool_decision}, pre_send=pass. "
                f"Supports: {', '.join(supporting_reasons) if supporting_reasons else 'standard confirmation'}."
            )

    # ── ELSE: any edge case → blocked ──
    else:
        classification = "blocked"
        reasons = ["unexpected pipeline state"]
        reason_text = "Unexpected pipeline state — blocked by default for safety"

    return {
        "classification": classification,
        "reason": reason_text,
        "is_price_only_noise": is_price_only_noise,
        "has_oi_or_volume_support": has_oi_or_volume_support,
        "has_multi_factor_support": has_multi_factor_support,
        "has_upgrade_signal": has_upgrade_signal,
    }


# ── Value gate helper ───────────────────────────────────────────────────────────

def _run_value_gate(signals: list[dict]) -> list[dict]:
    """Run all signals through SignalValueGate."""
    real_signals = [s for s in signals if not s.get("is_fixture")]
    real_down = [s for s in real_signals if (s.get("price_change_pct") or 0) < 0]
    real_up = [s for s in real_signals if (s.get("price_change_pct") or 0) > 0]
    same_dir_count = max(len(real_down), len(real_up))

    context = {
        "signals": signals,
        "same_direction_asset_count": len(signals),
        "real_same_direction_asset_count": same_dir_count,
        "batch_size": len(signals),
    }

    results: list[dict] = []
    for sig in signals:
        gate_result = evaluate_signal_value(sig, context)
        results.append({
            "asset": sig["asset"],
            "signal_type": sig["signal_type"],
            "source_type": sig["source_type"],
            "is_fixture": sig.get("is_fixture", False),
            "price_change_pct": sig.get("price_change_pct"),
            "gate_decision": gate_result["decision"],
            "value_score": gate_result["value_score"],
            "value_tier": gate_result["value_tier"],
            "factor_hits": gate_result["factor_hits"],
            "reasons": gate_result["reasons"],
            "warnings": gate_result["warnings"],
            "gate_version": gate_result["gate_version"],
        })

    return results


# ── Scenario builder — reuses v1.11-H exact scenarios ───────────────────────────

def _build_scenarios() -> list[dict]:
    """Build 6 scenarios from v1.11-H (26 signals total).

    These are the EXACT SAME scenarios as v1.11-H. We do not invent new samples.
    """
    now = datetime.now(CN_TZ)

    def _recent_ts(offset_minutes: int = 0) -> str:
        return (now - timedelta(minutes=offset_minutes)).isoformat()

    def _stale_ts() -> str:
        return (now - timedelta(hours=2)).isoformat()

    scenarios: list[dict] = []

    # ── H1: Full Happy Path with Real Cards ──
    scenarios.append({
        "scenario_id": "H1",
        "scenario_name": "Full Happy Path — Real Cards Pass All Gates",
        "objective": (
            "Verify that well-confirmed signals render real TG cards via "
            "render_card_payload(), and those real payloads pass pre_send_gate. "
            "All should be send_candidate."
        ),
        "signals": [
            {
                "asset": "BTC", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.54,
                "open_interest": 1_826_000_000, "volume": 6_345_000_000,
                "funding": None,
                "generated_at": _recent_ts(0),
                "trigger_reason": "BTC 24h 跌幅 5.54%，OI $1.83B + Vol $6.35B 三重确认",
                "minutes_offset": 0,
                "expect_final": "send_candidate",
            },
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.80,
                "open_interest": 12_900_000_000, "volume": 16_000_000_000,
                "funding": -0.015,
                "generated_at": _recent_ts(2),
                "trigger_reason": "ETH 24h 跌幅 6.80%，OI+Vol+Funding 极端四重确认",
                "minutes_offset": 2,
                "expect_final": "send_candidate",
            },
            {
                "asset": "SOL", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.24,
                "open_interest": 278_000_000, "volume": 527_000_000,
                "funding": 0.0,
                "generated_at": _recent_ts(4),
                "trigger_reason": "SOL 24h 跌幅 7.24%，OI $278M + Vol $527M 三重确认",
                "minutes_offset": 4,
                "expect_final": "send_candidate",
            },
            {
                "asset": "SUI", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.83,
                "open_interest": 28_000_000, "volume": 21_500_000,
                "funding": 0.0,
                "generated_at": _recent_ts(6),
                "trigger_reason": "SUI 24h 跌幅 5.83%，OI $28M + Vol $21.5M 三重确认",
                "minutes_offset": 6,
                "expect_final": "send_candidate",
            },
        ],
    })

    # ── H2: Value Gate Blocks ──
    scenarios.append({
        "scenario_id": "H2",
        "scenario_name": "Value Gate Blocks — Real Cards Never Reached",
        "objective": (
            "Verify that signals blocked by value gate never reach card rendering "
            "or pre_send_gate."
        ),
        "signals": [
            {
                "asset": "DOT", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -3.20,
                "open_interest": 200_000_000, "volume": None,
                "funding": None,
                "generated_at": _recent_ts(0),
                "trigger_reason": "DOT 仅跌 3.20%，未达 5% 价格阈值",
                "minutes_offset": 0,
                "expect_final": "blocked_by_value_gate",
            },
            {
                "asset": "LINK", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -4.00,
                "open_interest": None, "volume": None,
                "funding": None,
                "generated_at": _recent_ts(1),
                "trigger_reason": "LINK 仅跌 4.00%，无价格触发",
                "minutes_offset": 1,
                "expect_final": "blocked_by_value_gate",
            },
            {
                "asset": "MATIC", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -2.50,
                "open_interest": 50_000_000, "volume": 120_000_000,
                "funding": 0.0,
                "generated_at": _recent_ts(2),
                "trigger_reason": "MATIC 仅跌 2.50%，远低于阈值",
                "minutes_offset": 2,
                "expect_final": "blocked_by_value_gate",
            },
        ],
    })

    # ── H3: Cooldown Suppression ──
    scenarios.append({
        "scenario_id": "H3",
        "scenario_name": "Cooldown Suppression — Real Cards, Rate Limited",
        "objective": (
            "Verify that same-asset repeats are correctly suppressed by cooldown, "
            "even though each signal could produce a valid real card."
        ),
        "signals": [
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.55,
                "open_interest": 4_656_700, "volume": 4_942_400,
                "funding": 0.0,
                "generated_at": _recent_ts(0),
                "trigger_reason": "ARB 24h 跌幅 7.55%，第 1 次触发 (T+0min)",
                "minutes_offset": 0,
                "expect_final": "send_candidate",
            },
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.82,
                "open_interest": 4_612_000, "volume": 4_955_000,
                "funding": 0.0,
                "generated_at": _recent_ts(4),
                "trigger_reason": "ARB 24h 跌幅 7.82%，第 2 次触发 (T+4min)",
                "minutes_offset": 4,
                "expect_final": "suppressed_by_cooldown",
            },
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.90,
                "open_interest": 4_588_000, "volume": 4_961_000,
                "funding": 0.0,
                "generated_at": _recent_ts(8),
                "trigger_reason": "ARB 24h 跌幅 7.90%，第 3 次触发 (T+8min)",
                "minutes_offset": 8,
                "expect_final": "suppressed_by_cooldown",
            },
            {
                "asset": "SOL", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.80,
                "open_interest": 278_000_000, "volume": 530_000_000,
                "funding": 0.0,
                "generated_at": _recent_ts(6),
                "trigger_reason": "SOL 24h 跌幅 6.80%，不同资产无冷却",
                "minutes_offset": 6,
                "expect_final": "send_candidate",
            },
        ],
    })

    # ── H4: Pre-Send Gate Blocks ──
    scenarios.append({
        "scenario_id": "H4",
        "scenario_name": "Pre-Send Gate Blocks — Real Cards + Payload Validation",
        "objective": (
            "Verify that pre_send_gate correctly blocks invalid signals "
            "(source_trust, TTL, payload validation) even with real cards."
        ),
        "signals": [
            {
                "asset": "AVAX", "signal_type": "market_anomaly",
                "source_type": "unknown",
                "is_fixture": False,
                "price_change_pct": -6.20,
                "open_interest": 155_000_000, "volume": 220_000_000,
                "funding": None,
                "generated_at": _recent_ts(0),
                "trigger_reason": "AVAX 跌幅 6.20%，source_type=unknown → trust block",
                "minutes_offset": 0,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "source_trust",
                "_payload_mode": "real",
            },
            {
                "asset": "LTC", "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -5.80,
                "open_interest": 300_000_000, "volume": 450_000_000,
                "funding": None,
                "generated_at": _stale_ts(),
                "trigger_reason": "LTC 跌幅 5.80%，时间戳过期 (2h前) → TTL block",
                "minutes_offset": 2,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "ttl_expiry",
                "_payload_mode": "real",
            },
            {
                "asset": "NEAR", "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -5.50,
                "open_interest": 80_000_000, "volume": 120_000_000,
                "funding": 0.0,
                "generated_at": _recent_ts(4),
                "trigger_reason": "NEAR 跌幅 5.50%，载荷 text 为空 → payload validation block",
                "minutes_offset": 4,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "payload_validation",
                "_payload_override": "empty_text",
            },
            {
                "asset": "OP", "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -7.10,
                "open_interest": 60_000_000, "volume": 90_000_000,
                "funding": None,
                "generated_at": _recent_ts(6),
                "trigger_reason": "OP 跌幅 7.10%，载荷缺少 parse_mode → payload validation block",
                "minutes_offset": 6,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "payload_validation",
                "_payload_override": "no_parse_mode",
            },
        ],
    })

    # ── H5: Upgrade Override ──
    scenarios.append({
        "scenario_id": "H5",
        "scenario_name": "Upgrade Override — Score Improvement, Real Cards",
        "objective": (
            "Verify upgrade_override with real card rendering. First ETH moderate, "
            "second ETH strong. Δ>=15 triggers upgrade_override."
        ),
        "signals": [
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.50,
                "open_interest": 12_000_000_000, "volume": None, "funding": None,
                "generated_at": _recent_ts(0),
                "trigger_reason": "ETH 跌幅 5.50%，中等信号: 价格+OI (score~55)",
                "minutes_offset": 0,
                "expect_final": "send_candidate",
            },
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -8.50,
                "open_interest": 12_500_000_000, "volume": 18_200_000_000,
                "funding": -0.025,
                "generated_at": _recent_ts(5),
                "trigger_reason": "ETH 跌幅 8.50%，强信号: OI+Vol+Funding 全确认 (score~100)",
                "minutes_offset": 5,
                "expect_final": "send_candidate_upgrade",
            },
        ],
    })

    # ── H6: Full Mixed Pipeline ──
    scenarios.append({
        "scenario_id": "H6",
        "scenario_name": "Full Mixed Pipeline — Real Cards, All Outcomes",
        "objective": (
            "The definitive v1.11-I integration test. Mix of all outcome types "
            "with real card rendering."
        ),
        "signals": [
            {
                "asset": "BTC", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.54,
                "open_interest": 1_826_000_000, "volume": 6_345_000_000,
                "funding": None,
                "generated_at": _recent_ts(0),
                "trigger_reason": "BTC 24h 跌幅 5.54%，价值: allow, 冷却: allow, 安全: pass",
                "minutes_offset": 0,
                "expect_final": "send_candidate",
            },
            {
                "asset": "DOT", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -3.50,
                "open_interest": 120_000_000, "volume": None,
                "funding": None,
                "generated_at": _recent_ts(2),
                "trigger_reason": "DOT 仅跌 3.50%，价值: block, 管道终止于此",
                "minutes_offset": 2,
                "expect_final": "blocked_by_value_gate",
            },
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.55,
                "open_interest": 4_656_700, "volume": 4_942_400,
                "funding": 0.0,
                "generated_at": _recent_ts(4),
                "trigger_reason": "ARB 24h 跌幅 7.55%，价值: allow, 冷却: allow (首次), 安全: pass",
                "minutes_offset": 4,
                "expect_final": "send_candidate",
            },
            {
                "asset": "LINK", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.20,
                "open_interest": None, "volume": None,
                "funding": None,
                "generated_at": _recent_ts(6),
                "trigger_reason": "LINK 跌幅 7.20%，价值: observe (仅价格触发, 无确认因子)",
                "minutes_offset": 6,
                "expect_final": "observe",
            },
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.70,
                "open_interest": 4_590_000, "volume": 4_960_000,
                "funding": 0.0,
                "generated_at": _recent_ts(8),
                "trigger_reason": "ARB 24h 跌幅 7.70%，价值: allow, 冷却: suppress (T+8, Δ<15)",
                "minutes_offset": 8,
                "expect_final": "suppressed_by_cooldown",
            },
            {
                "asset": "SUI", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.83,
                "open_interest": 28_000_000, "volume": 21_500_000,
                "funding": 0.0,
                "generated_at": _recent_ts(10),
                "trigger_reason": "SUI 24h 跌幅 5.83%，价值: allow, 冷却: allow (首次), 安全: pass",
                "minutes_offset": 10,
                "expect_final": "send_candidate",
            },
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "unknown",
                "is_fixture": False,
                "price_change_pct": -6.50,
                "open_interest": 12_800_000_000, "volume": 15_800_000_000,
                "funding": None,
                "generated_at": _recent_ts(12),
                "trigger_reason": "ETH 跌幅 6.50%，价值: allow, 冷却: allow (首次), 安全: BLOCK (unknown source)",
                "minutes_offset": 12,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "source_trust",
                "_payload_mode": "real",
            },
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -8.50,
                "open_interest": 5_200_000, "volume": 6_100_000,
                "funding": -0.018,
                "generated_at": _recent_ts(14),
                "trigger_reason": "ARB 跌幅 8.50%，价值: allow, 冷却: upgrade_override (score↑), 安全: pass",
                "minutes_offset": 14,
                "expect_final": "send_candidate_upgrade",
            },
            {
                "asset": "AVAX", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.20,
                "open_interest": None, "volume": None,
                "funding": None,
                "generated_at": _recent_ts(0),
                "trigger_reason": "AVAX 跌幅 6.20%，价值: observe (仅价格触发, 无确认)",
                "minutes_offset": 16,
                "expect_final": "observe",
            },
        ],
    })

    return scenarios


# ── Audit record builder ────────────────────────────────────────────────────────

def _build_audit_record(
    signal: dict,
    signal_index: int,
    scenario_id: str,
    value_result: dict,
    cooldown_result: dict,
    pre_send_result: dict | None,
    payload_render: dict,
    format_check: dict,
    content_quality: dict,
) -> dict:
    """Build the complete audit record for a single signal per the v1.11-I spec."""

    val_decision = value_result["gate_decision"]
    cool_decision = cooldown_result["decision"]
    cool_allowed = cooldown_result["allowed"]

    # Value gate section
    value_gate = {
        "decision": val_decision,
        "score": value_result["value_score"],
        "reasons": value_result["reasons"],
    }

    # Cooldown gate section
    cooldown_gate = {
        "decision": cool_decision,
        "reason": cooldown_result.get("cooldown_reason", ""),
    }

    # Pre-send gate section
    if pre_send_result:
        pre_send_gate_section = {
            "decision": "pass" if pre_send_result["allowed"] else "block",
            "reasons": (
                [pre_send_result["blocked_reason"]]
                if not pre_send_result["allowed"] and pre_send_result.get("blocked_reason")
                else []
            ),
        }
    else:
        pre_send_gate_section = {
            "decision": "not_reached",
            "reasons": [],
        }

    # Build signal ID
    signal_id = f"{scenario_id}-{signal_index:02d}"

    record = {
        "scenario_id": scenario_id,
        "signal_id": signal_id,
        "asset": signal["asset"],
        "value_gate": value_gate,
        "cooldown_gate": cooldown_gate,
        "pre_send_gate": pre_send_gate_section,
        "payload_render": {
            "type": payload_render["type"],
            "success": payload_render["success"],
            "fallback": payload_render["fallback"],
            "parse_mode": payload_render["parse_mode"],
            "text_preview": payload_render["text_preview"],
            "text_length": payload_render["text_length"],
        },
        "format_check": format_check,
        "content_quality": content_quality,
    }

    return record


# ── Pipeline execution ─────────────────────────────────────────────────────────

def _run_pipeline(signals: list[dict], scenario_id: str) -> tuple[list[dict], dict]:
    """Run the full pipeline and produce v1.11-I audit records."""

    # Step 1: SignalValueGate
    value_results = _run_value_gate(signals)

    # Step 2: CooldownGate + Payload + Pre-send
    base_time = datetime.now(CN_TZ)
    min_offset = min(s.get("minutes_offset", 0) for s in signals)
    base_time = base_time - timedelta(minutes=min_offset)

    cooldown_state = CooldownState()
    audit_records: list[dict] = []

    ready = needs_review = observe_only = blocked = 0

    for i, (sig, vr) in enumerate(zip(signals, value_results)):
        offset = sig.get("minutes_offset", i)
        signal_time = (base_time + timedelta(minutes=offset)).isoformat()

        # ── Cooldown Gate ──
        cr = evaluate_cooldown(
            signal=sig,
            signal_value_result=vr,
            cooldown_state=cooldown_state,
            current_time=signal_time,
        )
        cooldown_state.apply(cr["cooldown_state"])

        val_decision = vr["gate_decision"]
        cool_decision = cr["decision"]
        cool_allowed = cr["allowed"]

        should_check_pre_send = (
            val_decision in ("allow", "observe")
            and cool_allowed
        )

        pre_send_result = None
        payload_render: dict = {
            "type": "real",
            "success": False,
            "fallback": False,
            "parse_mode": None,
            "text_preview": "",
            "text_full": "",
            "text_length": 0,
            "card_type": "unknown",
            "render_error": None,
            "warnings": [],
        }

        if should_check_pre_send:
            # ── Build payload ──
            payload_override = sig.get("_payload_override")

            if payload_override == "empty_text":
                payload = {"text": "", "parse_mode": "Markdown"}
                payload_render = {
                    "type": "mock",
                    "success": True,
                    "fallback": False,
                    "parse_mode": "Markdown",
                    "text_preview": "",
                    "text_full": "",
                    "text_length": 0,
                    "card_type": "mock",
                    "render_error": None,
                    "warnings": ["intentional empty_text for payload_validation test"],
                }
            elif payload_override == "no_parse_mode":
                payload_text = f"Signal for {sig.get('asset', 'unknown')}"
                payload = {"text": payload_text}
                payload_render = {
                    "type": "mock",
                    "success": True,
                    "fallback": False,
                    "parse_mode": None,
                    "text_preview": payload_text,
                    "text_full": payload_text,
                    "text_length": len(payload_text),
                    "card_type": "mock",
                    "render_error": None,
                    "warnings": ["intentional missing parse_mode for payload_validation test"],
                }
            else:
                # REAL card rendering
                payload_render = _render_payload_for_rehearsal(sig)
                if payload_render["success"]:
                    payload = {
                        "text": payload_render["text_full"],
                        "parse_mode": payload_render["parse_mode"] or "MarkdownV2",
                    }
                else:
                    payload = {
                        "text": payload_render["text_full"],
                        "parse_mode": None,
                    }

            # ── Run pre_send_gate ──
            pre_send_result = pre_send_gate(
                signal=sig,
                payload=payload,
                target_env="test",
            )

        # ── Format check ──
        format_check = _check_format(
            payload_render.get("text_full", ""),
            payload_render.get("parse_mode"),
        )

        # ── Content quality classification ──
        content_quality = _classify_content_quality(
            sig, vr, cr, pre_send_result, payload_render, format_check,
        )

        # ── Build audit record ──
        record = _build_audit_record(
            sig, i, scenario_id, vr, cr, pre_send_result,
            payload_render, format_check, content_quality,
        )
        audit_records.append(record)

        # Count classification
        cls = content_quality["classification"]
        if cls == "ready_to_test_send":
            ready += 1
        elif cls == "needs_editor_review":
            needs_review += 1
        elif cls == "observe_only":
            observe_only += 1
        else:
            blocked += 1

    stats = {
        "scenario_id": scenario_id,
        "total_signals": len(signals),
        "ready_to_test_send": ready,
        "needs_editor_review": needs_review,
        "observe_only": observe_only,
        "blocked": blocked,
    }

    return audit_records, stats


# ── Top candidate selector ──────────────────────────────────────────────────────

def _select_top_candidates(all_records: list[dict]) -> list[dict]:
    """Select the top 1-3 ready_to_test_send candidates for recommended delivery."""
    ready = [r for r in all_records if r["content_quality"]["classification"] == "ready_to_test_send"]

    # Score each ready candidate
    scored: list[tuple[int, dict]] = []
    for r in ready:
        score = 0
        vg = r["value_gate"]
        cq = r["content_quality"]

        # Higher value score = better
        score += vg["score"]

        # Multi-factor support
        if cq.get("has_multi_factor_support"):
            score += 30
        if cq.get("has_oi_or_volume_support"):
            score += 20
        if cq.get("has_upgrade_signal"):
            score += 15

        # Not price-only noise
        if not cq.get("is_price_only_noise"):
            score += 10

        # Payload text length is reasonable
        text_len = r["payload_render"].get("text_length", 0)
        if 100 <= text_len <= 1000:
            score += 5

        # No format issues
        if r["format_check"].get("markdown_or_html_safe") and not r["format_check"].get("issues"):
            score += 5

        scored.append((score, r))

    # Sort by score descending, take top 3
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:3]

    # Build result with recommendation reasons
    result: list[dict] = []
    tier_map = {0: "🥇", 1: "🥈", 2: "🥉"}
    for idx, (score, record) in enumerate(top):
        asset = record["asset"]
        reasons: list[str] = []
        if record["content_quality"].get("has_multi_factor_support"):
            reasons.append("multi-factor confirmation (price + OI + volume)")
        if record["content_quality"].get("has_upgrade_signal"):
            reasons.append("upgrade signal detected")
        if record["content_quality"].get("has_oi_or_volume_support"):
            reasons.append("OI/volume backed")
        if not record["content_quality"].get("is_price_only_noise"):
            reasons.append("not price-only noise")
        text_len = record["payload_render"].get("text_length", 0)
        reasons.append(f"card text {text_len} chars (TG-safe)")

        result.append({
            "rank": idx + 1,
            "tier_icon": tier_map.get(idx, ""),
            "signal_id": record["signal_id"],
            "asset": asset,
            "value_score": record["value_gate"]["score"],
            "composite_score": score,
            "recommendation_reasons": reasons,
            "payload_preview": record["payload_render"]["text_preview"],
            "full_record": record,
        })

    return result


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    print(f"Market Radar {PIPELINE_VERSION} — Pre-Test-Send Rehearsal (Dry Run)")
    print(f"Started: {china_stamp()}")
    print(f"Pipeline version: {PIPELINE_VERSION}")
    print(f"  Layer 1: SignalValueGate ({VALUE_GATE_VERSION})")
    print(f"  Layer 2: CooldownGate ({COOLDOWN_GATE_VERSION})")
    print(f"  Layer 3: REAL render_card_payload (card_router)")
    print(f"  Layer 4: pre_send_gate")
    print()
    print(f"MODE: DRY-RUN ONLY — NO TG SEND")
    print(f"SECRETS: NOT LOADED")
    print(f"FORMAL CHANNEL: NOT TOUCHED")
    print()

    scenarios = _build_scenarios()

    all_records: list[dict] = []
    scenario_results: list[dict] = []
    total_signals = 0
    total_ready = 0
    total_needs_review = 0
    total_observe = 0
    total_blocked = 0
    total_payload_real = 0
    total_payload_mock = 0
    total_payload_success = 0
    total_payload_fallback = 0
    total_format_safe = 0

    for scenario in scenarios:
        sid = scenario["scenario_id"]
        sname = scenario["scenario_name"]
        signals = scenario["signals"]

        print(f"{'─' * 70}")
        print(f"Batch {sid}: {sname} ({len(signals)} signals)")
        print()

        records, stats = _run_pipeline(signals, sid)

        # Print per-signal results
        for r in records:
            vg = r["value_gate"]
            cg = r["cooldown_gate"]
            psg = r["pre_send_gate"]
            cq = r["content_quality"]
            pr = r["payload_render"]

            cls_icon = {
                "ready_to_test_send": "✅",
                "needs_editor_review": "📝",
                "observe_only": "👁️",
                "blocked": "❌",
            }.get(cq["classification"], "?")

            print(f"  {cls_icon} [{r['signal_id']}] {r['asset']:6s} | "
                  f"V:{vg['decision']:7s}({vg['score']:3d}) | "
                  f"C:{cg['decision']:20s} | "
                  f"P:{psg['decision']:12s} | "
                  f"payload={'OK' if pr['success'] else 'FAIL'} | "
                  f"→ {cq['classification']}")

        # Batch summary
        print()
        print(f"  Batch {sid} classification:")
        print(f"    ready_to_test_send:   {stats['ready_to_test_send']}")
        print(f"    needs_editor_review:  {stats['needs_editor_review']}")
        print(f"    observe_only:         {stats['observe_only']}")
        print(f"    blocked:              {stats['blocked']}")
        print()

        all_records.extend(records)
        scenario_results.append({
            "scenario_id": sid,
            "scenario_name": sname,
            "batch_size": len(signals),
            "classification_stats": stats,
            "records": records,
        })

        total_signals += len(signals)
        total_ready += stats["ready_to_test_send"]
        total_needs_review += stats["needs_editor_review"]
        total_observe += stats["observe_only"]
        total_blocked += stats["blocked"]

        for r in records:
            pr = r["payload_render"]
            if pr["type"] == "real":
                total_payload_real += 1
            else:
                total_payload_mock += 1
            if pr["success"]:
                total_payload_success += 1
            if pr.get("fallback"):
                total_payload_fallback += 1
            if r["format_check"].get("markdown_or_html_safe"):
                total_format_safe += 1

    # ── Select top candidates ──
    top_candidates = _select_top_candidates(all_records)

    # ── Build result JSON ──
    summary = {
        "ready_to_test_send": total_ready,
        "needs_editor_review": total_needs_review,
        "observe_only": total_observe,
        "blocked": total_blocked,
    }

    result = {
        "version": PIPELINE_VERSION,
        "mode": "dry_run_pre_test_send_rehearsal",
        "tg_sent": False,
        "secrets_loaded": False,
        "official_channel_touched": False,
        "total_signals": total_signals,
        "summary": summary,
        "top_ready_candidates": [
            {
                "rank": c["rank"],
                "signal_id": c["signal_id"],
                "asset": c["asset"],
                "value_score": c["value_score"],
                "composite_score": c["composite_score"],
                "recommendation_reasons": c["recommendation_reasons"],
                "payload_preview": c["payload_preview"],
            }
            for c in top_candidates
        ],
        "all_records": all_records,
    }

    # ── Write JSON ──
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    # ── Print summary ──
    print(f"{'=' * 70}")
    print(f"v1.11-I Pre-Test-Send Rehearsal — Final Summary")
    print(f"{'=' * 70}")
    print(f"  Total signals:          {total_signals}")
    print(f"  ───────────────────────────────────────")
    print(f"  ✅ ready_to_test_send:  {total_ready} ({round(total_ready/total_signals*100, 1)}%)")
    print(f"  📝 needs_editor_review: {total_needs_review} ({round(total_needs_review/total_signals*100, 1)}%)")
    print(f"  👁️  observe_only:       {total_observe} ({round(total_observe/total_signals*100, 1)}%)")
    print(f"  ❌ blocked:             {total_blocked} ({round(total_blocked/total_signals*100, 1)}%)")
    print(f"  ───────────────────────────────────────")
    print(f"  Payload real:           {total_payload_real}")
    print(f"  Payload mock:           {total_payload_mock}")
    print(f"  Payload success:        {total_payload_success}")
    print(f"  Payload fallback:       {total_payload_fallback}")
    print(f"  Format safe:            {total_format_safe}/{total_signals}")
    print()
    if top_candidates:
        print(f"  Top recommended test-send candidates (max 3):")
        for c in top_candidates:
            print(f"    {c['rank']}. [{c['signal_id']}] {c['asset']} (score={c['composite_score']})")
            for reason in c["recommendation_reasons"]:
                print(f"       └ {reason}")
    else:
        print(f"  No ready_to_test_send candidates. Cannot recommend test-channel delivery.")
    print()
    print(f"  TG send:                NONE")
    print(f"  Secrets loaded:         NONE")
    print(f"  Formal channel:         NOT TOUCHED")
    print(f"  Paid APIs:              NONE")
    print(f"  Loop/daemon:            NONE")
    print(f"  Files deleted:          NONE")
    print()
    print(f"  Report:                 {output_path}")
    print(f"{'=' * 70}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
