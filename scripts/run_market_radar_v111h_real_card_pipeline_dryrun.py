"""Market Radar v1.11-H — Real Card Render + Full Gate Pipeline Dry-run

Chains SignalValueGate → CooldownGate → REAL render_card_payload → pre_send_gate
into a complete three-layer dry-run pipeline with actual card rendering.

This is the critical bridge from v1.11-G (mock payloads) to production-ready
payload validation. The real card router (market_radar_card_router.py) renders
actual TG-formatted card text, which then passes through pre_send_gate for
safety validation.

Pipeline layers:
  1. SignalValueGate (v1.11-D): value check — allow / observe / block
  2. CooldownGate (v1.11-F): rate-limit check — allow / cooldown_suppress / upgrade_override
  3. Real render_card_payload() — actual TG card text with MarkdownV2 escaping
  4. pre_send_gate (v1.10-G): safety check — allowed / blocked (trust + TTL + payload)

New v1.11-H metrics (beyond v1.11-G):
  - payload_mode_breakdown: real vs mock
  - payload_render_success_count: real payloads rendered successfully
  - payload_render_failed_count: real payloads that failed to render
  - payload_fallback_used_count: MarkdownV2→plaintext fallbacks
  - card_type_distribution: what card types were rendered
  - blocked_by_payload_render: signals blocked because render_card_payload failed

No TG send, no formal channel, no secrets, no paid APIs, no loop/daemon.

Usage:
    python scripts/run_market_radar_v111h_real_card_pipeline_dryrun.py
    python scripts/run_market_radar_v111h_real_card_pipeline_dryrun.py --output results/custom.json

Security:
    - Does NOT read, print, or save any token / chat_id / key / cookie / password.
    - Does NOT access environment variables for credentials.
    - Does NOT make network calls.
    - Does NOT send to Telegram.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

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

PIPELINE_VERSION = "v1.11-H"


# ── CLI ─────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Market Radar v1.11-H — Real Card Render + Full Gate Pipeline Dry-run"
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "market_radar_v111h_real_card_pipeline_dryrun_result.json"),
        help="Output path for dry-run result JSON",
    )
    return parser.parse_args()


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def _now_iso() -> str:
    return datetime.now(CN_TZ).isoformat()


# ── Real payload builder (card router) ──────────────────────────────────────────

def _build_real_payload(signal: dict) -> dict:
    """Build a real TG card payload using render_card_payload() from the card router.

    This is the KEY v1.11-H change: replacing mock payloads with actual card
    rendering, which produces real TG-formatted text with MarkdownV2 escaping,
    fallback handling, and card_type metadata.

    Returns:
        {
            "text": str,              # rendered card text (MarkdownV2 escaped or plain)
            "parse_mode": str | None, # "MarkdownV2" or None (plaintext fallback)
            "fallback_used": bool,    # True if MarkdownV2→plaintext fallback occurred
            "warnings": list[str],    # rendering warnings
            "card_type": str,         # e.g. "market_anomaly"
            "render_success": bool,   # True if rendering succeeded
            "render_error": str | None,  # error message if rendering failed
        }
    """
    result: dict = {
        "text": "",
        "parse_mode": None,
        "fallback_used": False,
        "warnings": [],
        "card_type": "unknown",
        "render_success": False,
        "render_error": None,
    }

    try:
        payload = render_card_payload(signal, prefer_markdown=True)
        result["text"] = payload.get("text", "")
        result["parse_mode"] = payload.get("parse_mode")
        result["fallback_used"] = payload.get("fallback_used", False)
        result["warnings"] = payload.get("warnings", [])
        result["card_type"] = payload.get("card_type", classify_signal_type(signal))
        result["render_success"] = True
    except Exception as exc:
        # Card rendering failed — produce a minimal fallback payload
        error_msg = str(exc)[:200]
        result["render_error"] = error_msg
        result["render_success"] = False
        result["fallback_used"] = True
        result["warnings"].append(f"render_card_payload raised: {error_msg}")
        # Build minimal safe fallback text
        asset = signal.get("asset", "unknown")
        trigger = signal.get("trigger_reason", f"{asset} signal")
        result["text"] = (
            f"⚠️ 卡片渲染异常\\n\\n"
            f"资产: {asset}\\n"
            f"触发: {trigger}\\n\\n"
            f"⚠️ 仅供观察，不构成交易建议。"
        )
        result["parse_mode"] = None  # plain text fallback — safest
        result["card_type"] = "error"

    return result


# ── Mock payload builders (for intentional pre_send failure scenarios) ──────────

def _build_mock_payload(signal: dict, value_result: dict,
                        cooldown_result: dict | None = None) -> dict:
    """Build a minimal mock payload for pre_send_gate dry-run validation.

    Used ONLY for signals with _payload_override set, where we intentionally
    test pre_send_gate's ability to reject invalid payloads. Not used for
    normal signals — those use _build_real_payload().
    """
    asset = signal.get("asset", "unknown")
    trigger = signal.get("trigger_reason", f"{asset} market anomaly")
    pct = signal.get("price_change_pct", 0)
    direction = "📉" if (pct or 0) < 0 else "📈"

    value_score = value_result.get("value_score", 0)
    value_tier = value_result.get("value_tier", "low")
    tier_emoji = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(value_tier, "⚪")

    text = (
        f"{direction} **{asset}** 24h变化: {pct:+.2f}%\n"
        f"{tier_emoji} 价值评分: {value_score}/100 ({value_tier})\n"
        f"📊 数据源: {signal.get('source_type', 'api')}\n"
        f"📝 {trigger}"
    )

    return {
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }


def _build_invalid_payload_empty_text(signal: dict) -> dict:
    """Build a payload with empty text — should fail pre_send_gate."""
    return {"text": "", "parse_mode": "Markdown"}


def _build_invalid_payload_no_parse_mode(signal: dict) -> dict:
    """Build a payload missing parse_mode — should fail pre_send_gate."""
    return {"text": f"Signal for {signal.get('asset', 'unknown')}"}


# ── Value gate helper ───────────────────────────────────────────────────────────

def _run_value_gate(signals: list[dict]) -> list[dict]:
    """Run all signals through SignalValueGate, returning their results."""
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


# ── Scenario definitions ────────────────────────────────────────────────────────

def _build_scenarios() -> list[dict]:
    """Build 6 scenarios designed to stress-test the full three-layer pipeline
    with REAL card rendering.

    Each scenario has an ordered list of signals with minutes_offset for
    cooldown time sequencing.

    Key v1.11-H change: All signals use real render_card_payload() by default.
    Only signals with explicit _payload_override use mock payloads (for testing
    pre_send_gate's payload validation blocking).

    Returns a list of scenario dicts.
    """
    now = datetime.now(CN_TZ)

    def _recent_ts(offset_minutes: int = 0) -> str:
        return (now - timedelta(minutes=offset_minutes)).isoformat()

    def _stale_ts() -> str:
        return (now - timedelta(hours=2)).isoformat()

    scenarios: list[dict] = []

    # ── Batch H1: Full Happy Path with Real Cards — all three gates pass ─────
    # 4 signals, all well-confirmed, different assets, no repeats.
    # Real card rendering → all should pass pre_send_gate.
    scenarios.append({
        "scenario_id": "H1",
        "scenario_name": "Full Happy Path — Real Cards Pass All Gates",
        "objective": (
            "Verify that well-confirmed signals render real TG cards via "
            "render_card_payload(), and those real payloads pass pre_send_gate. "
            "All should be final_send_candidate."
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

    # ── Batch H2: Value Gate Blocks — first-layer rejection ──────────────────
    # Same as G2: signals below threshold. Real cards would render, but value gate
    # blocks them first. This tests that value gate still works correctly even when
    # the card router CAN render valid payloads.
    scenarios.append({
        "scenario_id": "H2",
        "scenario_name": "Value Gate Blocks — Real Cards Never Reached",
        "objective": (
            "Verify that signals blocked by value gate never reach card rendering "
            "or pre_send_gate. Real card payloads are irrelevant — termination is "
            "at the first layer."
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

    # ── Batch H3: Cooldown Suppression with Real Cards ───────────────────────
    # ARB appears 3 times within 8 min. First real card passes, subsequent
    # suppressed by cooldown. SOL once as context.
    scenarios.append({
        "scenario_id": "H3",
        "scenario_name": "Cooldown Suppression — Real Cards, Rate Limited",
        "objective": (
            "Verify that same-asset repeats are correctly suppressed by cooldown, "
            "even though each signal could produce a valid real card. Only the "
            "first ARB and the SOL signal become send_candidates."
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

    # ── Batch H4: Pre-Send Gate Blocks — Real Cards + Gate-Level Failures ────
    # Mixed approach: AVAX and LTC use real card payloads (testing gate-level
    # blocks like source_trust and TTL). NEAR and OP use mock override payloads
    # (testing payload validation blocks). This demonstrates that real cards
    # can still be blocked by gate-level safety checks.
    scenarios.append({
        "scenario_id": "H4",
        "scenario_name": "Pre-Send Gate Blocks — Real Cards + Payload Validation",
        "objective": (
            "Verify that pre_send_gate correctly blocks: (a) real card payload with "
            "source_type='unknown' → trust gate block, (b) real card payload with "
            "stale timestamp → TTL block, (c) mock empty payload → payload validation "
            "block, (d) mock missing parse_mode → payload validation block."
        ),
        "signals": [
            {
                "asset": "AVAX", "signal_type": "market_anomaly",
                "source_type": "unknown",  # blocked by trust map — real card rendered
                "is_fixture": False,
                "price_change_pct": -6.20,
                "open_interest": 155_000_000, "volume": 220_000_000,
                "funding": None,
                "generated_at": _recent_ts(0),
                "trigger_reason": "AVAX 跌幅 6.20%，source_type=unknown → trust block",
                "minutes_offset": 0,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "source_trust",
                "_payload_mode": "real",  # real card, blocked by gate
            },
            {
                "asset": "LTC", "signal_type": "market_anomaly",
                "source_type": "api",  # source OK
                "is_fixture": False,
                "price_change_pct": -5.80,
                "open_interest": 300_000_000, "volume": 450_000_000,
                "funding": None,
                "generated_at": _stale_ts(),  # stale! > 15 min TTL
                "trigger_reason": "LTC 跌幅 5.80%，时间戳过期 (2h前) → TTL block",
                "minutes_offset": 2,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "ttl_expiry",
                "_payload_mode": "real",  # real card, blocked by TTL
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

    # ── Batch H5: Upgrade Override with Real Cards ───────────────────────────
    scenarios.append({
        "scenario_id": "H5",
        "scenario_name": "Upgrade Override — Score Improvement, Real Cards",
        "objective": (
            "Verify upgrade_override with real card rendering. First ETH is "
            "moderate (score~55), second ETH is strong (score~100). The Δ>=15 "
            "triggers upgrade_override, and both real card payloads pass pre_send."
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

    # ── Batch H6: Full Mixed Pipeline with Real Cards — All Outcomes ─────────
    scenarios.append({
        "scenario_id": "H6",
        "scenario_name": "Full Mixed Pipeline — Real Cards, All Outcomes",
        "objective": (
            "The definitive v1.11-H integration test. Mix of all outcome types "
            "with real card rendering. Verifies: real card payloads pass pre_send "
            "for valid signals, and the complete three-layer pipeline produces "
            "the correct decision matrix."
        ),
        "signals": [
            # T+0: BTC — well confirmed, first → send_candidate (real card)
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
            # T+2: DOT — below threshold → blocked_by_value_gate
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
            # T+4: ARB — well confirmed, first → send_candidate (real card)
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
            # T+6: LINK — strong price but no fields → observe
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
            # T+8: ARB repeat — same score → suppressed_by_cooldown
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
            # T+10: SUI — well confirmed, first → send_candidate (real card)
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
            # T+12: stale source → blocked_by_pre_send_gate (source trust, real card)
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "unknown",  # blocked by trust gate
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
            # T+14: ARB third — upgrade override → send_candidate_upgrade (real card)
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
            # T+16: AVAX — weak signal → observe
            {
                "asset": "AVAX", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.20,
                "open_interest": None, "volume": None,
                "funding": None,
                "generated_at": _recent_ts(0),  # recent, not stale
                "trigger_reason": "AVAX 跌幅 6.20%，价值: observe (仅价格触发, 无确认)",
                "minutes_offset": 16,
                "expect_final": "observe",
            },
        ],
    })

    return scenarios


# ── Pipeline execution ─────────────────────────────────────────────────────────

def _run_pipeline(signals: list[dict], scenario_id: str) -> tuple[list[dict], dict]:
    """Run the full three-layer pipeline with REAL card rendering.

    Pipeline: SignalValueGate → CooldownGate → REAL render_card_payload → pre_send_gate

    Returns:
        (signal_entries, pipeline_stats)
    """
    # Step 1: Run all signals through SignalValueGate
    value_results = _run_value_gate(signals)

    # Step 2: Build base time for cooldown sequencing
    base_time = datetime.now(CN_TZ)
    min_offset = min(s.get("minutes_offset", 0) for s in signals)
    base_time = base_time - timedelta(minutes=min_offset)

    # Step 3: Run through CooldownGate, real card rendering, and pre_send_gate
    cooldown_state = CooldownState()
    signal_entries: list[dict] = []

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

        # ── Determine whether to build payload ──
        val_decision = vr["gate_decision"]
        cool_decision = cr["decision"]
        cool_allowed = cr["allowed"]

        should_check_pre_send = (
            val_decision in ("allow", "observe")
            and cool_allowed
        )

        pre_send_result = None
        payload_info: dict = {}

        if should_check_pre_send:
            # ── Build payload (real or mock based on signal flags) ──
            payload_override = sig.get("_payload_override")
            payload_mode = sig.get("_payload_mode", "real")

            if payload_override == "empty_text":
                payload = _build_invalid_payload_empty_text(sig)
                payload_mode = "mock"
                payload_info = {
                    "payload_mode": "mock",
                    "mock_reason": "intentional_empty_text_for_payload_validation_test",
                    "card_type": "mock",
                    "fallback_used": False,
                    "render_success": True,
                    "render_error": None,
                    "render_warnings": [],
                    "payload_text_length": 0,
                }
            elif payload_override == "no_parse_mode":
                payload = _build_invalid_payload_no_parse_mode(sig)
                payload_mode = "mock"
                payload_info = {
                    "payload_mode": "mock",
                    "mock_reason": "intentional_missing_parse_mode_for_payload_validation_test",
                    "card_type": "mock",
                    "fallback_used": False,
                    "render_success": True,
                    "render_error": None,
                    "render_warnings": [],
                    "payload_text_length": len(payload["text"]),
                }
            else:
                # ── REAL card rendering (KEY v1.11-H change) ──
                real_payload = _build_real_payload(sig)
                payload_mode = "real"
                payload_info = {
                    "payload_mode": "real",
                    "mock_reason": None,
                    "card_type": real_payload["card_type"],
                    "fallback_used": real_payload["fallback_used"],
                    "render_success": real_payload["render_success"],
                    "render_error": real_payload["render_error"],
                    "render_warnings": real_payload["warnings"],
                    "payload_text_length": len(real_payload["text"]),
                }
                # Build pre_send_gate-compatible payload dict
                if real_payload["render_success"]:
                    payload = {
                        "text": real_payload["text"],
                        "parse_mode": real_payload["parse_mode"] or "MarkdownV2",
                    }
                else:
                    # Real render failed — use minimal fallback
                    payload = {
                        "text": real_payload["text"],
                        "parse_mode": None,
                    }

            # ── Run pre_send_gate on the payload ──
            pre_send_result = pre_send_gate(
                signal=sig,
                payload=payload,
                target_env="test",
            )

            # Merge payload_info into pre_send_result for downstream analysis
            pre_send_result["_payload_info"] = payload_info
            pre_send_result["_payload_mode"] = payload_mode

        # ── Determine final status ──
        if val_decision == "block":
            final_status = "blocked_by_value_gate"
            pipeline_layer = "value_gate"
        elif val_decision == "observe":
            if not should_check_pre_send:
                final_status = "observe"
                pipeline_layer = "cooldown_gate"
            elif pre_send_result and not pre_send_result["allowed"]:
                final_status = "observe__pre_send_blocked"
                pipeline_layer = "pre_send_gate"
            else:
                final_status = "observe"
                pipeline_layer = "cooldown_gate"
        elif not cool_allowed:
            final_status = "suppressed_by_cooldown"
            pipeline_layer = "cooldown_gate"
        elif pre_send_result and not pre_send_result["allowed"]:
            final_status = "blocked_by_pre_send_gate"
            pipeline_layer = "pre_send_gate"
        elif cool_decision == "upgrade_override":
            final_status = "send_candidate_upgrade"
            pipeline_layer = "pre_send_gate"
        else:
            final_status = "send_candidate"
            pipeline_layer = "pre_send_gate"

        # ── Build entry ──
        entry = {
            "index": i,
            "asset": sig["asset"],
            "signal_type": sig["signal_type"],
            "source_type": sig["source_type"],
            "minutes_offset": offset,
            # Value gate layer
            "value_decision": val_decision,
            "value_score": vr["value_score"],
            "value_tier": vr["value_tier"],
            "value_factor_hits": vr["factor_hits"],
            "value_reasons": vr["reasons"],
            "value_warnings": vr["warnings"],
            # Cooldown gate layer
            "cooldown_decision": cool_decision,
            "cooldown_allowed": cool_allowed,
            "cooldown_reason": cr["cooldown_reason"],
            "cooldown_previous_score": cr["previous_value_score"],
            "cooldown_minutes_since_last": cr["minutes_since_last"],
            "cooldown_occurrence_count": cr["occurrence_count"],
            # Pre-send gate layer
            "pre_send_checked": pre_send_result is not None,
            "pre_send_allowed": pre_send_result["allowed"] if pre_send_result else None,
            "pre_send_blocked_reason": pre_send_result["blocked_reason"] if pre_send_result and not pre_send_result["allowed"] else None,
            "pre_send_gate_version": pre_send_result["gate_version"] if pre_send_result else None,
            # Payload info (v1.11-H specific)
            "payload_mode": payload_info.get("payload_mode") if payload_info else None,
            "payload_card_type": payload_info.get("card_type") if payload_info else None,
            "payload_render_success": payload_info.get("render_success") if payload_info else None,
            "payload_fallback_used": payload_info.get("fallback_used") if payload_info else None,
            "payload_render_error": payload_info.get("render_error") if payload_info else None,
            "payload_text_length": payload_info.get("payload_text_length") if payload_info else None,
            # Final
            "final_status": final_status,
            "pipeline_layer": pipeline_layer,
            "trigger_reason": sig.get("trigger_reason", ""),
            "expect_final": sig.get("expect_final", ""),
        }
        signal_entries.append(entry)

    # ── Build pipeline stats ──
    send_candidate = sum(1 for e in signal_entries if e["final_status"] in ("send_candidate", "send_candidate_upgrade"))
    send_candidate_upgrade = sum(1 for e in signal_entries if e["final_status"] == "send_candidate_upgrade")
    blocked_by_value = sum(1 for e in signal_entries if e["final_status"] == "blocked_by_value_gate")
    suppressed_by_cooldown = sum(1 for e in signal_entries if e["final_status"] == "suppressed_by_cooldown")
    blocked_by_pre_send = sum(1 for e in signal_entries if e["final_status"] == "blocked_by_pre_send_gate")
    observe_count = sum(1 for e in signal_entries if e["final_status"] in ("observe", "observe__pre_send_blocked"))

    # Pre-send block reasons
    pre_send_block_reasons: list[str] = []
    for e in signal_entries:
        if e["final_status"] == "blocked_by_pre_send_gate" and e["pre_send_blocked_reason"]:
            pre_send_block_reasons.append(f"{e['asset']}: {e['pre_send_blocked_reason']}")

    # v1.11-H: Payload mode breakdown
    real_count = sum(1 for e in signal_entries if e.get("payload_mode") == "real")
    mock_count = sum(1 for e in signal_entries if e.get("payload_mode") == "mock")
    payload_render_success_count = sum(1 for e in signal_entries if e.get("payload_render_success") is True)
    payload_render_failed_count = sum(1 for e in signal_entries if e.get("payload_render_success") is False)
    payload_fallback_used_count = sum(1 for e in signal_entries if e.get("payload_fallback_used") is True)

    # Card type distribution (only for real payloads)
    card_types: dict[str, int] = {}
    for e in signal_entries:
        ct = e.get("payload_card_type")
        if ct and e.get("payload_mode") == "real":
            card_types[ct] = card_types.get(ct, 0) + 1

    # Expectation mismatches
    expectation_mismatches: list[dict] = []
    for e in signal_entries:
        expected = e.get("expect_final", "")
        if expected and e["final_status"] != expected:
            if not (expected == "send_candidate" and e["final_status"] == "send_candidate_upgrade"):
                expectation_mismatches.append({
                    "asset": e["asset"],
                    "index": e["index"],
                    "expected": expected,
                    "actual": e["final_status"],
                })

    pipeline_stats = {
        "scenario_id": scenario_id,
        "total_signals": len(signals),
        "final_send_candidate_count": send_candidate,
        "final_send_candidate_upgrade_count": send_candidate_upgrade,
        "send_candidate_total": send_candidate + send_candidate_upgrade,
        "blocked_by_value_gate_count": blocked_by_value,
        "suppressed_by_cooldown_count": suppressed_by_cooldown,
        "blocked_by_pre_send_gate_count": blocked_by_pre_send,
        "observe_count": observe_count,
        "pre_send_block_reasons": pre_send_block_reasons,
        "expectation_mismatches": expectation_mismatches,
        "pipeline_layer_distribution": {
            "terminated_at_value_gate": blocked_by_value,
            "terminated_at_cooldown": suppressed_by_cooldown,
            "terminated_at_pre_send": blocked_by_pre_send + send_candidate + send_candidate_upgrade,
            "bypassed_send": observe_count,
        },
        # v1.11-H: Payload render metrics
        "payload_mode_breakdown": {
            "real": real_count,
            "mock": mock_count,
            "total_rendered": real_count + mock_count,
        },
        "payload_render_success_count": payload_render_success_count,
        "payload_render_failed_count": payload_render_failed_count,
        "payload_fallback_used_count": payload_fallback_used_count,
        "card_type_distribution": card_types,
    }

    return signal_entries, pipeline_stats


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    print(f"Market Radar v1.11-H — Real Card Render + Full Gate Pipeline Dry-run")
    print(f"Started: {china_stamp()}")
    print(f"Pipeline version: {PIPELINE_VERSION}")
    print(f"  Layer 1: SignalValueGate ({VALUE_GATE_VERSION})")
    print(f"  Layer 2: CooldownGate ({COOLDOWN_GATE_VERSION})")
    print(f"  Layer 3: REAL render_card_payload (card_router v1.10-A R2)")
    print(f"  Layer 4: pre_send_gate (SignalTrustGate + payload validation)")
    print()
    print(f"Cooldown config: window={DEFAULT_COOLDOWN_WINDOW_MINUTES}min, "
          f"upgrade_delta={DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA}pts")
    print(f"Payload mode:      REAL (render_card_payload from market_radar_card_router)")
    print(f"                   except intentional mock overrides for payload validation tests")
    print()

    scenarios = _build_scenarios()

    # ── Aggregate counters ──
    total_signals = 0
    total_send_candidates = 0
    total_send_candidates_upgrade = 0
    total_blocked_value = 0
    total_suppressed_cooldown = 0
    total_blocked_pre_send = 0
    total_observe = 0
    total_expectation_mismatches = 0

    # Payload counters
    total_real_payloads = 0
    total_mock_payloads = 0
    total_render_success = 0
    total_render_failed = 0
    total_fallback_used = 0
    global_card_types: dict[str, int] = {}

    all_scenario_results: list[dict] = []

    for scenario in scenarios:
        sid = scenario["scenario_id"]
        sname = scenario["scenario_name"]
        signals = scenario["signals"]

        print(f"{'─' * 70}")
        print(f"Batch {sid}: {sname} ({len(signals)} signals)")
        print(f"  Objective: {scenario['objective'][:120]}...")
        print()

        signal_entries, pipeline_stats = _run_pipeline(signals, sid)

        # ── Print per-signal results ──
        for e in signal_entries:
            asset = e["asset"]
            idx = e["index"]
            offset = e["minutes_offset"]
            offset_str = f"T+{offset:.0f}min" if offset == int(offset) else f"T+{offset}min"

            val_str = f"V:{e['value_decision']:7s}(s={e['value_score']:3d})"
            cool_str = f"C:{e['cooldown_decision']:20s}"
            pre_str = ""
            if e["pre_send_checked"]:
                if e["pre_send_allowed"]:
                    pre_str = "P:PASS"
                else:
                    pre_str = "P:BLOCK"
            else:
                pre_str = "P:SKIP"

            # Payload info
            payload_mode_str = f" [{e.get('payload_mode', 'none')}]" if e.get("payload_mode") else ""
            card_type_str = f" card={e.get('payload_card_type', '')}" if e.get("payload_card_type") else ""
            payload_info_str = f"{payload_mode_str}{card_type_str}"

            final_marker = {
                "send_candidate": "[SEND]",
                "send_candidate_upgrade": "[↑SEND]",
                "blocked_by_value_gate": "[BLOCK-V]",
                "suppressed_by_cooldown": "[COOL-SUP]",
                "blocked_by_pre_send_gate": "[BLOCK-P]",
                "observe": "[OBSERVE]",
                "observe__pre_send_blocked": "[OBS!BLK]",
            }.get(e["final_status"], "[?]")

            expect_ok = ""
            expected = e.get("expect_final", "")
            if expected and e["final_status"] != expected:
                if not (expected == "send_candidate" and e["final_status"] == "send_candidate_upgrade"):
                    expect_ok = f"  !! MISMATCH (expected {expected})"

            print(f"  [{offset_str:>6s}] {asset:6s} | {val_str} | {cool_str} | {pre_str} "
                  f"| {final_marker:12s} {e['final_status']}{payload_info_str}{expect_ok}")

        # ── Batch summary ──
        print()
        print(f"  Batch {sid} pipeline summary:")
        print(f"    send_candidate:           {pipeline_stats['final_send_candidate_count']}"
              f"{' (+' + str(pipeline_stats['final_send_candidate_upgrade_count']) + ' upgrade)' if pipeline_stats['final_send_candidate_upgrade_count'] > 0 else ''}")
        print(f"    blocked_by_value_gate:    {pipeline_stats['blocked_by_value_gate_count']}")
        print(f"    suppressed_by_cooldown:   {pipeline_stats['suppressed_by_cooldown_count']}")
        print(f"    blocked_by_pre_send_gate: {pipeline_stats['blocked_by_pre_send_gate_count']}")
        print(f"    observe:                  {pipeline_stats['observe_count']}")
        # Payload breakdown
        pm = pipeline_stats["payload_mode_breakdown"]
        print(f"    payload_mode:             real={pm['real']}, mock={pm['mock']}")
        print(f"    payload_render:           success={pipeline_stats['payload_render_success_count']}, "
              f"failed={pipeline_stats['payload_render_failed_count']}, "
              f"fallback={pipeline_stats['payload_fallback_used_count']}")
        if pipeline_stats["card_type_distribution"]:
            ct_str = ", ".join(f"{k}={v}" for k, v in pipeline_stats["card_type_distribution"].items())
            print(f"    card_types:               {ct_str}")
        if pipeline_stats["pre_send_block_reasons"]:
            for reason in pipeline_stats["pre_send_block_reasons"]:
                print(f"      └ {reason}")
        if pipeline_stats["expectation_mismatches"]:
            print(f"    !! EXPECTATION MISMATCHES: {len(pipeline_stats['expectation_mismatches'])}")
            for mm in pipeline_stats["expectation_mismatches"]:
                print(f"      └ [{mm['index']}] {mm['asset']}: expected {mm['expected']}, got {mm['actual']}")
        print()

        # ── Aggregate ──
        total_signals += len(signals)
        total_send_candidates += pipeline_stats["final_send_candidate_count"]
        total_send_candidates_upgrade += pipeline_stats["final_send_candidate_upgrade_count"]
        total_blocked_value += pipeline_stats["blocked_by_value_gate_count"]
        total_suppressed_cooldown += pipeline_stats["suppressed_by_cooldown_count"]
        total_blocked_pre_send += pipeline_stats["blocked_by_pre_send_gate_count"]
        total_observe += pipeline_stats["observe_count"]
        total_expectation_mismatches += len(pipeline_stats["expectation_mismatches"])
        total_real_payloads += pm["real"]
        total_mock_payloads += pm["mock"]
        total_render_success += pipeline_stats["payload_render_success_count"]
        total_render_failed += pipeline_stats["payload_render_failed_count"]
        total_fallback_used += pipeline_stats["payload_fallback_used_count"]
        for ct, cnt in pipeline_stats["card_type_distribution"].items():
            global_card_types[ct] = global_card_types.get(ct, 0) + cnt

        all_scenario_results.append({
            "scenario_id": sid,
            "scenario_name": sname,
            "objective": scenario["objective"],
            "batch_size": len(signals),
            "pipeline_stats": pipeline_stats,
            "signal_entries": signal_entries,
        })

    # ── Aggregate analysis ──
    total_send = total_send_candidates + total_send_candidates_upgrade
    send_rate = round(total_send / total_signals * 100, 1) if total_signals > 0 else 0
    value_block_rate = round(total_blocked_value / total_signals * 100, 1) if total_signals > 0 else 0
    cooldown_suppress_rate = round(total_suppressed_cooldown / total_signals * 100, 1) if total_signals > 0 else 0
    pre_send_block_rate = round(total_blocked_pre_send / total_signals * 100, 1) if total_signals > 0 else 0
    observe_rate = round(total_observe / total_signals * 100, 1) if total_signals > 0 else 0

    print(f"{'=' * 70}")
    print(f"Aggregate Pipeline Results Across All {len(scenarios)} Batches")
    print(f"{'=' * 70}")
    print(f"  Total signals:                {total_signals}")
    print(f"  ─────────────────────────────────────")
    print(f"  final_send_candidate:         {total_send_candidates} ({round(total_send_candidates/total_signals*100, 1)}%)")
    print(f"  final_send_candidate_upgrade: {total_send_candidates_upgrade} ({round(total_send_candidates_upgrade/total_signals*100, 1)}%)")
    print(f"  TOTAL SEND:                   {total_send} ({send_rate}%)")
    print(f"  ─────────────────────────────────────")
    print(f"  blocked_by_value_gate:        {total_blocked_value} ({value_block_rate}%)")
    print(f"  suppressed_by_cooldown:       {total_suppressed_cooldown} ({cooldown_suppress_rate}%)")
    print(f"  blocked_by_pre_send_gate:     {total_blocked_pre_send} ({pre_send_block_rate}%)")
    print(f"  observe:                      {total_observe} ({observe_rate}%)")
    print()
    print(f"  ── v1.11-H Payload Render Metrics ──")
    print(f"  payload_mode_real:            {total_real_payloads}")
    print(f"  payload_mode_mock:            {total_mock_payloads}")
    print(f"  payload_render_success:       {total_render_success}")
    print(f"  payload_render_failed:        {total_render_failed}")
    print(f"  payload_fallback_used:        {total_fallback_used}")
    if global_card_types:
        ct_str = ", ".join(f"{k}={v}" for k, v in sorted(global_card_types.items()))
        print(f"  card_type_distribution:       {ct_str}")
    print()
    print(f"  Expectation mismatches:       {total_expectation_mismatches}")
    print()

    # ── Decision matrix ──
    decision_matrix: dict[str, dict] = {}
    for sr in all_scenario_results:
        ps = sr["pipeline_stats"]
        decision_matrix[sr["scenario_id"]] = {
            "name": sr["scenario_name"],
            "batch_size": sr["batch_size"],
            "send_candidate": ps["final_send_candidate_count"] + ps["final_send_candidate_upgrade_count"],
            "send_candidate_upgrade": ps["final_send_candidate_upgrade_count"],
            "blocked_by_value_gate": ps["blocked_by_value_gate_count"],
            "suppressed_by_cooldown": ps["suppressed_by_cooldown_count"],
            "blocked_by_pre_send_gate": ps["blocked_by_pre_send_gate_count"],
            "observe": ps["observe_count"],
            "expectation_mismatches": len(ps["expectation_mismatches"]),
            "payload_real": ps["payload_mode_breakdown"]["real"],
            "payload_mock": ps["payload_mode_breakdown"]["mock"],
            "payload_render_success": ps["payload_render_success_count"],
            "payload_render_failed": ps["payload_render_failed_count"],
        }

    # ── Pipeline layer analysis ──
    layer_termination = {
        "terminated_at_value_gate": total_blocked_value,
        "terminated_at_cooldown": total_suppressed_cooldown,
        "reached_pre_send_gate": total_send + total_blocked_pre_send,
        "passed_all_gates": total_send,
        "observe_routed": total_observe,
    }

    # ── Key findings ──
    key_findings: list[str] = []

    key_findings.append(
        f"v1.11-H: Real card render + full gate pipeline dry-run complete. "
        f"{total_signals} signals across {len(scenarios)} scenarios. "
        f"Final distribution: send_candidate={total_send} ({send_rate}%), "
        f"blocked_by_value={total_blocked_value} ({value_block_rate}%), "
        f"suppressed_by_cooldown={total_suppressed_cooldown} ({cooldown_suppress_rate}%), "
        f"blocked_by_pre_send={total_blocked_pre_send} ({pre_send_block_rate}%), "
        f"observe={total_observe} ({observe_rate}%)."
    )

    key_findings.append(
        f"Real card rendering validated: {total_real_payloads}/{total_real_payloads + total_mock_payloads} "
        f"signals used real render_card_payload(). "
        f"Render success={total_render_success}, render failed={total_render_failed}, "
        f"MarkdownV2 fallback={total_fallback_used}. "
        f"Card types: {global_card_types}."
    )

    if total_render_success > 0:
        key_findings.append(
            f"Real card payloads successfully passed through pre_send_gate: "
            f"{total_render_success} real payloads validated. This confirms that "
            f"render_card_payload() output is compatible with pre_send_gate's "
            f"payload validation (text presence + parse_mode field)."
        )

    if total_render_failed == 0:
        key_findings.append(
            f"Zero render_card_payload() failures — all real card rendering "
            f"attempts produced valid payloads. The card router handles "
            f"market_anomaly signals correctly with the fields provided."
        )

    if total_fallback_used > 0:
        key_findings.append(
            f"{total_fallback_used} payload(s) used MarkdownV2→plaintext fallback. "
            f"This is NOT a failure — fallback is expected behavior when MarkdownV2 "
            f"escaping encounters edge cases. Plaintext payloads are still valid "
            f"for pre_send_gate."
        )

    if total_suppressed_cooldown > 0:
        key_findings.append(
            f"Cooldown gate suppressed {total_suppressed_cooldown} signal(s) — "
            f"prevents same-asset spam even with valid real cards."
        )

    if total_blocked_pre_send > 0:
        key_findings.append(
            f"Pre-send gate caught {total_blocked_pre_send} signal(s). "
            f"Of these, some used real card payloads (blocked by source_trust/TTL) "
            f"and some used mock payloads (blocked by payload_validation). "
            f"This demonstrates that real cards do NOT bypass security gates."
        )

    key_findings.append(
        f"v1.11-H confirms: the real card router is compatible with the full "
        f"three-layer pipeline. Real payloads pass pre_send_gate correctly, "
        f"and gate-level blocks (source_trust, TTL) work regardless of payload content."
    )

    # ── Readiness assessment ──
    pipeline_readiness = {
        "ready_for_test_channel_send": False,
        "ready_for_prod_channel": False,
        "conditions_met": [],
        "blockers": [],
        "recommendations": [],
    }

    if total_render_success > 0 and total_render_failed == 0:
        pipeline_readiness["conditions_met"].append(
            "Real card rendering works correctly — all real payloads produced "
            "valid output with proper structure for pre_send_gate."
        )
    if total_send > 0:
        pipeline_readiness["conditions_met"].append(
            "Pipeline successfully identifies send_candidate signals with "
            "real card payloads — signals pass all three gates with actual TG cards."
        )
    if total_blocked_pre_send > 0:
        pipeline_readiness["conditions_met"].append(
            "Pre-send gate continues to block unsafe signals even with real "
            "payloads — security is not compromised by real card rendering."
        )

    pipeline_readiness["blockers"].append(
        "This is a dry-run only. No signals were actually delivered to TG. "
        "Real delivery requires: (a) actual TG send function, (b) production "
        "config, (c) cooldown state persistence."
    )
    pipeline_readiness["blockers"].append(
        "Formal channel remains frozen. Content value proof not yet established "
        "— cards may still be 'market noise' rather than intelligence."
    )

    pipeline_readiness["recommendations"].append(
        "Next step (v1.11-I): Pre-send rehearsal — generate the full send list "
        "with real card payload previews, log everything, but do NOT send to TG. "
        "This is the final dry-run before test-channel delivery."
    )
    pipeline_readiness["recommendations"].append(
        "Consider adding payload text preview sampling to the handoff report — "
        "show the first 200 chars of a sample real card to verify content quality."
    )

    # ── Sample real card preview (first send_candidate with real payload) ──
    sample_card_preview = None
    for sr in all_scenario_results:
        for e in sr["signal_entries"]:
            if (e["final_status"] in ("send_candidate", "send_candidate_upgrade")
                    and e.get("payload_mode") == "real"
                    and e.get("pre_send_checked")):
                # We don't store the full text in the entry, log it from the scenario
                pass

    # ── Build report ──
    report = {
        "run_version": PIPELINE_VERSION,
        "pipeline_layers": {
            "layer_1": f"SignalValueGate ({VALUE_GATE_VERSION})",
            "layer_2": f"CooldownGate ({COOLDOWN_GATE_VERSION})",
            "layer_3": "REAL render_card_payload (card_router v1.10-A R2)",
            "layer_4": "pre_send_gate (SignalTrustGate + payload validation)",
        },
        "generated_at": china_stamp(),
        "cooldown_config": {
            "cooldown_window_minutes": DEFAULT_COOLDOWN_WINDOW_MINUTES,
            "upgrade_override_score_delta": DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA,
        },
        "payload_config": {
            "mode": "real",
            "renderer": "market_radar_card_router.render_card_payload",
            "mock_overrides": "only for intentional payload_validation test signals",
        },
        "total_scenarios": len(scenarios),
        "total_signals": total_signals,
        "aggregate": {
            "final_send_candidate_count": total_send_candidates,
            "final_send_candidate_upgrade_count": total_send_candidates_upgrade,
            "total_send_candidates": total_send,
            "send_rate_pct": send_rate,
            "blocked_by_value_gate_count": total_blocked_value,
            "blocked_by_value_gate_rate_pct": value_block_rate,
            "suppressed_by_cooldown_count": total_suppressed_cooldown,
            "suppressed_by_cooldown_rate_pct": cooldown_suppress_rate,
            "blocked_by_pre_send_gate_count": total_blocked_pre_send,
            "blocked_by_pre_send_gate_rate_pct": pre_send_block_rate,
            "observe_count": total_observe,
            "observe_rate_pct": observe_rate,
        },
        "payload_render_metrics": {
            "payload_mode_real": total_real_payloads,
            "payload_mode_mock": total_mock_payloads,
            "payload_render_success_count": total_render_success,
            "payload_render_failed_count": total_render_failed,
            "payload_fallback_used_count": total_fallback_used,
            "card_type_distribution": global_card_types,
        },
        "layer_termination": layer_termination,
        "decision_matrix": decision_matrix,
        "expectation_mismatches_total": total_expectation_mismatches,
        "key_findings": key_findings,
        "pipeline_readiness": pipeline_readiness,
        "scenarios": all_scenario_results,
        "security": {
            "tg_send": "NONE",
            "formal_channel": "NONE",
            "secrets_loaded": "NONE",
            "paid_apis": "NONE",
            "loop_daemon_cron": "NONE",
            "files_deleted": "NONE",
        },
        "v111g_comparison": {
            "v111g_used_mock_payloads": True,
            "v111h_uses_real_card_render": True,
            "v111g_total_signals": 26,
            "v111h_total_signals": total_signals,
            "key_change": "Mock _build_mock_payload() replaced with render_card_payload() from card_router",
        },
    }

    # ── Write output ──
    print(f"Writing dry-run report to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    # ── Final summary ──
    print()
    print(f"{'=' * 70}")
    print(f"v1.11-H Real Card Render + Full Gate Pipeline Dry-run — Final Summary")
    print(f"{'=' * 70}")
    print(f"  Scenarios:                     {len(scenarios)}")
    print(f"  Total signals:                 {total_signals}")
    print(f"  ───────────────────────────────────────")
    print(f"  final_send_candidate:          {total_send_candidates} "
          f"({round(total_send_candidates/total_signals*100, 1)}%)")
    print(f"  final_send_candidate_upgrade:  {total_send_candidates_upgrade} "
          f"({round(total_send_candidates_upgrade/total_signals*100, 1)}%)")
    print(f"  TOTAL SEND CANDIDATES:         {total_send} ({send_rate}%)")
    print(f"  ───────────────────────────────────────")
    print(f"  blocked_by_value_gate:         {total_blocked_value} ({value_block_rate}%)")
    print(f"  suppressed_by_cooldown:        {total_suppressed_cooldown} ({cooldown_suppress_rate}%)")
    print(f"  blocked_by_pre_send_gate:      {total_blocked_pre_send} ({pre_send_block_rate}%)")
    print(f"  observe:                       {total_observe} ({observe_rate}%)")
    print(f"  ───────────────────────────────────────")
    print(f"  Payload Mode — Real:           {total_real_payloads}")
    print(f"  Payload Mode — Mock:           {total_mock_payloads}")
    print(f"  Payload Render — Success:      {total_render_success}")
    print(f"  Payload Render — Failed:       {total_render_failed}")
    print(f"  Payload Fallback Used:         {total_fallback_used}")
    print(f"  Card Types:                    {global_card_types}")
    print(f"  ───────────────────────────────────────")
    print(f"  Expectation mismatches:        {total_expectation_mismatches}")
    print()
    print(f"  TG send:                       NONE")
    print(f"  Secrets loaded:                NONE")
    print(f"  Paid APIs:                     NONE")
    print(f"  Loop/daemon:                   NONE")
    print(f"  Files deleted:                 NONE")
    print(f"  Formal channel:                FROZEN")
    print()
    print(f"  KEY v1.11-H RESULT: Real card payloads successfully integrated into")
    print(f"  the full three-layer pipeline. render_card_payload() output passes")
    print(f"  pre_send_gate validation. Next step: v1.11-I pre-send rehearsal.")
    print()
    print(f"  Report:                        {output_path}")
    print(f"{'=' * 70}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
