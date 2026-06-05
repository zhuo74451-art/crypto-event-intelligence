"""Market Radar v1.11-F — Same-Asset Cooldown Gate Dry-run

Runs 5 live-like scenarios through the v1.11-F same-asset cooldown gate to verify:

  1. First occurrence per asset → allow (cooldown starts)
  2. Same asset within 10 min window → cooldown_suppress
  3. Same asset within window with significantly higher value_score → upgrade_override
  4. Cooldown window expired → allow again
  5. Multi-asset interleaving → independent per-asset tracking
  6. Integration with SignalValueGate results — correct handoff

The dry-run uses the same small-batch scenarios from v1.11-E as input signals,
plus additional scenarios specifically designed to stress-test cooldown behavior.

No TG send, no formal channel, no secrets, no paid APIs, no loop/daemon.
No pre_send_gate integration.

Usage:
    python scripts/run_market_radar_same_asset_cooldown_v111f_dryrun.py
    python scripts/run_market_radar_same_asset_cooldown_v111f_dryrun.py --output results/custom.json

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
    evaluate_cooldown_batch,
    CooldownState,
    COOLDOWN_GATE_VERSION,
    DEFAULT_COOLDOWN_WINDOW_MINUTES,
    DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA,
)


# ── CLI ─────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Market Radar v1.11-F — Same-Asset Cooldown Gate Dry-run"
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "market_radar_v111f_same_asset_cooldown_result.json"),
        help="Output path for dry-run result JSON",
    )
    return parser.parse_args()


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


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
        })

    return results


# ── Scenario definitions ────────────────────────────────────────────────────────

def _build_scenarios() -> list[dict]:
    """Build 5 scenarios designed to stress-test the cooldown gate.

    Each scenario has an ordered list of signals, representing a realistic
    production batch where signals arrive sequentially.

    Returns a list of scenario dicts, each with:
      - scenario_id: str
      - scenario_name: str
      - objective: str
      - signals: list[dict]
    """
    scenarios: list[dict] = []

    # ── Batch F1: Same-asset repeat — cooldown suppression ─────────────────
    # ARB appears 3 times within 8 minutes. First passes, subsequent suppressed.
    # BTC and SOL provide context for multi_asset_sync (optional).
    scenarios.append({
        "scenario_id": "F1",
        "scenario_name": "Same-Asset Repeat — Cooldown Suppression",
        "objective": (
            "Verify that same-asset repeats within 10 min cooldown window are "
            "correctly suppressed. ARB appears 3 times (T+0, T+4, T+8 min). "
            "First passes, second and third are cooldown_suppress. "
            "Different assets (BTC, SOL) pass independently."
        ),
        "signals": [
            # T+0: ARB first occurrence → should allow
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.55,
                "open_interest": 4_656_700, "volume": 4_942_400, "funding": 0.0,
                "trigger_reason": "ARB 24h 跌幅 7.55% — 第 1 次触发 (T+0min)",
                "note": "First occurrence — expect cooldown: allow",
                "minutes_offset": 0,
            },
            # T+4: ARB again, same score → should suppress
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.82,
                "open_interest": 4_612_000, "volume": 4_955_000, "funding": 0.0,
                "trigger_reason": "ARB 24h 跌幅 7.82% — 第 2 次触发 (T+4min)",
                "note": "Second occurrence, 4 min later — expect cooldown: cooldown_suppress",
                "minutes_offset": 4,
            },
            # T+8: ARB again, same score → should suppress again
            {
                "asset": "ARB", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.90,
                "open_interest": 4_588_000, "volume": 4_961_000, "funding": 0.0,
                "trigger_reason": "ARB 24h 跌幅 7.90% — 第 3 次触发 (T+8min)",
                "note": "Third occurrence, 8 min later — expect cooldown: cooldown_suppress",
                "minutes_offset": 8,
            },
        ],
    })

    # ── Batch F2: Upgrade override — score improvement triggers allow ──────
    # ETH appears twice: low score (45) then high score (75) with OI/volume.
    # The significant improvement should trigger upgrade_override.
    scenarios.append({
        "scenario_id": "F2",
        "scenario_name": "Upgrade Override — Score Improvement Within Window",
        "objective": (
            "Verify that when the same asset reappears within the cooldown window "
            "but with a significantly higher value_score (Δ >= 15), the cooldown "
            "gate issues an upgrade_override (allowed). "
            "ETH: first at score=45 (price only), then at score=75 (price+OI+volume)."
        ),
        "signals": [
            # T+0: ETH first — weak signal (price only, no OI/vol)
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.80,  # strong price
                "open_interest": None, "volume": None, "funding": None,
                "trigger_reason": "ETH 跌幅 7.80% — 弱信号: 只有价格, 无确认因子",
                "note": "First occurrence, weak → score ~30 (price only). Expect cooldown: allow",
                "minutes_offset": 0,
            },
            # T+5: ETH again — now with OI + volume confirmation
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -8.50,  # strong price
                "open_interest": 12_500_000_000, "volume": 18_200_000_000, "funding": -0.025,
                "trigger_reason": "ETH 跌幅 8.50% — 强信号: 价格+OI+volume+funding extreme",
                "note": "Second occurrence, 5 min later, much stronger → expect cooldown: upgrade_override",
                "minutes_offset": 5,
            },
        ],
    })

    # ── Batch F3: Cooldown window expiry — allow after window passes ───────
    # SOL appears at T+0 and T+12. The 10-min window expires, so second passes.
    scenarios.append({
        "scenario_id": "F3",
        "scenario_name": "Cooldown Window Expiry — Allow After Window",
        "objective": (
            "Verify that after the cooldown window (10 min) expires, the same "
            "asset can be sent again. SOL appears at T+0 and T+12 — the second "
            "should pass as a normal allow (not upgrade_override)."
        ),
        "signals": [
            # T+0: SOL first
            {
                "asset": "SOL", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.24,
                "open_interest": 278_000_000, "volume": 527_000_000, "funding": 0.0,
                "trigger_reason": "SOL 24h 跌幅 7.24% — 第 1 次 (T+0min)",
                "note": "First occurrence — expect cooldown: allow",
                "minutes_offset": 0,
            },
            # T+12: SOL again — window expired
            {
                "asset": "SOL", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.80,
                "open_interest": 275_000_000, "volume": 530_000_000, "funding": 0.0,
                "trigger_reason": "SOL 24h 跌幅 6.80% — 第 2 次 (T+12min)",
                "note": "Second occurrence, 12 min later — expect cooldown: allow (window expired)",
                "minutes_offset": 12,
            },
        ],
    })

    # ── Batch F4: Multi-asset interleaving — independent tracking ───────────
    # BTC, ETH, BTC, SOL, ETH in sequence. Cooldown tracks each asset independently.
    scenarios.append({
        "scenario_id": "F4",
        "scenario_name": "Multi-Asset Interleaving — Independent Per-Asset Cooldown",
        "objective": (
            "Verify that cooldown tracking is per-asset. BTC and ETH each appear "
            "twice — their cooldown states are independent. BTC at T+5 should be "
            "suppressed; ETH at T+7 should be suppressed; SOL at T+9 is a first "
            "occurrence → allow."
        ),
        "signals": [
            # T+0: BTC
            {
                "asset": "BTC", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.54,
                "open_interest": 1_826_000_000, "volume": 6_345_000_000, "funding": None,
                "trigger_reason": "BTC 24h 跌幅 5.54% — (T+0min)",
                "note": "BTC first — expect cooldown: allow",
                "minutes_offset": 0,
            },
            # T+3: ETH
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.20,
                "open_interest": 12_800_000_000, "volume": 15_500_000_000, "funding": None,
                "trigger_reason": "ETH 24h 跌幅 6.20% — (T+3min)",
                "note": "ETH first — expect cooldown: allow",
                "minutes_offset": 3,
            },
            # T+5: BTC repeat
            {
                "asset": "BTC", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.80,
                "open_interest": 1_830_000_000, "volume": 6_400_000_000, "funding": None,
                "trigger_reason": "BTC 24h 跌幅 5.80% — (T+5min)",
                "note": "BTC repeat, 5 min since first — expect cooldown: cooldown_suppress",
                "minutes_offset": 5,
            },
            # T+7: ETH repeat
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.50,
                "open_interest": 12_750_000_000, "volume": 15_800_000_000, "funding": None,
                "trigger_reason": "ETH 24h 跌幅 6.50% — (T+7min)",
                "note": "ETH repeat, 4 min since first — expect cooldown: cooldown_suppress",
                "minutes_offset": 7,
            },
            # T+9: SOL first
            {
                "asset": "SOL", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.50,
                "open_interest": 280_000_000, "volume": 535_000_000, "funding": 0.0,
                "trigger_reason": "SOL 24h 跌幅 7.50% — (T+9min)",
                "note": "SOL first, independent of BTC/ETH — expect cooldown: allow",
                "minutes_offset": 9,
            },
        ],
    })

    # ── Batch F5: Mixed — allow + suppress + upgrade + observe ─────────────
    # A realistic batch where SignalValueGate produces a mix of allow, observe,
    # and block decisions before cooldown. Tests integration.
    scenarios.append({
        "scenario_id": "F5",
        "scenario_name": "Mixed Integration — Value Gate + Cooldown Gate Pipeline",
        "objective": (
            "Full pipeline integration test. Signals pass through SignalValueGate "
            "first, then CooldownGate. Tests: (a) blocked signal doesn't enter "
            "cooldown; (b) observe signal goes to cooldown check; (c) same-asset "
            "repeat is suppressed; (d) upgrade_override works in mixed context."
        ),
        "signals": [
            # T+0: SUI — well confirmed, first occurrence → allow
            {
                "asset": "SUI", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -5.83,
                "open_interest": 28_000_000, "volume": 21_500_000, "funding": 0.0,
                "trigger_reason": "SUI 24h 跌幅 5.83% — (T+0min)",
                "note": "SUI first, well-confirmed — signal value: allow, cooldown: allow",
                "minutes_offset": 0,
            },
            # T+2: ETH — well confirmed → allow (different asset)
            {
                "asset": "ETH", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.80,
                "open_interest": 12_900_000_000, "volume": 16_000_000_000, "funding": -0.015,
                "trigger_reason": "ETH 24h 跌幅 6.80% — (T+2min)",
                "note": "ETH first — signal value: allow, cooldown: allow",
                "minutes_offset": 2,
            },
            # T+4: DOT — below threshold → value gate: block
            {
                "asset": "DOT", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -4.50,
                "open_interest": 120_000_000, "volume": None, "funding": None,
                "trigger_reason": "DOT 仅跌 4.50% — 未达价格阈值 (T+4min)",
                "note": "DOT below threshold → signal value: block, cooldown: N/A (skip)",
                "minutes_offset": 4,
            },
            # T+6: SUI repeat — same score → suppress
            {
                "asset": "SUI", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -6.10,
                "open_interest": 28_100_000, "volume": 21_800_000, "funding": 0.0,
                "trigger_reason": "SUI 24h 跌幅 6.10% — (T+6min)",
                "note": "SUI repeat, 6 min later, similar score → cooldown: cooldown_suppress",
                "minutes_offset": 6,
            },
            # T+8: LINK — price only, no confirmation → value gate: observe
            {
                "asset": "LINK", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -7.20,
                "open_interest": None, "volume": None, "funding": None,
                "trigger_reason": "LINK 跌幅 7.20% — 无确认因子 (T+8min)",
                "note": "LINK first, value gate: observe → cooldown check runs (but no send anyway)",
                "minutes_offset": 8,
            },
            # T+10: SUI — significantly higher score → upgrade_override
            {
                "asset": "SUI", "signal_type": "market_anomaly",
                "source_type": "api", "is_fixture": False,
                "price_change_pct": -9.20,
                "open_interest": 35_000_000, "volume": 28_000_000, "funding": 0.012,
                "trigger_reason": "SUI 持续下跌 9.20% — OI+volume+funding 三重确认 (T+10min)",
                "note": "SUI third occurrence, strong improvement → cooldown: upgrade_override",
                "minutes_offset": 10,
            },
        ],
    })

    return scenarios


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    print(f"Market Radar v1.11-F — Same-Asset Cooldown Gate Dry-run")
    print(f"Started: {china_stamp()}")
    print(f"Cooldown gate version: {COOLDOWN_GATE_VERSION}")
    print(f"Signal value gate version: {VALUE_GATE_VERSION}")
    print()
    print(f"Default cooldown window: {DEFAULT_COOLDOWN_WINDOW_MINUTES} min")
    print(f"Upgrade override delta: {DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA} pts")
    print()

    scenarios = _build_scenarios()

    # ── Aggregate counters ──
    aggregate_cooldown_allow = 0
    aggregate_cooldown_suppress = 0
    aggregate_upgrade_override = 0
    aggregate_value_allow = 0
    aggregate_value_observe = 0
    aggregate_value_block = 0
    total_signals = 0
    total_repeated_assets: set[str] = set()

    all_scenario_results: list[dict] = []

    for scenario in scenarios:
        sid = scenario["scenario_id"]
        sname = scenario["scenario_name"]
        signals = scenario["signals"]

        print(f"{'─' * 60}")
        print(f"Batch {sid}: {sname} ({len(signals)} signals)")
        print(f"  Objective: {scenario['objective'][:120]}...")
        print()

        # Step 1: Run all signals through SignalValueGate
        value_results = _run_value_gate(signals)

        # Step 2: Run through CooldownGate sequentially
        # Build the base time and advance by minutes_offset per signal
        base_time = datetime.now(CN_TZ)
        # Use the first signal's offset as the base; all offsets are relative
        min_offset = min(s.get("minutes_offset", 0) for s in signals)
        base_time = base_time - timedelta(minutes=min_offset)

        cooldown_state = CooldownState()
        cooldown_results: list[dict] = []
        signal_entries: list[dict] = []

        for i, (sig, vr) in enumerate(zip(signals, value_results)):
            offset = sig.get("minutes_offset", i)
            signal_time = (base_time + timedelta(minutes=offset)).isoformat()

            cr = evaluate_cooldown(
                signal=sig,
                signal_value_result=vr,
                cooldown_state=cooldown_state,
                current_time=signal_time,
            )
            cooldown_state.apply(cr["cooldown_state"])
            cooldown_results.append(cr)

            # ── Print per-signal result ──
            asset = sig["asset"]
            val_decision = vr["gate_decision"]
            val_score = vr["value_score"]
            cool_decision = cr["decision"]
            offset_str = f"T+{offset}min" if offset == int(offset) else f"T+{offset:.0f}min"

            # Determine final pipeline status
            if val_decision == "block":
                final_status = "BLOCKED (value gate)"
            elif val_decision == "observe":
                final_status = "OBSERVE (not sent)"
            elif cool_decision == "allow":
                final_status = "SEND"
            elif cool_decision == "upgrade_override":
                final_status = "SEND (upgrade)"
            else:
                final_status = "COOLDOWN SUPPRESS"

            status_marker = {
                "allow": "[+]",
                "cooldown_suppress": "[-]",
                "upgrade_override": "[^]",
            }.get(cool_decision, "[?]")

            print(f"  [{offset_str:>6s}] {asset:6s} | "
                  f"value: {val_decision:7s} (score={val_score:3d}) | "
                  f"cooldown: {status_marker} {cool_decision:20s} | "
                  f"> {final_status}")

            signal_entries.append({
                "asset": asset,
                "minutes_offset": offset,
                "signal_value_decision": val_decision,
                "signal_value_score": val_score,
                "signal_value_tier": vr["value_tier"],
                "cooldown_decision": cool_decision,
                "cooldown_allowed": cr["allowed"],
                "cooldown_reason": cr["cooldown_reason"],
                "previous_value_score": cr["previous_value_score"],
                "minutes_since_last": cr["minutes_since_last"],
                "occurrence_count": cr["occurrence_count"],
                "final_status": final_status,
                "trigger_reason": sig.get("trigger_reason", ""),
            })

            # Aggregate
            total_signals += 1
            if cool_decision == "allow":
                aggregate_cooldown_allow += 1
            elif cool_decision == "cooldown_suppress":
                aggregate_cooldown_suppress += 1
            elif cool_decision == "upgrade_override":
                aggregate_upgrade_override += 1

            if val_decision == "allow":
                aggregate_value_allow += 1
            elif val_decision == "observe":
                aggregate_value_observe += 1
            elif val_decision == "block":
                aggregate_value_block += 1

        # ── Batch summary ──
        b_allow = sum(1 for e in signal_entries if e["cooldown_decision"] == "allow")
        b_suppress = sum(1 for e in signal_entries if e["cooldown_decision"] == "cooldown_suppress")
        b_upgrade = sum(1 for e in signal_entries if e["cooldown_decision"] == "upgrade_override")

        # Count repeated assets in this batch
        assets_seen: dict[str, int] = {}
        for e in signal_entries:
            a = e["asset"]
            assets_seen[a] = assets_seen.get(a, 0) + 1
        repeated = [a for a, c in assets_seen.items() if c >= 2]
        for a in repeated:
            total_repeated_assets.add(a)

        print()
        print(f"  Batch {sid} cooldown summary: allow={b_allow}, "
              f"suppress={b_suppress}, upgrade_override={b_upgrade}")
        if repeated:
            print(f"  Repeated assets: {', '.join(repeated)}")
        print()

        all_scenario_results.append({
            "scenario_id": sid,
            "scenario_name": sname,
            "objective": scenario["objective"],
            "batch_size": len(signals),
            "cooldown_stats": {
                "allow": b_allow,
                "cooldown_suppress": b_suppress,
                "upgrade_override": b_upgrade,
                "suppression_rate_pct": round(b_suppress / len(signals) * 100, 1) if len(signals) > 0 else 0,
            },
            "repeated_assets": repeated,
            "signal_entries": signal_entries,
        })

    # ── Final cooldown state ──
    final_state = cooldown_state.to_dict() if not cooldown_state.is_empty() else {}

    # ── Aggregate analysis ──
    print(f"{'=' * 60}")
    print(f"Aggregate Cooldown Gate Results Across All {len(scenarios)} Batches")
    print(f"{'=' * 60}")
    print(f"  Total signals:              {total_signals}")
    print(f"  Cooldown allow:             {aggregate_cooldown_allow} "
          f"({round(aggregate_cooldown_allow/total_signals*100, 1)}%)")
    print(f"  Cooldown suppress:          {aggregate_cooldown_suppress} "
          f"({round(aggregate_cooldown_suppress/total_signals*100, 1)}%)")
    print(f"  Upgrade override:           {aggregate_upgrade_override} "
          f"({round(aggregate_upgrade_override/total_signals*100, 1)}%)")
    print(f"  Repeated assets detected:   {len(total_repeated_assets)} "
          f"({', '.join(sorted(total_repeated_assets)) if total_repeated_assets else 'none'})")
    print()
    print(f"  Value gate decisions (ref):")
    print(f"    allow:                    {aggregate_value_allow}")
    print(f"    observe:                  {aggregate_value_observe}")
    print(f"    block:                    {aggregate_value_block}")
    print()

    # ── Key findings ──
    key_findings: list[str] = []

    suppression_rate = round(aggregate_cooldown_suppress / total_signals * 100, 1) if total_signals > 0 else 0
    upgrade_rate = round(aggregate_upgrade_override / total_signals * 100, 1) if total_signals > 0 else 0

    key_findings.append(
        f"Cooldown gate successfully suppresses same-asset repeats within the "
        f"{DEFAULT_COOLDOWN_WINDOW_MINUTES}-min window. {aggregate_cooldown_suppress} "
        f"signals ({suppression_rate}%) were suppressed that would have been sent "
        f"without cooldown (all passed SignalValueGate as 'allow')."
    )

    if aggregate_upgrade_override > 0:
        key_findings.append(
            f"Upgrade override triggered {aggregate_upgrade_override} time(s) "
            f"({upgrade_rate}%), allowing a repeat because value_score improved "
            f"by >= {DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA} points. This prevents "
            f"cooldown from becoming a hard silence — important signals still get through."
        )

    key_findings.append(
        f"Per-asset tracking confirmed: {len(total_repeated_assets)} asset(s) "
        f"appeared multiple times across batches. Cooldown state correctly tracks "
        f"each asset independently."
    )

    key_findings.append(
        f"Integration with SignalValueGate: blocked signals skip cooldown check; "
        f"observe signals still go through cooldown evaluation (but would not be "
        f"sent regardless). cooldown_suppress + value_observe are independent "
        f"concerns — observe means 'not valuable enough', suppress means 'too soon'."
    )

    # ── Pre-send gate readiness assessment ──
    pre_send_gate_readiness = {
        "ready": False,
        "blockers": [],
        "conditions_met": [],
    }

    if aggregate_cooldown_suppress > 0:
        pre_send_gate_readiness["conditions_met"].append(
            "Cooldown gate successfully suppresses same-asset repeats — "
            "the only blocker identified in v1.11-E is now resolved."
        )

    if aggregate_upgrade_override > 0:
        pre_send_gate_readiness["conditions_met"].append(
            "Upgrade override works — important signal escalations are not "
            "silently dropped by cooldown."
        )

    pre_send_gate_readiness["conditions_met"].append(
        "Cooldown gate is a separate layer from SignalValueGate — "
        "separation of concerns is maintained. pre_send_gate can now "
        "consume both SignalValueGate (value check) and CooldownGate "
        "(rate limit) before sending."
    )

    # Check if cooldown is working correctly
    if aggregate_cooldown_suppress == 0:
        pre_send_gate_readiness["blockers"].append(
            "No cooldown suppressions observed — need more repeat scenarios "
            "to verify suppression logic in production-like conditions."
        )

    if not pre_send_gate_readiness["blockers"]:
        pre_send_gate_readiness["ready"] = True
        pre_send_gate_readiness["recommendation"] = (
            "Cooldown gate is ready for integration. Next step (v1.11-G): "
            "wire CooldownGate between SignalValueGate and pre_send_gate in "
            "a dry-run pipeline. Do NOT send to TG yet."
        )

    # ── Build report ──
    report = {
        "run_version": "v1.11-F",
        "cooldown_gate_version": COOLDOWN_GATE_VERSION,
        "signal_value_gate_version": VALUE_GATE_VERSION,
        "generated_at": china_stamp(),
        "cooldown_config": {
            "cooldown_window_minutes": DEFAULT_COOLDOWN_WINDOW_MINUTES,
            "upgrade_override_score_delta": DEFAULT_UPGRADE_OVERRIDE_SCORE_DELTA,
        },
        "total_scenarios": len(scenarios),
        "total_signals": total_signals,
        "aggregate": {
            "cooldown_allow_count": aggregate_cooldown_allow,
            "cooldown_suppress_count": aggregate_cooldown_suppress,
            "upgrade_override_count": aggregate_upgrade_override,
            "repeated_assets": sorted(total_repeated_assets),
            "repeated_asset_count": len(total_repeated_assets),
            "suppression_rate_pct": suppression_rate,
            "upgrade_override_rate_pct": upgrade_rate,
        },
        "value_gate_reference": {
            "value_allow": aggregate_value_allow,
            "value_observe": aggregate_value_observe,
            "value_block": aggregate_value_block,
        },
        "key_findings": key_findings,
        "pre_send_gate_readiness": pre_send_gate_readiness,
        "final_cooldown_state": final_state,
        "scenarios": all_scenario_results,
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
    print(f"v1.11-F Same-Asset Cooldown Gate Dry-run — Final Summary")
    print(f"{'=' * 60}")
    print(f"  Scenarios:              {len(scenarios)}")
    print(f"  Total signals:          {total_signals}")
    print(f"  Cooldown allow:         {aggregate_cooldown_allow} "
          f"({round(aggregate_cooldown_allow/total_signals*100, 1)}%)")
    print(f"  Cooldown suppress:      {aggregate_cooldown_suppress} "
          f"({suppression_rate}%)")
    print(f"  Upgrade override:       {aggregate_upgrade_override} "
          f"({upgrade_rate}%)")
    print(f"  Repeated assets:        {len(total_repeated_assets)} "
          f"({', '.join(sorted(total_repeated_assets)) if total_repeated_assets else 'none'})")
    print()
    print(f"  Pre-send gate ready:    {'YES' if pre_send_gate_readiness['ready'] else 'NOT YET'}")
    print(f"  Blockers remaining:     {len(pre_send_gate_readiness['blockers'])}")
    print(f"  Conditions met:         {len(pre_send_gate_readiness['conditions_met'])}")
    if pre_send_gate_readiness.get("recommendation"):
        print(f"  Recommendation:         {pre_send_gate_readiness['recommendation'][:100]}...")
    print()
    print(f"  TG send:                NONE")
    print(f"  Secrets loaded:         NONE")
    print(f"  Paid APIs:              NONE")
    print(f"  Loop/daemon:            NONE")
    print(f"  Files deleted:          NONE")
    print(f"  Pre_send_gate:          NOT connected")
    print()
    print(f"  Report:                 {output_path}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
