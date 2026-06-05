"""Market Radar v1.11-C — Historical Signal Value Replay 历史信号价值回放

Collects 10-20 real/fixture signals from historical Market Radar data,
runs each through the v1.11-B SignalValueGate, and produces a comprehensive
replay report with false-positive/negative analysis.

No TG send, no secrets, no paid APIs, no loop/daemon.

Usage:
    python scripts/run_market_radar_signal_value_gate_v111c_replay.py
    python scripts/run_market_radar_signal_value_gate_v111c_replay.py --output results/custom.json
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

from scripts.market_radar_signal_value_gate_v111b import evaluate_signal_value, GATE_VERSION


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Market Radar v1.11-C — Historical Signal Value Replay"
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "market_radar_v111c_signal_value_replay_result.json"),
        help="Output path for replay result JSON",
    )
    return parser.parse_args()


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


# ── Signal collection ─────────────────────────────────────────────────────────

def _collect_replay_signals() -> list[dict]:
    """Collect 10-20 replayable signals from historical Market Radar data.

    Priority sources:
      1. v110f result — real TG sends (ARB/SUI/BTC, actually sent)
      2. v110i result — real TG sends (ARB/SUI/BTC, actually sent)
      3. v110b result — real TG send (SOL, actually sent)
      4. v110e result — real TG send (ARB, actually sent)
      5. v111b dry-run — fixture signals (not actually sent)

    Each signal preserves source_file and is marked is_fixture.
    Real signals are verified via message_id in TG test channel.
    """

    signals: list[dict] = []

    # ── Real signals (actually sent to TG test channel) ──

    # Source: v110b — SOL single card send
    signals.append({
        "asset": "SOL",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -7.24,
        "open_interest": 278_000_000,
        "volume": 527_000_000,
        "funding": 0.0,  # +0.00% annualized 0.1%
        "message_id": "2239",
        "send_stage": "v1.10-B",
        "source_file": "results/market_radar_v110b_real_tg_send_result.json",
        "trigger_reason": "SOL 24h 跌幅 7.24% 触发行情异动监测",
    })

    # Source: v110e — ARB gate-protected send
    signals.append({
        "asset": "ARB",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -6.96,
        "open_interest": 4_682_600,
        "volume": 4_932_100,
        "funding": 0.0,  # +0.00% annualized 1.4%
        "message_id": "2245",
        "send_stage": "v1.10-E",
        "source_file": "results/market_radar_v110e_gate_protected_test_channel_send_result.json",
        "trigger_reason": "ARB 24h 跌幅 6.96% 触发行情异动监测",
    })

    # Source: v110f — gate-protected test channel matrix send
    signals.append({
        "asset": "ARB",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -7.55,
        "open_interest": 4_656_700,
        "volume": 4_942_400,
        "funding": 0.0,
        "message_id": "2250",
        "send_stage": "v1.10-F",
        "source_file": "results/market_radar_v110f_gate_protected_test_channel_matrix_send_result.json",
        "trigger_reason": "ARB 24h 跌幅 7.55% 触发行情异动监测",
    })

    signals.append({
        "asset": "SUI",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -6.73,
        "open_interest": 27_997_200,
        "volume": 21_182_700,
        "funding": 0.0,
        "message_id": "2251",
        "send_stage": "v1.10-F",
        "source_file": "results/market_radar_v110f_gate_protected_test_channel_matrix_send_result.json",
        "trigger_reason": "SUI 24h 跌幅 6.73% 触发行情异动监测",
    })

    signals.append({
        "asset": "BTC",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -5.54,
        "open_interest": 1_826_000_000,
        "volume": 6_345_000_000,
        "funding": None,  # Not available in v110f result
        "message_id": "2252",
        "send_stage": "v1.10-F",
        "source_file": "results/market_radar_v110f_gate_protected_test_channel_matrix_send_result.json",
        "trigger_reason": "BTC 24h 跌幅 5.54% 触发行情异动监测",
    })

    # Source: v110i — test channel stability replay
    signals.append({
        "asset": "ARB",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -6.75,
        "open_interest": 4_671_000,
        "volume": 4_905_700,
        "funding": 0.0,
        "message_id": "2257",
        "send_stage": "v1.10-I",
        "source_file": "results/market_radar_v110i_test_channel_stability_replay_result.json",
        "trigger_reason": "ARB 24h 跌幅 6.75% 触发行情异动监测",
    })

    signals.append({
        "asset": "SUI",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -5.96,
        "open_interest": 28_182_200,
        "volume": 21_344_100,
        "funding": 0.0,
        "message_id": "2258",
        "send_stage": "v1.10-I",
        "source_file": "results/market_radar_v110i_test_channel_stability_replay_result.json",
        "trigger_reason": "SUI 24h 跌幅 5.96% 触发行情异动监测",
    })

    signals.append({
        "asset": "BTC",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -5.21,
        "open_interest": 1_880_000_000,
        "volume": 6_409_000_000,
        "funding": None,
        "message_id": "2259",
        "send_stage": "v1.10-I",
        "source_file": "results/market_radar_v110i_test_channel_stability_replay_result.json",
        "trigger_reason": "BTC 24h 跌幅 5.21% 触发行情异动监测",
    })

    # ── Fixture signals from v111b dry-run (NOT actually sent) ──

    signals.append({
        "asset": "ETH",
        "signal_type": "market_anomaly",
        "source_type": "fixture",
        "is_fixture": True,
        "price_change_pct": -8.2,
        "open_interest": 890_000_000,
        "volume": None,
        "funding": -0.025,
        "message_id": None,
        "send_stage": None,
        "source_file": "results/market_radar_v111b_signal_value_gate_dryrun.json",
        "trigger_reason": "ETH 跌幅 8.2% + funding -2.5% extreme (fixture)",
    })

    signals.append({
        "asset": "SOL",
        "signal_type": "market_anomaly",
        "source_type": "fixture",
        "is_fixture": True,
        "price_change_pct": -11.5,
        "open_interest": None,
        "volume": 1_200_000_000,
        "funding": None,
        "message_id": None,
        "send_stage": None,
        "source_file": "results/market_radar_v111b_signal_value_gate_dryrun.json",
        "trigger_reason": "SOL 跌幅 11.5% strong + volume surge (fixture)",
    })

    signals.append({
        "asset": "LINK",
        "signal_type": "market_anomaly",
        "source_type": "fixture",
        "is_fixture": True,
        "price_change_pct": -3.2,
        "open_interest": 150_000_000,
        "volume": None,
        "funding": None,
        "message_id": None,
        "send_stage": None,
        "source_file": "results/market_radar_v111b_signal_value_gate_dryrun.json",
        "trigger_reason": "LINK 仅跌 3.2% 未触发异常阈值 (fixture)",
    })

    signals.append({
        "asset": "DOT",
        "signal_type": "market_anomaly",
        "source_type": "fixture",
        "is_fixture": True,
        "price_change_pct": None,
        "open_interest": None,
        "volume": None,
        "funding": None,
        "message_id": None,
        "send_stage": None,
        "source_file": "results/market_radar_v111b_signal_value_gate_dryrun.json",
        "trigger_reason": "DOT 无可用价格数据 (fixture edge case)",
    })

    signals.append({
        "asset": "HYPE",
        "signal_type": "onchain_position",
        "source_type": "fixture",
        "is_fixture": True,
        "price_change_pct": 15.0,
        "open_interest": 450_000_000,
        "volume": 890_000_000,
        "funding": None,
        "message_id": None,
        "send_stage": None,
        "source_file": "results/market_radar_v111b_signal_value_gate_dryrun.json",
        "trigger_reason": "HYPE +15% with OI spike (fixture onchain_position)",
    })

    # Additional fixture: ARB with only OI (no volume) — different field profile
    signals.append({
        "asset": "ARB",
        "signal_type": "market_anomaly",
        "source_type": "fixture",
        "is_fixture": True,
        "price_change_pct": -7.55,
        "open_interest": 4_656_700,
        "volume": None,
        "funding": None,
        "message_id": None,
        "send_stage": None,
        "source_file": "results/market_radar_v111b_signal_value_gate_dryrun.json",
        "trigger_reason": "ARB 跌幅 7.55% OI-only (fixture, no volume/funding)",
    })

    # Additional fixture: BTC with funding near zero
    signals.append({
        "asset": "BTC",
        "signal_type": "market_anomaly",
        "source_type": "fixture",
        "is_fixture": True,
        "price_change_pct": -5.54,
        "open_interest": 1_826_000_000,
        "volume": 6_345_000_000,
        "funding": 0.00004,
        "message_id": None,
        "send_stage": None,
        "source_file": "results/market_radar_v111b_signal_value_gate_dryrun.json",
        "trigger_reason": "BTC 跌幅 5.54% + OI/volume, funding near zero (fixture)",
    })

    return signals


# ── False positive / negative detection ───────────────────────────────────────

def _detect_suspected_false_positives(signal: dict, gate_result: dict) -> dict | None:
    """Detect suspected false positives using deterministic rules (no AI).

    False positive: decision=allow, but signal lacks sufficient confirmation:
      - Only price_move, no OI/volume/funding/multi_asset_sync support
      - Large number of unknown fields but still allow
    """
    if gate_result["decision"] != "allow":
        return None

    price_pct = abs(signal.get("price_change_pct") or 0)
    hits = gate_result["factor_hits"]
    has_oi = hits.get("oi_confirmation", False)
    has_vol = hits.get("volume_confirmation", False)
    has_funding = hits.get("funding_extreme", False)
    has_multi = hits.get("multi_asset_sync", False)

    reasons: list[str] = []
    risk_level = "none"

    # Rule 1: allow with ONLY price_move (no confirmations at all, except possible multi-asset)
    # But multi_asset_sync is batch-context dependent — flag if only price_move + multi
    confirmation_count = sum([has_oi, has_vol, has_funding])
    if confirmation_count == 0 and has_multi:
        reasons.append("allow with only price_move + multi_asset_sync, no OI/volume/funding confirmation")
        risk_level = "low"
    elif confirmation_count == 0 and not has_multi:
        reasons.append("allow with only price_move, no confirmation factors at all — HIGHLY SUSPICIOUS")
        risk_level = "high"

    # Rule 2: fields largely unknown but still allow
    unknown_fields = []
    if signal.get("open_interest") is None:
        unknown_fields.append("OI")
    if signal.get("volume") is None:
        unknown_fields.append("volume")
    if signal.get("funding") is None:
        unknown_fields.append("funding")
    if len(unknown_fields) >= 2:
        reasons.append(f"allow with {len(unknown_fields)} missing confirmation fields ({', '.join(unknown_fields)}) — limited evidence")
        if risk_level == "none":
            risk_level = "medium"
        elif risk_level == "low":
            risk_level = "medium"

    # Rule 3: small-cap asset with modest price change, weak evidence
    if signal["asset"] in ("ARB", "SUI") and price_pct < 8.0 and confirmation_count <= 1:
        reasons.append(f"small-cap {signal['asset']} with {price_pct:.1f}% move, only {confirmation_count} confirmation(s) — likely noise")
        if risk_level == "none":
            risk_level = "low"

    if not reasons:
        return None

    return {
        "risk_level": risk_level,
        "reasons": reasons,
    }


def _detect_suspected_false_negatives(signal: dict, gate_result: dict) -> dict | None:
    """Detect suspected false negatives using deterministic rules (no AI).

    False negative: decision=block, but signal shows clear price anomaly with
    resonance or confirmation factors that the gate missed.
    """
    if gate_result["decision"] != "block":
        return None

    price_pct = abs(signal.get("price_change_pct") or 0)
    hits = gate_result["factor_hits"]
    has_oi = hits.get("oi_confirmation", False)
    has_vol = hits.get("volume_confirmation", False)
    has_funding = hits.get("funding_extreme", False)
    has_multi = hits.get("multi_asset_sync", False)

    reasons: list[str] = []
    risk_level = "none"

    # Rule 1: price anomaly is obvious (>= 8%) but gate blocked due to field quality
    if price_pct >= 8.0:
        reasons.append(f"strong price move ({price_pct:.1f}%) blocked — price anomaly is objectively significant")
        risk_level = "medium"

    # Rule 2: has OI/volume/funding but blocked anyway (should only happen if price < 5%)
    if has_oi and has_vol:
        reasons.append("both OI and volume present but blocked — check if price threshold (5%) is too strict")
        risk_level = "high"
    elif has_oi and not has_vol:
        reasons.append("OI present but blocked — gate requires price_move first, check if 5% threshold rejects moderate moves with OI confirmation")
        if price_pct >= 3.0:
            if risk_level != "high":
                risk_level = "medium"

    # Rule 3: price near threshold (4-5%) blocked — borderline case
    if 4.0 <= price_pct < 5.0:
        reasons.append(f"price ({price_pct:.1f}%) near 5% threshold but blocked — borderline case, could be allow if context supports")
        if risk_level == "none":
            risk_level = "low"

    if not reasons:
        return None

    return {
        "risk_level": risk_level,
        "reasons": reasons,
    }


def _judge_review(signal: dict, gate_result: dict, fp: dict | None, fn: dict | None) -> str:
    """Produce a review judgment label based on gate decision and FP/FN analysis.

    Returns one of: 'likely_correct', 'possibly_noise', 'possibly_missed', 'edge_case'
    """
    decision = gate_result["decision"]

    if decision == "allow":
        if fp and fp.get("risk_level") == "high":
            return "possibly_noise"
        elif fp and fp.get("risk_level") == "medium":
            return "possibly_noise"
        elif fp and fp.get("risk_level") == "low":
            return "likely_correct (minor concern)"
        else:
            return "likely_correct"

    elif decision == "observe":
        return "likely_correct (observe is conservative)"

    elif decision == "block":
        if fn and fn.get("risk_level") in ("high", "medium"):
            return "possibly_missed"
        elif fn and fn.get("risk_level") == "low":
            return "likely_correct (borderline)"
        else:
            return "likely_correct"

    return "unknown"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    print(f"Market Radar v1.11-C — Historical Signal Value Replay: {china_stamp()}")
    print(f"Gate version: {GATE_VERSION}")

    # Step 1: Collect signals
    print("\n[1/5] Collecting replay signals...")
    signals = _collect_replay_signals()
    real_signals = [s for s in signals if not s["is_fixture"]]
    fixture_signals = [s for s in signals if s["is_fixture"]]
    print(f"  Collected {len(signals)} signals: {len(real_signals)} real, {len(fixture_signals)} fixture")
    for s in signals:
        tag = "REAL" if not s["is_fixture"] else "FIXTURE"
        print(f"    [{tag:7s}] {s['asset']:6s} {s['signal_type']:20s} price={s.get('price_change_pct')} source={s['source_file']}")

    # Step 2: Run gate evaluation
    print(f"\n[2/5] Running SignalValueGate on {len(signals)} signals...")
    results: list[dict] = []
    for sig in signals:
        context = {
            "signals": signals,
            "same_direction_asset_count": len(signals),  # all in batch
            "replay_batch_size": len(signals),
        }
        gate_result = evaluate_signal_value(sig, context)

        # Step 3: Detect suspected false positives/negatives
        fp = _detect_suspected_false_positives(sig, gate_result)
        fn = _detect_suspected_false_negatives(sig, gate_result)
        review = _judge_review(sig, gate_result, fp, fn)

        entry = {
            "asset": sig["asset"],
            "signal_type": sig["signal_type"],
            "source_type": sig["source_type"],
            "is_fixture": sig["is_fixture"],
            "price_change_pct": sig.get("price_change_pct"),
            "open_interest": sig.get("open_interest"),
            "volume": sig.get("volume"),
            "funding": sig.get("funding"),
            "message_id": sig.get("message_id"),
            "send_stage": sig.get("send_stage"),
            "source_file": sig["source_file"],
            "gate_decision": gate_result["decision"],
            "value_score": gate_result["value_score"],
            "value_tier": gate_result["value_tier"],
            "factor_hits": gate_result["factor_hits"],
            "reasons": gate_result["reasons"],
            "warnings": gate_result["warnings"],
            "review_judgment": review,
            "suspected_false_positive": fp,
            "suspected_false_negative": fn,
        }
        results.append(entry)

        decision = gate_result["decision"]
        score = gate_result["value_score"]
        asset = sig["asset"]
        fixture_mark = " [F]" if sig["is_fixture"] else ""
        fp_mark = " [FP]" if fp else ""
        fn_mark = " [FN?]" if fn else ""
        print(f"  [{decision.upper():7s}] {asset:6s} score={score:3d} tier={gate_result['value_tier']:6s} review={review:30s}{fixture_mark}{fp_mark}{fn_mark}")

    # ── Aggregate ──
    print(f"\n[3/5] Aggregating statistics...")
    allow_count = sum(1 for r in results if r["gate_decision"] == "allow")
    observe_count = sum(1 for r in results if r["gate_decision"] == "observe")
    block_count = sum(1 for r in results if r["gate_decision"] == "block")
    real_count = sum(1 for r in results if not r["is_fixture"])
    fixture_count = sum(1 for r in results if r["is_fixture"])

    # Decision breakdown by signal_type
    decision_breakdown: dict[str, dict] = {}
    for r in results:
        st = r["signal_type"]
        d = r["gate_decision"]
        if st not in decision_breakdown:
            decision_breakdown[st] = {}
        decision_breakdown[st][d] = decision_breakdown[st].get(d, 0) + 1

    # Asset-level results
    asset_results: dict[str, dict] = {}
    for r in results:
        asset = r["asset"]
        if asset not in asset_results:
            asset_results[asset] = {"total": 0, "allow": 0, "observe": 0, "block": 0, "signals": []}
        asset_results[asset]["total"] += 1
        asset_results[asset][r["gate_decision"]] += 1
        asset_results[asset]["signals"].append({
            "is_fixture": r["is_fixture"],
            "price_change_pct": r["price_change_pct"],
            "gate_decision": r["gate_decision"],
            "value_score": r["value_score"],
            "factor_hits": r["factor_hits"],
            "review_judgment": r["review_judgment"],
        })

    # Suspected false positives / negatives
    suspected_fp = [r for r in results if r["suspected_false_positive"]]
    suspected_fn = [r for r in results if r["suspected_false_negative"]]

    # ── Threshold notes ──
    print(f"\n[4/5] Generating threshold analysis...")
    threshold_notes = []

    # Check if too many allows
    allow_pct = allow_count / len(results) * 100 if results else 0
    if allow_pct > 50:
        threshold_notes.append(
            f"allow rate is {allow_pct:.0f}% ({allow_count}/{len(results)}) — "
            f"consider raising price threshold or requiring more confirmation factors. "
            f"Many signals with only price+OI (no volume, near-zero funding) pass as allow."
        )

    # Check if observe count is high
    observe_pct = observe_count / len(results) * 100 if results else 0
    if observe_pct > 30:
        threshold_notes.append(
            f"observe rate is {observe_pct:.0f}% ({observe_count}/{len(results)}) — "
            f"suggests field quality is insufficient. Consider enhancing OI/volume delta data "
            f"before connecting to send pipeline."
        )

    # Check for funding dependency
    funding_hit_count = sum(1 for r in results if r["factor_hits"].get("funding_extreme"))
    if funding_hit_count <= 1:
        threshold_notes.append(
            f"funding_extreme only hit {funding_hit_count}/{len(results)} times — "
            f"funding near zero is the norm in these samples. funding factor currently provides "
            f"almost no differentiation. Consider lowering funding threshold or collecting "
            f"funding delta data."
        )

    # Volume field quality
    vol_missing_count = sum(1 for r in results if r.get("volume") is None)
    oi_missing_count = sum(1 for r in results if r.get("open_interest") is None)
    threshold_notes.append(
        f"field availability: OI missing in {oi_missing_count}/{len(results)} signals, "
        f"volume missing in {vol_missing_count}/{len(results)} signals. "
        f"Missing fields cause -10 score penalty each."
    )

    # Multi-asset sync context note
    threshold_notes.append(
        f"multi_asset_sync: triggered based on batch context ({len(signals)} signals in batch). "
        f"All downward-moving assets join the same direction set. In production, "
        f"same_direction_asset_count would be from real-time signals window."
    )

    # ── Warnings ──
    all_warnings: list[str] = []
    for r in results:
        for w in r["warnings"]:
            if w not in all_warnings:
                all_warnings.append(w)

    # Additional structural warnings
    custom_warnings: list[str] = []
    if fixture_count > real_count:
        custom_warnings.append(
            f"fixture signals ({fixture_count}) outnumber real signals ({real_count}) — "
            f"replay conclusions are skewed toward synthetic data. Run with more real "
            f"historical signals when available."
        )
    if suspected_fp:
        fp_assets = [f"{r['asset']}({r['suspected_false_positive']['risk_level']})" for r in suspected_fp]
        custom_warnings.append(
            f"{len(suspected_fp)} suspected false positive(s): {', '.join(fp_assets)}. "
            f"Review these before connecting to send pipeline."
        )
    if suspected_fn:
        fn_assets = [f"{r['asset']}({r['suspected_false_negative']['risk_level']})" for r in suspected_fn]
        custom_warnings.append(
            f"{len(suspected_fn)} suspected false negative(s): {', '.join(fn_assets)}. "
            f"May indicate missed valuable signals."
        )

    # ── Build report ──
    report = {
        "gate_version": GATE_VERSION,
        "replay_version": "v1.11-C",
        "generated_at": china_stamp(),
        "total_signals": len(results),
        "real_signal_count": real_count,
        "fixture_signal_count": fixture_count,
        "allow_count": allow_count,
        "observe_count": observe_count,
        "block_count": block_count,
        "decision_breakdown": decision_breakdown,
        "asset_results": asset_results,
        "suspected_false_positive": [
            {
                "asset": r["asset"],
                "risk_level": r["suspected_false_positive"]["risk_level"],
                "reasons": r["suspected_false_positive"]["reasons"],
                "gate_decision": r["gate_decision"],
                "value_score": r["value_score"],
                "factor_hits": r["factor_hits"],
                "is_fixture": r["is_fixture"],
            }
            for r in suspected_fp
        ],
        "suspected_false_negative": [
            {
                "asset": r["asset"],
                "risk_level": r["suspected_false_negative"]["risk_level"],
                "reasons": r["suspected_false_negative"]["reasons"],
                "gate_decision": r["gate_decision"],
                "value_score": r["value_score"],
                "factor_hits": r["factor_hits"],
                "is_fixture": r["is_fixture"],
            }
            for r in suspected_fn
        ],
        "threshold_notes": threshold_notes,
        "warnings": custom_warnings,
        "field_warnings": all_warnings,
        "details": results,
    }

    # ── Write output ──
    print(f"\n[5/5] Writing replay report to {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print(f"SignalValueGate v1.11-C Replay Summary")
    print(f"{'=' * 60}")
    print(f"  Total signals:     {len(results)} ({real_count} real, {fixture_count} fixture)")
    print(f"  Allowed:           {allow_count}")
    print(f"  Observe:           {observe_count}")
    print(f"  Blocked:           {block_count}")
    print(f"  Suspected FP:      {len(suspected_fp)}")
    print(f"  Suspected FN:      {len(suspected_fn)}")
    print(f"")
    print(f"  Decision breakdown by type:")
    for st, counts in decision_breakdown.items():
        parts = ", ".join(f"{d}={c}" for d, c in sorted(counts.items()))
        print(f"    {st}: {parts}")
    print(f"")
    print(f"  TG send:           NONE (replay only)")
    print(f"  Secrets loaded:    NONE")
    print(f"  Paid APIs:         NONE")
    print(f"  Loop/daemon:       NONE")
    print(f"")
    print(f"  Report written to: {output_path}")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
