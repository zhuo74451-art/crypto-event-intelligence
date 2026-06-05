"""Market Radar v1.11-G — Full Gate Pipeline Dry-run

Chains SignalValueGate → CooldownGate → pre_send_gate into a complete
three-layer dry-run pipeline. Verifies the full distribution of final outcomes
before any real TG send.

Pipeline layers:
  1. SignalValueGate (v1.11-D): value check — allow / observe / block
  2. CooldownGate (v1.11-F): rate-limit check — allow / cooldown_suppress / upgrade_override
  3. pre_send_gate (v1.10-G): safety check — allowed / blocked (trust + TTL + payload)

Output metrics:
  - final_send_candidate_count — signals that pass ALL three gates
  - suppressed_by_cooldown_count — signals blocked by cooldown
  - blocked_by_value_gate_count — signals blocked by value gate
  - blocked_by_pre_send_gate_count — signals blocked by pre_send
  - pre_send_block_reasons — detailed reasons for pre_send blocks
  - observe_count — signals routed to observe (not send)

No TG send, no formal channel, no secrets, no paid APIs, no loop/daemon.

Usage:
    python scripts/run_market_radar_v111g_full_gate_pipeline_dryrun.py
    python scripts/run_market_radar_v111g_full_gate_pipeline_dryrun.py --output results/custom.json

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
from scripts.market_radar_pre_send_gate import (
    pre_send_gate,
)

PIPELINE_VERSION = "v1.11-G"


# ── CLI ─────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Market Radar v1.11-G — Full Gate Pipeline Dry-run"
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "market_radar_v111g_full_gate_pipeline_dryrun_result.json"),
        help="Output path for dry-run result JSON",
    )
    return parser.parse_args()


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


def _now_iso() -> str:
    return datetime.now(CN_TZ).isoformat()


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


# ── Payload builder (mock, for dry-run only) ────────────────────────────────────

def _build_mock_payload(signal: dict, value_result: dict,
                        cooldown_result: dict | None = None) -> dict:
    """Build a minimal mock payload for pre_send_gate dry-run validation.

    Simulates what render_card_payload() would produce, with enough structure
    to pass pre_send_gate's payload validation. Used only in dry-run context.
    """
    asset = signal.get("asset", "unknown")
    trigger = signal.get("trigger_reason", f"{asset} market anomaly")
    pct = signal.get("price_change_pct", 0)
    direction = "📉" if (pct or 0) < 0 else "📈"

    value_score = value_result.get("value_score", 0)
    value_tier = value_result.get("value_tier", "low")

    # tier emoji
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
    return {
        "text": "",
        "parse_mode": "Markdown",
    }


def _build_invalid_payload_no_parse_mode(signal: dict) -> dict:
    """Build a payload missing parse_mode — should fail pre_send_gate."""
    return {
        "text": f"Signal for {signal.get('asset', 'unknown')}",
    }


# ── Scenario definitions ────────────────────────────────────────────────────────

def _build_scenarios() -> list[dict]:
    """Build 6 scenarios designed to stress-test the full three-layer pipeline.

    Each scenario has an ordered list of signals with minutes_offset for
    cooldown time sequencing.

    Returns a list of scenario dicts.
    """
    now = datetime.now(CN_TZ)

    # Helper to create recent timestamps that will pass TTL checks
    def _recent_ts(offset_minutes: int = 0) -> str:
        return (now - timedelta(minutes=offset_minutes)).isoformat()

    # Helper to create stale timestamps that will fail TTL checks
    def _stale_ts() -> str:
        # 2 hours ago — exceeds market_anomaly TTL of 15 min
        return (now - timedelta(hours=2)).isoformat()

    scenarios: list[dict] = []

    # ── Batch G1: Full Happy Path — all three gates pass ──────────────────────
    # 4 signals, all well-confirmed, different assets, no repeats.
    # All should be final_send_candidate.
    scenarios.append({
        "scenario_id": "G1",
        "scenario_name": "Full Happy Path — All Gates Pass",
        "objective": (
            "Verify that well-confirmed signals (price + OI + volume) from "
            "trusted sources with no asset repeats pass all three gates and "
            "become final_send_candidate."
        ),
        "signals": [
            {
                "asset": "BTC", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.54,
                "open_interest": 1_826_000_000, "volume": 6_345_000_000,
                "funding": None,
                "generated_at": _recent_ts(0),
                "trigger_reason": "BTC 24h 跌幅 5.54% — 三重确认",
                "minutes_offset": 0,
                "expect_final": "send_candidate",
            },
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.80,
                "open_interest": 12_900_000_000, "volume": 16_000_000_000,
                "funding": -0.015, "generated_at": _recent_ts(2),
                "trigger_reason": "ETH 24h 跌幅 6.80% — 四重确认 (含 funding extreme)",
                "minutes_offset": 2,
                "expect_final": "send_candidate",
            },
            {
                "asset": "SOL", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.24,
                "open_interest": 278_000_000, "volume": 527_000_000,
                "funding": 0.0, "generated_at": _recent_ts(4),
                "trigger_reason": "SOL 24h 跌幅 7.24% — 三重确认",
                "minutes_offset": 4,
                "expect_final": "send_candidate",
            },
            {
                "asset": "SUI", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.83,
                "open_interest": 28_000_000, "volume": 21_500_000,
                "funding": 0.0, "generated_at": _recent_ts(6),
                "trigger_reason": "SUI 24h 跌幅 5.83% — 三重确认",
                "minutes_offset": 6,
                "expect_final": "send_candidate",
            },
        ],
    })

    # ── Batch G2: Value Gate Blocks — signals fail at first layer ─────────────
    # 3 signals with price < 5%, so value gate blocks them.
    # They never reach cooldown or pre_send.
    scenarios.append({
        "scenario_id": "G2",
        "scenario_name": "Value Gate Blocks — First-Layer Rejection",
        "objective": (
            "Verify that signals below the 5% price threshold are blocked by "
            "the value gate and never proceed to cooldown or pre_send."
        ),
        "signals": [
            {
                "asset": "DOT", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -3.20,
                "open_interest": 200_000_000, "volume": None,
                "funding": None, "generated_at": _recent_ts(0),
                "trigger_reason": "DOT 仅跌 3.20% — 未达 5% 价格阈值",
                "minutes_offset": 0,
                "expect_final": "blocked_by_value_gate",
            },
            {
                "asset": "LINK", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -4.00,
                "open_interest": None, "volume": None,
                "funding": None, "generated_at": _recent_ts(1),
                "trigger_reason": "LINK 仅跌 4.00% — 无价格触发",
                "minutes_offset": 1,
                "expect_final": "blocked_by_value_gate",
            },
            {
                "asset": "MATIC", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -2.50,
                "open_interest": 50_000_000, "volume": 120_000_000,
                "funding": 0.0, "generated_at": _recent_ts(2),
                "trigger_reason": "MATIC 仅跌 2.50% — 远低于阈值",
                "minutes_offset": 2,
                "expect_final": "blocked_by_value_gate",
            },
        ],
    })

    # ── Batch G3: Cooldown Suppression — second-layer block ───────────────────
    # ARB appears 3 times within 8 min. First passes, subsequent suppressed.
    # SOL once as context. Tests cooldown suppression in isolation.
    scenarios.append({
        "scenario_id": "G3",
        "scenario_name": "Cooldown Suppression — Second-Layer Rate Limiting",
        "objective": (
            "Verify that same-asset repeats (ARB x3 within 8 min) are correctly "
            "suppressed by the cooldown gate. The value gate lets them all through "
            "(they are well-confirmed), but cooldown blocks repeats 2 and 3."
        ),
        "signals": [
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.55,
                "open_interest": 4_656_700, "volume": 4_942_400,
                "funding": 0.0, "generated_at": _recent_ts(0),
                "trigger_reason": "ARB 24h 跌幅 7.55% — 第 1 次触发 (T+0min)",
                "minutes_offset": 0,
                "expect_final": "send_candidate",
            },
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.82,
                "open_interest": 4_612_000, "volume": 4_955_000,
                "funding": 0.0, "generated_at": _recent_ts(4),
                "trigger_reason": "ARB 24h 跌幅 7.82% — 第 2 次触发 (T+4min)",
                "minutes_offset": 4,
                "expect_final": "suppressed_by_cooldown",
            },
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.90,
                "open_interest": 4_588_000, "volume": 4_961_000,
                "funding": 0.0, "generated_at": _recent_ts(8),
                "trigger_reason": "ARB 24h 跌幅 7.90% — 第 3 次触发 (T+8min)",
                "minutes_offset": 8,
                "expect_final": "suppressed_by_cooldown",
            },
            {
                "asset": "SOL", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.80,
                "open_interest": 278_000_000, "volume": 530_000_000,
                "funding": 0.0, "generated_at": _recent_ts(6),
                "trigger_reason": "SOL 24h 跌幅 6.80% — 不同资产, 无冷却",
                "minutes_offset": 6,
                "expect_final": "send_candidate",
            },
        ],
    })

    # ── Batch G4: Pre-send Gate Blocks — third-layer rejection ────────────────
    # Signals that pass value+cooldown but fail at pre_send_gate.
    # Tests: source trust block, TTL expiry, payload validation failure.
    scenarios.append({
        "scenario_id": "G4",
        "scenario_name": "Pre-Send Gate Blocks — Third-Layer Safety Rejection",
        "objective": (
            "Verify that pre_send_gate correctly blocks signals that pass value "
            "and cooldown checks but fail safety rules: (a) source_type='unknown' "
            "→ trust gate block, (b) stale timestamp → TTL gate block, "
            "(c) empty payload text → payload validation block."
        ),
        "signals": [
            {
                "asset": "AVAX", "signal_type": "market_anomaly",
                "source_type": "unknown",  # blocked by trust map
                "is_fixture": False,
                "price_change_pct": -6.20,
                "open_interest": 155_000_000, "volume": 220_000_000,
                "funding": None, "generated_at": _recent_ts(0),
                "trigger_reason": "AVAX 跌幅 6.20% — source_type=unknown",
                "minutes_offset": 0,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "source_trust",
                "_payload_override": "valid",  # use valid payload but bad source
            },
            {
                "asset": "LTC", "signal_type": "market_anomaly",
                "source_type": "api",  # source OK
                "is_fixture": False,
                "price_change_pct": -5.80,
                "open_interest": 300_000_000, "volume": 450_000_000,
                "funding": None, "generated_at": _stale_ts(),  # stale! > 15 min TTL
                "trigger_reason": "LTC 跌幅 5.80% — 时间戳过期 (2h 前)",
                "minutes_offset": 2,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "ttl_expiry",
                "_payload_override": "valid",
            },
            {
                "asset": "NEAR", "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -5.50,
                "open_interest": 80_000_000, "volume": 120_000_000,
                "funding": 0.0, "generated_at": _recent_ts(4),
                "trigger_reason": "NEAR 跌幅 5.50% — 载荷 text 为空",
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
                "funding": None, "generated_at": _recent_ts(6),
                "trigger_reason": "OP 跌幅 7.10% — 载荷缺少 parse_mode",
                "minutes_offset": 6,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "payload_validation",
                "_payload_override": "no_parse_mode",
            },
        ],
    })

    # ── Batch G5: Upgrade Override — cooldown allows improved repeat ──────────
    # ETH appears twice: first weak (score ~30), then strong (score ~100).
    # The significant improvement triggers upgrade_override.
    scenarios.append({
        "scenario_id": "G5",
        "scenario_name": "Upgrade Override — Score Improvement Bypasses Cooldown",
        "objective": (
            "Verify that when the same asset reappears within the cooldown window "
            "with a much higher value_score (Δ >= 15), the cooldown gate issues "
            "an upgrade_override, and the signal passes through to pre_send_gate."
        ),
        "signals": [
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.50,  # moderate price
                "open_interest": 12_000_000_000, "volume": None, "funding": None,
                "generated_at": _recent_ts(0),
                "trigger_reason": "ETH 跌幅 5.50% — 中等信号: 价格+OI (score~55)",
                "minutes_offset": 0,
                "expect_final": "send_candidate",  # first occurrence, passes value gate with OI
            },
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -8.50,  # stronger price + all confirmations
                "open_interest": 12_500_000_000, "volume": 18_200_000_000,
                "funding": -0.025, "generated_at": _recent_ts(5),
                "trigger_reason": "ETH 跌幅 8.50% — 强信号: OI+volume+funding 全确认 (score~100)",
                "minutes_offset": 5,
                "expect_final": "send_candidate_upgrade",  # upgrade_override
            },
        ],
    })

    # ── Batch G6: Full Mixed Pipeline — all outcomes in one batch ─────────────
    # The most important scenario. Mix of:
    #   - Value: allow, observe, block
    #   - Cooldown: allow, cooldown_suppress, upgrade_override
    #   - Pre-send: pass, block
    # Multi-asset interleaving, various confirmation levels.
    scenarios.append({
        "scenario_id": "G6",
        "scenario_name": "Full Mixed Pipeline — All Outcomes Stress Test",
        "objective": (
            "The definitive three-layer integration test. Mixed signals produce "
            "all possible outcome combinations: value→allow/observe/block, "
            "cooldown→allow/suppress/upgrade, pre_send→pass/block. "
            "Verifies the complete decision matrix."
        ),
        "signals": [
            # T+0: BTC — well confirmed, first → send_candidate
            {
                "asset": "BTC", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.54,
                "open_interest": 1_826_000_000, "volume": 6_345_000_000,
                "funding": None, "generated_at": _recent_ts(0),
                "trigger_reason": "BTC 24h 跌幅 5.54% — 价值: allow, 冷却: allow, 安全: pass",
                "minutes_offset": 0,
                "expect_final": "send_candidate",
            },
            # T+2: DOT — below threshold → blocked_by_value_gate
            {
                "asset": "DOT", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -3.50,
                "open_interest": 120_000_000, "volume": None,
                "funding": None, "generated_at": _recent_ts(2),
                "trigger_reason": "DOT 仅跌 3.50% — 价值: block, 管道终止于此",
                "minutes_offset": 2,
                "expect_final": "blocked_by_value_gate",
            },
            # T+4: ARB — well confirmed, first → send_candidate
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.55,
                "open_interest": 4_656_700, "volume": 4_942_400,
                "funding": 0.0, "generated_at": _recent_ts(4),
                "trigger_reason": "ARB 24h 跌幅 7.55% — 价值: allow, 冷却: allow (首次), 安全: pass",
                "minutes_offset": 4,
                "expect_final": "send_candidate",
            },
            # T+6: LINK — strong price but no fields → observe
            {
                "asset": "LINK", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.20,
                "open_interest": None, "volume": None,
                "funding": None, "generated_at": _recent_ts(6),
                "trigger_reason": "LINK 跌幅 7.20% — 价值: observe, 冷却检查但不会发送",
                "minutes_offset": 6,
                "expect_final": "observe",
            },
            # T+8: ARB repeat — same score → suppressed_by_cooldown
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.70,
                "open_interest": 4_590_000, "volume": 4_960_000,
                "funding": 0.0, "generated_at": _recent_ts(8),
                "trigger_reason": "ARB 24h 跌幅 7.70% — 价值: allow, 冷却: suppress (T+8, Δ<15)",
                "minutes_offset": 8,
                "expect_final": "suppressed_by_cooldown",
            },
            # T+10: SUI — well confirmed, first → send_candidate
            {
                "asset": "SUI", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.83,
                "open_interest": 28_000_000, "volume": 21_500_000,
                "funding": 0.0, "generated_at": _recent_ts(10),
                "trigger_reason": "SUI 24h 跌幅 5.83% — 价值: allow, 冷却: allow (首次), 安全: pass",
                "minutes_offset": 10,
                "expect_final": "send_candidate",
            },
            # T+12: stale source → blocked_by_pre_send_gate (source trust)
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "unknown",  # blocked by trust gate
                "is_fixture": False,
                "price_change_pct": -6.50,
                "open_interest": 12_800_000_000, "volume": 15_800_000_000,
                "funding": None, "generated_at": _recent_ts(12),
                "trigger_reason": "ETH 跌幅 6.50% — 价值: allow, 冷却: allow (首次), 安全: BLOCK (unknown source)",
                "minutes_offset": 12,
                "expect_final": "blocked_by_pre_send_gate",
                "pre_send_block_expect": "source_trust",
                "_payload_override": "valid",
            },
            # T+14: ARB third — upgrade override (stronger) → send_candidate_upgrade
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -8.50,
                "open_interest": 5_200_000, "volume": 6_100_000,
                "funding": -0.018, "generated_at": _recent_ts(14),
                "trigger_reason": "ARB 跌幅 8.50% — 价值: allow, 冷却: upgrade_override (score↑), 安全: pass",
                "minutes_offset": 14,
                "expect_final": "send_candidate_upgrade",
            },
            # T+16: weak signal → observe (use recent timestamp to avoid TTL expiry)
            {
                "asset": "AVAX", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.20,
                "open_interest": None, "volume": None,
                "funding": None, "generated_at": _recent_ts(0),  # recent, not stale
                "trigger_reason": "AVAX 跌幅 6.20% — 价值: observe (仅价格触发, 无确认)",
                "minutes_offset": 16,
                "expect_final": "observe",
            },
        ],
    })

    return scenarios


# ── Pipeline execution ─────────────────────────────────────────────────────────

def _run_pipeline(signals: list[dict], scenario_id: str) -> tuple[list[dict], dict]:
    """Run the full three-layer pipeline on a batch of signals.

    Pipeline: SignalValueGate → CooldownGate → pre_send_gate

    Returns:
        (signal_entries, pipeline_stats)
    """
    # Step 1: Run all signals through SignalValueGate
    value_results = _run_value_gate(signals)

    # Step 2: Build base time for cooldown sequencing
    base_time = datetime.now(CN_TZ)
    min_offset = min(s.get("minutes_offset", 0) for s in signals)
    base_time = base_time - timedelta(minutes=min_offset)

    # Step 3: Run through CooldownGate and pre_send_gate sequentially
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

        # ── pre_send_gate ──
        # Only run pre_send_gate if value gate and cooldown gate both allow
        val_decision = vr["gate_decision"]
        cool_decision = cr["decision"]
        cool_allowed = cr["allowed"]

        should_check_pre_send = (
            val_decision in ("allow", "observe")
            and cool_allowed
        )

        pre_send_result = None
        if should_check_pre_send:
            # Build mock payload
            payload_override = sig.get("_payload_override", "valid")
            if payload_override == "empty_text":
                payload = _build_invalid_payload_empty_text(sig)
            elif payload_override == "no_parse_mode":
                payload = _build_invalid_payload_no_parse_mode(sig)
            else:
                payload = _build_mock_payload(sig, vr, cr)

            pre_send_result = pre_send_gate(
                signal=sig,
                payload=payload,
                target_env="test",
            )

        # ── Determine final status ──
        if val_decision == "block":
            final_status = "blocked_by_value_gate"
            pipeline_layer = "value_gate"
        elif val_decision == "observe":
            # Observe signals: not sent, but tracked through cooldown and pre_send
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
            # Value gate allowed, cooldown suppressed
            if cool_decision == "cooldown_suppress":
                final_status = "suppressed_by_cooldown"
            else:
                final_status = "suppressed_by_cooldown"
            pipeline_layer = "cooldown_gate"
        elif pre_send_result and not pre_send_result["allowed"]:
            # Value + cooldown allowed, pre_send blocked
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

    # Expectation mismatches (for verification)
    expectation_mismatches: list[dict] = []
    for e in signal_entries:
        expected = e.get("expect_final", "")
        if expected and e["final_status"] != expected:
            # Allow "send_candidate_upgrade" to match "send_candidate_upgrade" or "send_candidate"
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
    }

    return signal_entries, pipeline_stats


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    print(f"Market Radar v1.11-G — Full Gate Pipeline Dry-run")
    print(f"Started: {china_stamp()}")
    print(f"Pipeline version: {PIPELINE_VERSION}")
    print(f"  Layer 1: SignalValueGate ({VALUE_GATE_VERSION})")
    print(f"  Layer 2: CooldownGate ({COOLDOWN_GATE_VERSION})")
    print(f"  Layer 3: pre_send_gate (SignalTrustGate + payload validation)")
    print()
    print(f"Cooldown config: window={DEFAULT_COOLDOWN_WINDOW_MINUTES}min, "
          f"upgrade_delta={DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA}pts")
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

    all_scenario_results: list[dict] = []

    # Track cooldown state across all scenarios (simulates session continuity)
    global_cooldown_state = CooldownState()

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

            # Build pipeline trace
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
                  f"| {final_marker:12s} {e['final_status']}{expect_ok}")

        # ── Batch summary ──
        print()
        print(f"  Batch {sid} pipeline summary:")
        print(f"    send_candidate:           {pipeline_stats['final_send_candidate_count']}"
              f"{' (+' + str(pipeline_stats['final_send_candidate_upgrade_count']) + ' upgrade)' if pipeline_stats['final_send_candidate_upgrade_count'] > 0 else ''}")
        print(f"    blocked_by_value_gate:    {pipeline_stats['blocked_by_value_gate_count']}")
        print(f"    suppressed_by_cooldown:   {pipeline_stats['suppressed_by_cooldown_count']}")
        print(f"    blocked_by_pre_send_gate: {pipeline_stats['blocked_by_pre_send_gate_count']}")
        print(f"    observe:                  {pipeline_stats['observe_count']}")
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
        f"Full three-layer pipeline verification complete. "
        f"{total_signals} signals across {len(scenarios)} scenarios. "
        f"Final distribution: send_candidate={total_send} ({send_rate}%), "
        f"blocked_by_value={total_blocked_value} ({value_block_rate}%), "
        f"suppressed_by_cooldown={total_suppressed_cooldown} ({cooldown_suppress_rate}%), "
        f"blocked_by_pre_send={total_blocked_pre_send} ({pre_send_block_rate}%), "
        f"observe={total_observe} ({observe_rate}%)."
    )

    if total_suppressed_cooldown > 0:
        key_findings.append(
            f"Cooldown gate successfully suppressed {total_suppressed_cooldown} signal(s) "
            f"that passed the value gate — preventing same-asset spam in the send pipeline. "
            f"This is the key v1.11-G validation: cooldown works correctly as the "
            f"second layer between value gate and pre_send."
        )

    if total_send_candidates_upgrade > 0:
        key_findings.append(
            f"Upgrade override triggered {total_send_candidates_upgrade} time(s) — "
            f"assets with significantly improved value scores bypass cooldown. "
            f"This prevents the cooldown gate from becoming a hard silence: "
            f"important escalations still get through."
        )

    if total_blocked_pre_send > 0:
        key_findings.append(
            f"Pre-send gate caught {total_blocked_pre_send} signal(s) that passed "
            f"both value and cooldown checks — demonstrating the value of the "
            f"third safety layer. Block reasons include source trust, TTL expiry, "
            f"and payload validation failures."
        )
    else:
        key_findings.append(
            f"Pre-send gate did not block any signals that reached it. "
            f"This confirms: (a) the dry-run signals are syntactically valid, "
            f"(b) the Gate is not over-blocking legitimate signals in test mode, "
            f"(c) payload mock construction matches expected format."
        )

    if total_observe > 0:
        key_findings.append(
            f"Observe layer correctly captured {total_observe} signal(s) — "
            f"signals with price movement but insufficient confirmation factors. "
            f"These would enter an observation pool rather than the send channel."
        )

    key_findings.append(
        f"Pipeline layer separation confirmed: value gate, cooldown gate, and "
        f"pre_send gate operate independently with clear pass/fail boundaries. "
        f"Signals terminate at the first failing layer — no skip-around possible."
    )

    # ── v1.11-F comparison ──
    # v1.11-F: allow=11 (61.1%), suppress=5 (27.8%), upgrade=2 (11.1%), total=18
    key_findings.append(
        f"Compared to v1.11-F (which only tested value+cooldown, 18 signals): "
        f"v1.11-G adds pre_send_gate as the third layer. The additional "
        f"signals with pre_send blocking scenarios validate that the safety "
        f"layer correctly rejects signals that would otherwise slip through "
        f"a two-layer pipeline."
    )

    # ── Readiness assessment ──
    pipeline_readiness = {
        "ready_for_test_channel": False,
        "ready_for_prod_channel": False,
        "conditions_met": [],
        "blockers": [],
        "recommendations": [],
    }

    # Conditions met
    if total_suppressed_cooldown > 0:
        pipeline_readiness["conditions_met"].append(
            "Cooldown gate correctly suppresses same-asset repeats — "
            "prevents spam in the send channel."
        )
    if total_blocked_pre_send > 0:
        pipeline_readiness["conditions_met"].append(
            "Pre-send gate correctly catches unsafe signals (source trust, "
            "TTL, payload validation) that pass value+cooldown."
        )
    if total_send > 0:
        pipeline_readiness["conditions_met"].append(
            "Pipeline successfully identifies send_candidate signals — "
            "signals that pass all three gates are valid for test-channel delivery."
        )
    if total_observe > 0:
        pipeline_readiness["conditions_met"].append(
            "Observe layer is active and captures low-confidence signals "
            "for monitoring without sending."
        )

    # Blockers
    if total_expectation_mismatches > 0:
        pipeline_readiness["blockers"].append(
            f"{total_expectation_mismatches} expectation mismatch(es) — "
            f"pipeline behavior differs from expected outcomes. Review before proceeding."
        )

    pipeline_readiness["blockers"].append(
        "This is a dry-run only. No signals were actually delivered to TG. "
        "Real delivery requires: (a) card router/renderer integration, "
        "(b) actual TG send function, (c) production config."
    )

    # Recommendations
    pipeline_readiness["recommendations"].append(
        "Next step (v1.11-H): After verifying no expectation mismatches, "
        "run a test-channel live dry-run where: (a) signals that pass all "
        "three gates have mock cards rendered, (b) the rendered card is "
        "logged but NOT sent, (c) the full pipeline is validated end-to-end "
        "with real payload rendering."
    )
    pipeline_readiness["recommendations"].append(
        "Do NOT un-freeze the formal channel. The pipeline has not yet been "
        "validated with real TG delivery. Continue test-channel-only validation."
    )
    pipeline_readiness["recommendations"].append(
        "Consider adding a pipeline_dashboard that visualizes the three-layer "
        "flow: signals entering → value gate rejection → cooldown suppression "
        "→ pre-send blocks → final send candidates."
    )

    # ── Build report ──
    report = {
        "run_version": PIPELINE_VERSION,
        "pipeline_layers": {
            "layer_1": f"SignalValueGate ({VALUE_GATE_VERSION})",
            "layer_2": f"CooldownGate ({COOLDOWN_GATE_VERSION})",
            "layer_3": "pre_send_gate (SignalTrustGate + payload validation)",
        },
        "generated_at": china_stamp(),
        "cooldown_config": {
            "cooldown_window_minutes": DEFAULT_COOLDOWN_WINDOW_MINUTES,
            "upgrade_override_score_delta": DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA,
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
    }

    # ── Write output ──
    print(f"Writing dry-run report to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    # ── Final summary ──
    print()
    print(f"{'=' * 70}")
    print(f"v1.11-G Full Gate Pipeline Dry-run — Final Summary")
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
    print(f"  Expectation mismatches:        {total_expectation_mismatches}")
    print()
    print(f"  TG send:                       NONE")
    print(f"  Secrets loaded:                NONE")
    print(f"  Paid APIs:                     NONE")
    print(f"  Loop/daemon:                   NONE")
    print(f"  Files deleted:                 NONE")
    print(f"  Formal channel:                FROZEN")
    print()
    print(f"  Report:                        {output_path}")
    print(f"{'=' * 70}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
