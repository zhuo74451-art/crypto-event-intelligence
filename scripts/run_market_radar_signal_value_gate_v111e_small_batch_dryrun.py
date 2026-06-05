"""Market Radar v1.11-E — Small Batch Live-like SignalValueGate Dry-run

Runs 5 small-batch (3–5 signals each) live-like scenarios through the
v1.11-D calibrated SignalValueGate to verify:

  1. allow / observe / block distribution in realistic small batches
     (v1.11-D used 15-signal replay; real production batches are 3–5).
  2. Whether multi_asset_sync still over-generates in small batches
     (needs >=3 real same-direction assets; may not fire at all).
  3. Whether observe layer triggers correctly when field data is incomplete.
  4. Whether same-asset cooldown is needed (demonstrated, not implemented).
  5. Readiness assessment for pre_send_gate integration.

No TG send, no formal channel, no secrets, no paid APIs, no loop/daemon.
No pre_send_gate integration.

Usage:
    python scripts/run_market_radar_signal_value_gate_v111e_small_batch_dryrun.py
    python scripts/run_market_radar_signal_value_gate_v111e_small_batch_dryrun.py --output results/custom.json

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
    _is_fixture,
    GATE_VERSION,
)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Market Radar v1.11-E — Small Batch Live-like SignalValueGate Dry-run"
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "market_radar_v111e_small_batch_dryrun_result.json"),
        help="Output path for dry-run result JSON",
    )
    return parser.parse_args()


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


# ── Small-batch scenario definitions ──────────────────────────────────────────
#
# Each scenario represents a realistic production-like batch of 3–5 signals.
# The signals are designed to probe specific gate behaviors in small batches
# (unlike v1.11-D which used a single 15-signal mega-batch).

def _build_scenarios() -> list[dict]:
    """Build 5 small-batch scenarios with distinct test objectives.

    Returns a list of scenario dicts, each with:
      - scenario_id: str
      - scenario_name: str
      - objective: str — what this scenario is testing
      - signals: list[dict] — the signals in this batch
    """

    scenarios: list[dict] = []

    # ── Batch A: Baseline — well-confirmed signals ─────────────────────────
    # All 3 signals have price + OI + volume triple confirmation.
    # This is the "happy path" — represents a normal down day with good data.
    # With 3 real down assets, multi_asset_sync is AT the threshold (>=3).
    scenarios.append({
        "scenario_id": "A",
        "scenario_name": "Baseline — Well-Confirmed Signals",
        "objective": (
            "Verify that 3 well-confirmed signals all pass as allow. "
            "Tests multi_asset_sync at the exact threshold (3 real assets). "
            "This is the expected normal-operation baseline."
        ),
        "batch_size": 3,
        "signals": [
            {
                "asset": "BTC",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -5.54,
                "open_interest": 1_826_000_000,
                "volume": 6_345_000_000,
                "funding": None,
                "trigger_reason": "BTC 24h 跌幅 5.54% — 大盘领跌",
                "note": "Real signal from v1.10-F matrix send (msg 2252)",
            },
            {
                "asset": "SOL",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -7.24,
                "open_interest": 278_000_000,
                "volume": 527_000_000,
                "funding": 0.0,
                "trigger_reason": "SOL 24h 跌幅 7.24% — 主流资产领跌",
                "note": "Real signal from v1.10-B single card send (msg 2239)",
            },
            {
                "asset": "ARB",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -6.96,
                "open_interest": 4_682_600,
                "volume": 4_932_100,
                "funding": 0.0,
                "trigger_reason": "ARB 24h 跌幅 6.96% — 小市值跟跌",
                "note": "Real signal from v1.10-E gate-protected send (msg 2245)",
            },
        ],
    })

    # ── Batch B: Mixed confirmation — observe layer should fire ────────────
    # 3 signals: 1 well-confirmed, 1 price-only (missing vol), 1 no price hit.
    # With only 2 real assets in same direction, multi_asset_sync won't fire.
    # This tests whether observe fires without the multi_asset_sync "crutch".
    scenarios.append({
        "scenario_id": "B",
        "scenario_name": "Mixed Confirmation — Observe Layer Test",
        "objective": (
            "Verify that signals with incomplete field data correctly route to "
            "observe when multi_asset_sync cannot fire (only 2 same-direction "
            "real assets). Tests the gate WITHOUT the large-batch multi_asset "
            "crutch seen in v1.11-D."
        ),
        "batch_size": 3,
        "signals": [
            {
                "asset": "SUI",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -5.83,
                "open_interest": 28_000_000,
                "volume": 21_500_000,
                "funding": 0.0,
                "trigger_reason": "SUI 24h 跌幅 5.83% — OI/volume 可确认",
                "note": "Well-confirmed: price + OI + volume → expect allow",
            },
            {
                "asset": "ETH",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -7.50,
                "open_interest": None,
                "volume": None,
                "funding": None,
                "trigger_reason": "ETH 24h 跌幅 7.50% — OI/volume 数据延迟缺失",
                "note": "Strong price but ALL fields missing → expect observe",
            },
            {
                "asset": "DOT",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -4.50,
                "open_interest": 120_000_000,
                "volume": None,
                "funding": None,
                "trigger_reason": "DOT 24h 跌幅 4.50% — 未达 5% 阈值",
                "note": "Price below threshold, has OI → expect block (price not hit)",
            },
        ],
    })

    # ── Batch C: Multi-asset at boundary + fixture exclusion ───────────────
    # 4 signals: 3 real down + 1 fixture up.
    # The 3 real down signals put multi_asset_sync right at threshold.
    # The fixture up signal is opposite direction → excluded from down count.
    # Tests: (a) multi fires for real signals, (b) fixture excluded correctly,
    # (c) fixture signal gets its own evaluation.
    scenarios.append({
        "scenario_id": "C",
        "scenario_name": "Multi-Asset Boundary + Fixture Exclusion",
        "objective": (
            "Verify multi_asset_sync at threshold (3 real down + 1 fixture up). "
            "Fixture should NOT count toward same-direction tally. The 3 real "
            "down signals should get multi_asset_sync backing; the fixture up "
            "signal should be evaluated independently."
        ),
        "batch_size": 4,
        "signals": [
            {
                "asset": "SOL",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -6.80,
                "open_interest": 275_000_000,
                "volume": 530_000_000,
                "funding": 0.0,
                "trigger_reason": "SOL 24h 跌幅 6.80% — 三重确认",
                "note": "Real, well-confirmed → expect allow",
            },
            {
                "asset": "SUI",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -5.30,
                "open_interest": 28_000_000,
                "volume": None,
                "funding": None,
                "trigger_reason": "SUI 24h 跌幅 5.30% — 缺少 volume",
                "note": "Real, price+OI, no vol → expect allow (has OI confirmation)",
            },
            {
                "asset": "ARB",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -5.10,
                "open_interest": 4_700_000,
                "volume": None,
                "funding": None,
                "trigger_reason": "ARB 24h 跌幅 5.10% — 刚好过线, 缺 volume",
                "note": "Real, price barely hit, OI only → expect allow (has OI confirmation)",
            },
            {
                "asset": "HYPE",
                "signal_type": "onchain_position",
                "source_type": "fixture",
                "is_fixture": True,
                "price_change_pct": 15.00,
                "open_interest": 450_000_000,
                "volume": 890_000_000,
                "funding": None,
                "trigger_reason": "HYPE +15% onchain position — fixture 类型",
                "note": "Fixture, opposite direction, triple confirm → expect allow (fixture warning)",
            },
        ],
    })

    # ── Batch D: Same-asset repeat — cooldown demonstration ────────────────
    # 5 signals: ARB appears twice within a short window.
    # SignalValueGate does NOT implement cooldown — both ARB signals will pass.
    # This batch demonstrates WHY cooldown is needed as a separate layer.
    scenarios.append({
        "scenario_id": "D",
        "scenario_name": "Same-Asset Repeat — Cooldown Gap Demonstration",
        "objective": (
            "Demonstrate that SignalValueGate correctly evaluates each signal "
            "independently but cannot detect same-asset repeats. ARB appears "
            "twice — both will pass the gate. This proves cooldown must be "
            "a separate layer (pre_send_gate or cooldown module), not inside "
            "SignalValueGate."
        ),
        "batch_size": 5,
        "signals": [
            {
                "asset": "ARB",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -7.55,
                "open_interest": 4_656_700,
                "volume": 4_942_400,
                "funding": 0.0,
                "trigger_reason": "ARB 24h 跌幅 7.55% — 第 1 次触发 (T+0min)",
                "note": "First occurrence — gate should allow (triple confirmation)",
                "occurrence_index": 1,
                "minutes_since_first": 0,
            },
            {
                "asset": "ARB",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -7.82,
                "open_interest": 4_612_000,
                "volume": 4_955_000,
                "funding": 0.0,
                "trigger_reason": "ARB 24h 跌幅 7.82% — 第 2 次触发 (T+10min)",
                "note": "Second occurrence, 10 min later — gate will STILL allow (no cooldown logic)",
                "occurrence_index": 2,
                "minutes_since_first": 10,
            },
            {
                "asset": "BTC",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -5.50,
                "open_interest": 1_830_000_000,
                "volume": 6_400_000_000,
                "funding": None,
                "trigger_reason": "BTC 24h 跌幅 5.50% — 大盘确认",
                "note": "Context signal — provides multi-asset sync backing",
            },
            {
                "asset": "SUI",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -6.10,
                "open_interest": 27_800_000,
                "volume": 21_100_000,
                "funding": 0.0,
                "trigger_reason": "SUI 24h 跌幅 6.10% — 板块共振",
                "note": "Context signal — provides multi-asset sync backing",
            },
            {
                "asset": "SOL",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -6.80,
                "open_interest": 278_000_000,
                "volume": 530_000_000,
                "funding": 0.0,
                "trigger_reason": "SOL 24h 跌幅 6.80% — 主流共振",
                "note": "Context signal — provides multi-asset sync backing",
            },
        ],
    })

    # ── Batch E: Observe-dominant edge batch ───────────────────────────────
    # 5 signals: mostly weak or incomplete. Designed to produce more observe
    # and block than allow — tests the gate at its most discriminating.
    scenarios.append({
        "scenario_id": "E",
        "scenario_name": "Observe-Dominant — Low-Quality Signal Day",
        "objective": (
            "Simulate a day with weak/incomplete signals: strong price without "
            "confirmation, borderline prices, missing fields. Verify that the "
            "gate correctly routes these to observe/block rather than allow. "
            "This tests the gate's ability to suppress '行情播报型噪音'."
        ),
        "batch_size": 5,
        "signals": [
            {
                "asset": "ETH",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -7.80,
                "open_interest": None,
                "volume": None,
                "funding": None,
                "trigger_reason": "ETH 跌幅 7.80% — 强价格但所有确认字段缺失",
                "note": "Strong price, zero confirmation → expect observe",
            },
            {
                "asset": "LTC",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -5.50,
                "open_interest": None,
                "volume": None,
                "funding": None,
                "trigger_reason": "LTC 跌幅 5.50% — 价格触发但无确认字段",
                "note": "Price hit, zero confirmation → expect observe",
            },
            {
                "asset": "AVAX",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -6.20,
                "open_interest": None,
                "volume": 155_000_000,
                "funding": None,
                "trigger_reason": "AVAX 跌幅 6.20% — 有 volume 确认",
                "note": "Price + volume confirmation → expect allow",
            },
            {
                "asset": "DOT",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -3.20,
                "open_interest": 200_000_000,
                "volume": None,
                "funding": None,
                "trigger_reason": "DOT 仅跌 3.20% — 未达价格阈值",
                "note": "No price hit, has OI → expect block",
            },
            {
                "asset": "LINK",
                "signal_type": "market_anomaly",
                "source_type": "api",
                "is_fixture": False,
                "price_change_pct": -4.00,
                "open_interest": None,
                "volume": None,
                "funding": None,
                "trigger_reason": "LINK 仅跌 4.00% — 无价格触发, 无任何确认",
                "note": "No price hit, no fields → expect block",
            },
        ],
    })

    return scenarios


# ── Cooldown analysis (post-gate, pre-send layer) ─────────────────────────────

def _analyze_cooldown(scenario: dict, results: list[dict]) -> list[dict]:
    """Detect same-asset repeats within a batch and flag cooldown violations.

    This is NOT part of SignalValueGate. It is a separate analysis to
    demonstrate the need for a cooldown layer. Returns a list of cooldown
    findings, each with:
      - asset: str
      - occurrences: int
      - gate_results: list[str] — gate decisions for each occurrence
      - cooldown_violation: bool — True if same asset appears >= 2 times
      - recommendation: str
    """
    asset_seen: dict[str, list[dict]] = {}
    for i, (sig, res) in enumerate(zip(scenario["signals"], results)):
        asset = sig["asset"]
        if asset not in asset_seen:
            asset_seen[asset] = []
        asset_seen[asset].append({
            "index": i,
            "trigger_reason": sig.get("trigger_reason", ""),
            "gate_decision": res["gate_decision"],
            "occurrence_index": sig.get("occurrence_index"),
            "minutes_since_first": sig.get("minutes_since_first"),
        })

    findings: list[dict] = []
    for asset, occurrences in asset_seen.items():
        if len(occurrences) >= 2:
            decisions = [o["gate_decision"] for o in occurrences]
            all_allowed = all(d == "allow" for d in decisions)
            findings.append({
                "asset": asset,
                "occurrences": len(occurrences),
                "gate_decisions": decisions,
                "all_allowed": all_allowed,
                "cooldown_violation": True,
                "recommendation": (
                    f"{asset} triggered {len(occurrences)} times within batch. "
                    f"Gate allowed all occurrences (no cooldown logic in gate). "
                    f"Recommend: implement in pre_send_gate or cooldown layer — "
                    f"first occurrence passes, subsequent within 10–30 min cooldown "
                    f"window are suppressed unless value_score increases significantly."
                ),
                "details": occurrences,
            })

    return findings


# ── Multi-asset sync small-batch analysis ─────────────────────────────────────

def _analyze_multi_asset_sync_batch(scenario: dict, results: list[dict]) -> dict:
    """Analyze multi_asset_sync behavior in the context of this small batch.

    Key question: does multi_asset_sync fire in small batches, and if so,
    does it contribute to over-allow?
    """
    real_signals = [s for s in scenario["signals"] if not s.get("is_fixture")]
    real_down = [s for s in real_signals if (s.get("price_change_pct") or 0) < 0]
    real_up = [s for s in real_signals if (s.get("price_change_pct") or 0) > 0]

    dominant_dir = "down" if len(real_down) >= len(real_up) else "up"
    dominant_count = max(len(real_down), len(real_up))

    multi_hit_signals = [
        r for r in results if r["factor_hits"].get("multi_asset_sync")
    ]
    multi_used_for_allow = [
        r for r in multi_hit_signals
        if r["gate_decision"] == "allow"
        and "multi_asset_sync" in " ".join(r["reasons"])
    ]

    return {
        "real_signal_count": len(real_signals),
        "fixture_signal_count": len([s for s in scenario["signals"] if s.get("is_fixture")]),
        "same_direction_real_count": dominant_count,
        "dominant_direction": dominant_dir,
        "multi_threshold_met": dominant_count >= 3,
        "multi_asset_sync_triggered_count": len(multi_hit_signals),
        "multi_asset_sync_used_in_allow": len(multi_used_for_allow),
        "multi_contributed_to_over_allow": (
            "low" if not (dominant_count >= 3) else
            "medium" if len(multi_used_for_allow) <= 3 else
            "high"
        ),
        "note": (
            f"Small batch ({len(real_signals)} real, {dominant_count} in dominant direction): "
            f"multi_asset_sync {'FIRES' if dominant_count >= 3 else 'does NOT fire'} "
            f"(threshold is >= 3 real assets). "
            f"{'This prevents multi_asset_sync from inflating allow rate in small batches.' if dominant_count < 3 else 'Multi fires but is backed by OI/volume in most signals.'}"
        ),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    print(f"Market Radar v1.11-E — Small Batch Live-like SignalValueGate Dry-run")
    print(f"Started: {china_stamp()}")
    print(f"Gate version: {GATE_VERSION}")
    print()
    print(f"Objective: Verify SignalValueGate behavior in small (3-5 signal)")
    print(f"batches — closer to real production than the 15-signal v1.11-D replay.")
    print()

    scenarios = _build_scenarios()

    # ── Run all scenarios ──
    all_batch_results: list[dict] = []
    aggregate_allow = 0
    aggregate_observe = 0
    aggregate_block = 0
    total_signals = 0

    for scenario in scenarios:
        sid = scenario["scenario_id"]
        sname = scenario["scenario_name"]
        signals = scenario["signals"]

        print(f"{'─' * 60}")
        print(f"Batch {sid}: {sname} ({len(signals)} signals)")
        print(f"  Objective: {scenario['objective'][:100]}...")
        print()

        # Build context: provide list of signals for multi_asset_sync detection
        # and pre-compute real_same_direction_asset_count to avoid fixture inflation
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

        batch_results: list[dict] = []
        for sig in signals:
            gate_result = evaluate_signal_value(sig, context)

            entry = {
                "asset": sig["asset"],
                "signal_type": sig["signal_type"],
                "source_type": sig["source_type"],
                "is_fixture": sig.get("is_fixture", False),
                "price_change_pct": sig.get("price_change_pct"),
                "open_interest": sig.get("open_interest"),
                "volume": sig.get("volume"),
                "funding": sig.get("funding"),
                "trigger_reason": sig.get("trigger_reason", ""),
                "gate_decision": gate_result["decision"],
                "value_score": gate_result["value_score"],
                "value_tier": gate_result["value_tier"],
                "factor_hits": gate_result["factor_hits"],
                "reasons": gate_result["reasons"],
                "warnings": gate_result["warnings"],
            }
            batch_results.append(entry)

            decision = gate_result["decision"]
            score = gate_result["value_score"]
            asset = sig["asset"]
            fixture_mark = " [F]" if sig.get("is_fixture") else ""
            factors = ", ".join(
                k for k, v in gate_result["factor_hits"].items() if v
            ) or "none"
            print(f"  [{decision.upper():7s}] {asset:6s} score={score:3d} "
                  f"tier={gate_result['value_tier']:6s} "
                  f"hits=[{factors}]{fixture_mark}")

        # Cooldown analysis for this batch
        cooldown_findings = _analyze_cooldown(scenario, batch_results)
        multi_analysis = _analyze_multi_asset_sync_batch(scenario, batch_results)

        # Batch stats
        b_allow = sum(1 for r in batch_results if r["gate_decision"] == "allow")
        b_observe = sum(1 for r in batch_results if r["gate_decision"] == "observe")
        b_block = sum(1 for r in batch_results if r["gate_decision"] == "block")
        b_real = sum(1 for r in batch_results if not r["is_fixture"])

        print()
        print(f"  Batch {sid} summary: allow={b_allow}, observe={b_observe}, "
              f"block={b_block} (real={b_real}, fixture={len(signals) - b_real})")
        print(f"  Multi-asset sync: {multi_analysis['note']}")
        if cooldown_findings:
            for cf in cooldown_findings:
                print(f"  [COOLDOWN] VIOLATION: {cf['asset']} x{cf['occurrences']} "
                      f"- all allowed by gate (cooldown layer needed)")
        print()

        aggregate_allow += b_allow
        aggregate_observe += b_observe
        aggregate_block += b_block
        total_signals += len(signals)

        all_batch_results.append({
            "scenario_id": sid,
            "scenario_name": sname,
            "objective": scenario["objective"],
            "batch_size": len(signals),
            "batch_stats": {
                "allow": b_allow,
                "observe": b_observe,
                "block": b_block,
                "real_count": b_real,
                "fixture_count": len(signals) - b_real,
                "allow_rate_pct": round(b_allow / len(signals) * 100, 1),
                "observe_rate_pct": round(b_observe / len(signals) * 100, 1),
            },
            "multi_asset_sync_analysis": multi_analysis,
            "cooldown_findings": cooldown_findings,
            "signal_results": batch_results,
        })

    # ── Aggregate analysis ──
    print(f"{'=' * 60}")
    print(f"Aggregate Results Across All {len(scenarios)} Batches")
    print(f"{'=' * 60}")
    print(f"  Total signals:     {total_signals}")
    print(f"  Allowed:           {aggregate_allow} ({round(aggregate_allow/total_signals*100, 1)}%)")
    print(f"  Observe:           {aggregate_observe} ({round(aggregate_observe/total_signals*100, 1)}%)")
    print(f"  Blocked:           {aggregate_block} ({round(aggregate_block/total_signals*100, 1)}%)")
    print()

    # ── Key findings ──
    all_signals_real = sum(
        b["batch_stats"]["real_count"] for b in all_batch_results
    )
    all_signals_fixture = total_signals - all_signals_real

    # Count scenarios where multi_asset_sync didn't fire
    batches_without_multi = [
        b for b in all_batch_results
        if not b["multi_asset_sync_analysis"]["multi_threshold_met"]
    ]
    batches_with_multi = [
        b for b in all_batch_results
        if b["multi_asset_sync_analysis"]["multi_threshold_met"]
    ]

    # Count total cooldown violations
    total_cooldown_violations = sum(
        len(b["cooldown_findings"]) for b in all_batch_results
    )

    # Observe layer assessment
    batches_with_observe = [
        b for b in all_batch_results if b["batch_stats"]["observe"] > 0
    ]

    # Decision matrix by scenario
    decision_matrix = {
        b["scenario_id"]: {
            "name": b["scenario_name"],
            "allow": b["batch_stats"]["allow"],
            "observe": b["batch_stats"]["observe"],
            "block": b["batch_stats"]["block"],
            "allow_pct": b["batch_stats"]["allow_rate_pct"],
            "observe_pct": b["batch_stats"]["observe_rate_pct"],
            "multi_fired": b["multi_asset_sync_analysis"]["multi_threshold_met"],
            "has_cooldown_issue": len(b["cooldown_findings"]) > 0,
        }
        for b in all_batch_results
    }

    allow_rate_aggregate = round(aggregate_allow / total_signals * 100, 1)
    observe_rate_aggregate = round(aggregate_observe / total_signals * 100, 1)

    # ── Assessment ──
    # Compare with v1.11-D metrics
    # v1.11-D: allow=13/15 (87%), observe=0/15 (0%), block=2/15 (13%)
    allow_delta_vs_v111d = round(allow_rate_aggregate - 86.7, 1)
    observe_delta_vs_v111d = round(observe_rate_aggregate - 0.0, 1)

    key_findings: list[str] = []

    key_findings.append(
        f"Allow rate: {allow_rate_aggregate}% ({aggregate_allow}/{total_signals}) "
        f"vs v1.11-D 86.7% (13/15) — Δ{allow_delta_vs_v111d:+.1f}%. "
        f"Small batches produce a more realistic distribution because "
        f"multi_asset_sync does not fire in {len(batches_without_multi)}/"
        f"{len(scenarios)} scenarios."
    )

    if observe_rate_aggregate > 0:
        key_findings.append(
            f"Observe layer ACTIVATED: {observe_rate_aggregate}% ({aggregate_observe}/{total_signals}). "
            f"v1.11-D had 0% observe — the large batch inflated multi_asset_sync "
            f"and suppressed observe. Small batches correctly route incomplete "
            f"signals to observe. Observe triggered in {len(batches_with_observe)}/"
            f"{len(scenarios)} batches."
        )
    else:
        key_findings.append(
            f"Observe layer still at 0% — all signals with price movement had "
            f"at least one confirmation factor. This is plausible for real "
            f"production signals with good field quality."
        )

    key_findings.append(
        f"Multi_asset_sync: fired in {len(batches_with_multi)}/{len(scenarios)} "
        f"batches (requires >= 3 real same-direction assets). In the remaining "
        f"{len(batches_without_multi)} batches, only 2 or fewer real assets shared "
        f"direction — multi_asset_sync could not fire. This is the CORRECT behavior "
        f"for small batches."
    )

    key_findings.append(
        f"Cooldown: {total_cooldown_violations} same-asset repeat scenario(s) "
        f"detected. SignalValueGate correctly allows both occurrences (no cooldown "
        f"logic in gate by design). This CONFIRMS cooldown must be a separate layer "
        f"in pre_send_gate or a dedicated cooldown module."
    )

    # Pre-send gate readiness
    pre_send_gate_readiness = {
        "ready": False,
        "blockers": [],
        "conditions": [],
    }

    if observe_rate_aggregate > 0:
        pre_send_gate_readiness["conditions"].append(
            "Observe layer fires correctly in small batches — gate is "
            "discriminating enough to be useful as a pre-filter."
        )
    else:
        pre_send_gate_readiness["blockers"].append(
            "Observe layer did not fire — need more evidence that gate can "
            "discriminate low-value signals before connecting to send pipeline."
        )

    if total_cooldown_violations > 0:
        pre_send_gate_readiness["blockers"].append(
            "Cooldown not implemented — same-asset repeats would flood "
            "test channel. Implement cooldown layer before pre_send_gate."
        )

    if allow_rate_aggregate > 70:
        pre_send_gate_readiness["blockers"].append(
            f"Allow rate ({allow_rate_aggregate}%) is still high. Consider "
            f"OI/volume delta thresholds to further discriminate."
        )

    pre_send_gate_readiness["conditions"].append(
        "Complete v1.11-E validation with real-time data before deciding."
    )

    if not pre_send_gate_readiness["blockers"]:
        pre_send_gate_readiness["ready"] = True

    key_findings.append(
        f"Pre-send gate readiness: {'READY' if pre_send_gate_readiness['ready'] else 'NOT READY'}. "
        f"Blockers: {len(pre_send_gate_readiness['blockers'])}. "
        f"Conditions: {len(pre_send_gate_readiness['conditions'])}."
    )

    # ── Build report ──
    report = {
        "run_version": "v1.11-E",
        "gate_version": GATE_VERSION,
        "generated_at": china_stamp(),
        "total_scenarios": len(scenarios),
        "total_signals": total_signals,
        "real_signal_count": all_signals_real,
        "fixture_signal_count": all_signals_fixture,
        "aggregate_allow": aggregate_allow,
        "aggregate_observe": aggregate_observe,
        "aggregate_block": aggregate_block,
        "aggregate_allow_rate_pct": allow_rate_aggregate,
        "aggregate_observe_rate_pct": observe_rate_aggregate,
        "allow_rate_delta_vs_v111d_pct": allow_delta_vs_v111d,
        "observe_rate_delta_vs_v111d_pct": observe_delta_vs_v111d,
        "decision_matrix_by_scenario": decision_matrix,
        "batches_with_multi_asset_sync": len(batches_with_multi),
        "batches_without_multi_asset_sync": len(batches_without_multi),
        "cooldown_violations_total": total_cooldown_violations,
        "batches_with_observe_activated": len(batches_with_observe),
        "key_findings": key_findings,
        "pre_send_gate_readiness": pre_send_gate_readiness,
        "scenarios": all_batch_results,
        "security": {
            "tg_send": "NONE",
            "formal_channel": "NONE",
            "secrets_loaded": "NONE",
            "paid_apis": "NONE",
            "loop_daemon_cron": "NONE",
            "files_deleted": "NONE",
            "pre_send_gate_connected": "NONE",
        },
    }

    # ── Write output ──
    print(f"Writing dry-run report to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    # ── Final summary ──
    print()
    print(f"{'=' * 60}")
    print(f"v1.11-E Small Batch Dry-run — Final Summary")
    print(f"{'=' * 60}")
    print(f"  Scenarios:         {len(scenarios)}")
    print(f"  Total signals:     {total_signals} ({all_signals_real} real, {all_signals_fixture} fixture)")
    print(f"  Allow:             {aggregate_allow} ({allow_rate_aggregate}%)")
    print(f"  Observe:           {aggregate_observe} ({observe_rate_aggregate}%)")
    print(f"  Block:             {aggregate_block} ({round(aggregate_block/total_signals*100, 1)}%)")
    print(f"  vs v1.11-D allow:  Δ{allow_delta_vs_v111d:+.1f}%")
    print(f"  vs v1.11-D observe: Δ{observe_delta_vs_v111d:+.1f}%")
    print(f"  Multi fired in:    {len(batches_with_multi)}/{len(scenarios)} batches")
    print(f"  Observe fired in:  {len(batches_with_observe)}/{len(scenarios)} batches")
    print(f"  Cooldown issues:   {total_cooldown_violations}")
    print(f"  Pre-send gate:     {'READY' if pre_send_gate_readiness['ready'] else 'NOT READY'}")
    print()
    print(f"  TG send:           NONE")
    print(f"  Secrets loaded:    NONE")
    print(f"  Paid APIs:         NONE")
    print(f"  Loop/daemon:       NONE")
    print(f"  Files deleted:     NONE")
    print()
    print(f"  Report:            {output_path}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
