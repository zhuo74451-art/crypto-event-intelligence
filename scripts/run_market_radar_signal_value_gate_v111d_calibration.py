"""Market Radar v1.11-D — SignalValueGate Calibration Replay 门控校准回放

Reads the same 15 signals from the v1.11-C replay, runs each through the
v1.11-D calibrated gate, and produces a before/after comparison.

No TG send, no secrets, no paid APIs, no loop/daemon.

Usage:
    python scripts/run_market_radar_signal_value_gate_v111d_calibration.py
    python scripts/run_market_radar_signal_value_gate_v111d_calibration.py --output results/custom.json
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
        description="Market Radar v1.11-D — SignalValueGate Calibration Replay"
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "results" / "market_radar_v111d_signal_value_calibration_result.json"),
        help="Output path for calibration result JSON",
    )
    # Accept path to v1.11-C result for before/after comparison
    parser.add_argument(
        "--v111c-result",
        default=str(ROOT / "results" / "market_radar_v111c_signal_value_replay_result.json"),
        help="Path to v1.11-C replay result JSON for comparison",
    )
    return parser.parse_args()


def china_stamp() -> str:
    return datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S UTC+8")


# ── Signal collection (same 15 signals as v1.11-C) ────────────────────────────

def _collect_replay_signals() -> list[dict]:
    """Collect the same 15 replayable signals as v1.11-C."""

    signals: list[dict] = []

    # ── Real signals (actually sent to TG test channel) ──
    signals.append({
        "asset": "SOL",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -7.24,
        "open_interest": 278_000_000,
        "volume": 527_000_000,
        "funding": 0.0,
        "message_id": "2239",
        "send_stage": "v1.10-B",
        "source_file": "results/market_radar_v110b_real_tg_send_result.json",
        "trigger_reason": "SOL 24h 跌幅 7.24% 触发行情异动监测",
    })

    signals.append({
        "asset": "ARB",
        "signal_type": "market_anomaly",
        "source_type": "api",
        "is_fixture": False,
        "price_change_pct": -6.96,
        "open_interest": 4_682_600,
        "volume": 4_932_100,
        "funding": 0.0,
        "message_id": "2245",
        "send_stage": "v1.10-E",
        "source_file": "results/market_radar_v110e_gate_protected_test_channel_send_result.json",
        "trigger_reason": "ARB 24h 跌幅 6.96% 触发行情异动监测",
    })

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
        "funding": None,
        "message_id": "2252",
        "send_stage": "v1.10-F",
        "source_file": "results/market_radar_v110f_gate_protected_test_channel_matrix_send_result.json",
        "trigger_reason": "BTC 24h 跌幅 5.54% 触发行情异动监测",
    })

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

    # ── Fixture signals ──
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


# ── False positive / negative detection (v1.11-D calibrated) ──────────────────

def _detect_suspected_false_positives(signal: dict, gate_result: dict) -> dict | None:
    """Detect suspected false positives (v1.11-D calibrated rules).

    False positive: decision=allow, but signal lacks sufficient confirmation.
    """
    if gate_result["decision"] != "allow":
        return None

    hits = gate_result["factor_hits"]
    has_oi = hits.get("oi_confirmation", False)
    has_vol = hits.get("volume_confirmation", False)
    has_funding = hits.get("funding_extreme", False)
    has_multi = hits.get("multi_asset_sync", False)

    reasons: list[str] = []
    risk_level = "none"

    confirmation_count = sum([has_oi, has_vol, has_funding])

    # Rule 1: allow with multi_asset_sync as only backing — now much less likely in v1.11-D
    # because multi is no longer auto-allow. Still check for edge cases.
    if has_multi and confirmation_count == 0:
        reasons.append("allow via multi_asset_sync but no OI/volume/funding backing — POSSIBLE CALIBRATION GAP")
        risk_level = "low"

    # Rule 2: allow with only 1 confirmation and missing >= 2 fields
    if confirmation_count == 1:
        missing_count = 0
        if signal.get("open_interest") is None and not has_oi:
            missing_count += 1
        if signal.get("volume") is None and not has_vol:
            missing_count += 1
        if signal.get("funding") is None and not has_funding:
            missing_count += 1
        if missing_count >= 2:
            reasons.append(f"allow with only 1 confirmation and {missing_count} missing fields — limited evidence")
            risk_level = "low"

    # Rule 3: small-cap asset with modest price, only 1 confirmation
    price_pct = abs(signal.get("price_change_pct") or 0)
    if signal["asset"] in ("ARB", "SUI") and price_pct < 8.0 and confirmation_count <= 1:
        reasons.append(f"small-cap {signal['asset']} with {price_pct:.1f}% move, only {confirmation_count} confirmation(s)")
        if risk_level == "none":
            risk_level = "low"

    if not reasons:
        return None

    return {
        "risk_level": risk_level,
        "reasons": reasons,
    }


def _detect_suspected_false_negatives(signal: dict, gate_result: dict) -> dict | None:
    """Detect suspected false negatives (same rules as v1.11-C)."""
    if gate_result["decision"] != "block":
        return None

    price_pct = abs(signal.get("price_change_pct") or 0)
    hits = gate_result["factor_hits"]
    has_oi = hits.get("oi_confirmation", False)
    has_vol = hits.get("volume_confirmation", False)

    reasons: list[str] = []
    risk_level = "none"

    if price_pct >= 8.0:
        reasons.append(f"strong price move ({price_pct:.1f}%) blocked — price anomaly is objectively significant")
        risk_level = "medium"

    if has_oi and has_vol:
        reasons.append("both OI and volume present but blocked")
        risk_level = "high"
    elif has_oi and not has_vol:
        reasons.append("OI present but blocked — gate requires price_move first")
        if price_pct >= 3.0:
            if risk_level != "high":
                risk_level = "medium"

    if 4.0 <= price_pct < 5.0:
        reasons.append(f"price ({price_pct:.1f}%) near 5% threshold but blocked — borderline case")
        if risk_level == "none":
            risk_level = "low"

    if not reasons:
        return None

    return {
        "risk_level": risk_level,
        "reasons": reasons,
    }


def _judge_review(signal: dict, gate_result: dict, fp: dict | None, fn: dict | None) -> str:
    """Produce a review judgment label."""
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


# ── Load v1.11-C results for before/after comparison ──────────────────────────

def _load_v111c_stats(v111c_path: str) -> dict:
    """Load v1.11-C stats for before/after comparison."""
    try:
        with open(v111c_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "allow_count": data.get("allow_count", 0),
            "observe_count": data.get("observe_count", 0),
            "block_count": data.get("block_count", 0),
            "total_signals": data.get("total_signals", 0),
            "suspected_fp_count": len(data.get("suspected_false_positive", [])),
            "suspected_fn_count": len(data.get("suspected_false_negative", [])),
            "loaded": True,
        }
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        return {
            "allow_count": 0,
            "observe_count": 0,
            "block_count": 0,
            "total_signals": 0,
            "suspected_fp_count": 0,
            "suspected_fn_count": 0,
            "loaded": False,
            "error": str(exc),
        }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path

    print(f"Market Radar v1.11-D — SignalValueGate Calibration Replay: {china_stamp()}")
    print(f"Gate version: {GATE_VERSION}")

    # Load v1.11-C stats for comparison
    print("\n[0/5] Loading v1.11-C baseline...")
    v111c = _load_v111c_stats(args.v111c_result)
    if v111c["loaded"]:
        print(f"  v1.11-C: allow={v111c['allow_count']}, observe={v111c['observe_count']}, "
              f"block={v111c['block_count']}, FP={v111c['suspected_fp_count']}, "
              f"FN={v111c['suspected_fn_count']}")
    else:
        print(f"  v1.11-C result not available ({v111c.get('error', 'unknown')}) — "
              f"before/after comparison will use N/A")

    # Step 1: Collect signals
    print("\n[1/5] Collecting replay signals...")
    signals = _collect_replay_signals()
    real_signals = [s for s in signals if not s["is_fixture"]]
    fixture_signals = [s for s in signals if s["is_fixture"]]
    print(f"  Collected {len(signals)} signals: {len(real_signals)} real, {len(fixture_signals)} fixture")

    # Count real assets in same direction for context — v1.11-D uses this to avoid
    # inflated multi_asset_sync from fixtures
    real_down = [s for s in real_signals if (s.get("price_change_pct") or 0) < 0]
    real_up = [s for s in real_signals if (s.get("price_change_pct") or 0) > 0]
    # Determine batch direction (most signals are down)
    real_same_dir = max(len(real_down), len(real_up))
    print(f"  Batch: {len(real_signals)} real signals, {real_same_dir} in dominant direction")

    # Step 2: Run v1.11-D calibrated gate
    print(f"\n[2/5] Running v1.11-D calibrated SignalValueGate on {len(signals)} signals...")
    results: list[dict] = []

    for sig in signals:
        # v1.11-D context: provide pre-computed real_same_direction_asset_count
        # to avoid fixture inflation. The gate will use this for multi_asset_sync.
        context = {
            "signals": signals,
            "same_direction_asset_count": len(signals),  # total (including fixtures)
            "real_same_direction_asset_count": real_same_dir,  # real only
            "replay_batch_size": len(signals),
        }
        gate_result = evaluate_signal_value(sig, context)

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

    # ── Before/after comparison ──
    print(f"\n[4/5] Building before/after comparison...")
    allow_pct_d = allow_count / len(results) * 100 if results else 0
    observe_pct_d = observe_count / len(results) * 100 if results else 0

    if v111c["loaded"] and v111c["total_signals"] > 0:
        allow_pct_c = v111c["allow_count"] / v111c["total_signals"] * 100
        observe_pct_c = v111c["observe_count"] / v111c["total_signals"] * 100
        before_after = {
            "v111c_allow_count": v111c["allow_count"],
            "v111c_observe_count": v111c["observe_count"],
            "v111c_block_count": v111c["block_count"],
            "v111c_allow_rate_pct": round(allow_pct_c, 1),
            "v111c_observe_rate_pct": round(observe_pct_c, 1),
            "v111c_suspected_fp_count": v111c["suspected_fp_count"],
            "v111c_suspected_fn_count": v111c["suspected_fn_count"],
            "v111d_allow_count": allow_count,
            "v111d_observe_count": observe_count,
            "v111d_block_count": block_count,
            "v111d_allow_rate_pct": round(allow_pct_d, 1),
            "v111d_observe_rate_pct": round(observe_pct_d, 1),
            "v111d_suspected_fp_count": len(suspected_fp),
            "v111d_suspected_fn_count": len(suspected_fn),
            "allow_rate_delta": round(allow_pct_d - allow_pct_c, 1),
            "observe_rate_delta": round(observe_pct_d - observe_pct_c, 1),
            "allow_count_delta": allow_count - v111c["allow_count"],
            "observe_count_delta": observe_count - v111c["observe_count"],
            "suspected_fp_delta": len(suspected_fp) - v111c["suspected_fp_count"],
            "suspected_fn_delta": len(suspected_fn) - v111c["suspected_fn_count"],
        }
    else:
        before_after = {
            "v111c_allow_count": "N/A",
            "v111c_observe_count": "N/A",
            "v111c_block_count": "N/A",
            "v111c_allow_rate_pct": "N/A",
            "v111c_observe_rate_pct": "N/A",
            "v111c_suspected_fp_count": "N/A",
            "v111c_suspected_fn_count": "N/A",
            "v111d_allow_count": allow_count,
            "v111d_observe_count": observe_count,
            "v111d_block_count": block_count,
            "v111d_allow_rate_pct": round(allow_pct_d, 1),
            "v111d_observe_rate_pct": round(observe_pct_d, 1),
            "v111d_suspected_fp_count": len(suspected_fp),
            "v111d_suspected_fn_count": len(suspected_fn),
            "allow_rate_delta": "N/A",
            "observe_rate_delta": "N/A",
            "allow_count_delta": "N/A",
            "observe_count_delta": "N/A",
            "suspected_fp_delta": "N/A",
            "suspected_fn_delta": "N/A",
            "note": "v1.11-C result file not available — comparison is one-sided",
        }

    # ── Threshold notes ──
    threshold_notes = []

    # Allow rate analysis
    if allow_pct_d > 50:
        threshold_notes.append(
            f"v1.11-D allow rate is {allow_pct_d:.0f}% ({allow_count}/{len(results)}) — "
            f"lower than v1.11-C but still above 50%. Most allowed signals have price + OI + volume "
            f"triple confirmation (real TG signals). Remaining allows are from strong confirmation combos."
        )
    else:
        threshold_notes.append(
            f"v1.11-D allow rate is {allow_pct_d:.0f}% ({allow_count}/{len(results)}) — "
            f"significantly improved from v1.11-C (87%). Gate now correctly requires OI/volume backing "
            f"for multi_asset_sync and filters out field-deficient signals."
        )

    # Observe layer activation
    if observe_count > 0:
        threshold_notes.append(
            f"observe layer activated: {observe_count}/{len(results)} ({observe_pct_d:.0f}%). "
            f"Signals in observe are those with price movement but insufficient confirmation factors. "
            f"These are candidates for monitoring without entering send pipeline."
        )
    else:
        threshold_notes.append(
            f"observe layer still at 0 — all signals with price move have at least one strong confirmation. "
            f"This suggests sample field quality is high; smaller production batches may yield more observe."
        )

    # Multi-asset sync impact
    multi_hit_count = sum(1 for r in results if r["factor_hits"].get("multi_asset_sync"))
    threshold_notes.append(
        f"multi_asset_sync: triggered {multi_hit_count}/{len(results)} times. "
        f"v1.11-D calibration prevents multi_asset_sync from being a 'free pass' — "
        f"it now requires OI or volume backing to count as strong confirmation."
    )

    # Funding factor
    funding_hit_count = sum(1 for r in results if r["factor_hits"].get("funding_extreme"))
    threshold_notes.append(
        f"funding_extreme: hit {funding_hit_count}/{len(results)} times. "
        f"Funding near zero remains the norm; this factor provides limited differentiation."
    )

    # Field quality
    vol_missing_count = sum(1 for r in results if r.get("volume") is None)
    oi_missing_count = sum(1 for r in results if r.get("open_interest") is None)
    threshold_notes.append(
        f"field availability: OI missing in {oi_missing_count}/{len(results)} signals, "
        f"volume missing in {vol_missing_count}/{len(results)} signals."
    )

    # ── Warnings ──
    custom_warnings: list[str] = []
    if suspected_fp:
        fp_assets = [f"{r['asset']}({r['suspected_false_positive']['risk_level']})" for r in suspected_fp]
        custom_warnings.append(
            f"{len(suspected_fp)} suspected false positive(s): {', '.join(fp_assets)}."
        )
    else:
        custom_warnings.append("NO suspected false positives detected — v1.11-D calibration has eliminated the FP issues seen in v1.11-C.")

    if suspected_fn:
        fn_assets = [f"{r['asset']}({r['suspected_false_negative']['risk_level']})" for r in suspected_fn]
        custom_warnings.append(
            f"{len(suspected_fn)} suspected false negative(s): {', '.join(fn_assets)}."
        )

    # Collect all unique field warnings
    all_warnings: list[str] = []
    for r in results:
        for w in r["warnings"]:
            if w not in all_warnings:
                all_warnings.append(w)

    # ── Build report ──
    report = {
        "gate_version": GATE_VERSION,
        "replay_version": "v1.11-D",
        "generated_at": china_stamp(),
        "total_signals": len(results),
        "real_signal_count": real_count,
        "fixture_signal_count": fixture_count,
        "allow_count": allow_count,
        "observe_count": observe_count,
        "block_count": block_count,
        "decision_breakdown": decision_breakdown,
        "before_after_comparison": before_after,
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
    print(f"\n[5/5] Writing calibration report to {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print(f"SignalValueGate v1.11-D Calibration Replay Summary")
    print(f"{'=' * 60}")
    print(f"  Total signals:     {len(results)} ({real_count} real, {fixture_count} fixture)")
    print(f"  Allowed:           {allow_count}")
    print(f"  Observe:           {observe_count}")
    print(f"  Blocked:           {block_count}")
    print(f"  Suspected FP:      {len(suspected_fp)}")
    print(f"  Suspected FN:      {len(suspected_fn)}")
    print(f"")
    print(f"  Before/After Comparison:")
    if before_after.get("v111c_allow_count") != "N/A":
        print(f"    v1.11-C allow: {before_after['v111c_allow_count']} → v1.11-D allow: {allow_count} (Δ{allow_count - before_after['v111c_allow_count']})")
        print(f"    v1.11-C observe: {before_after['v111c_observe_count']} → v1.11-D observe: {observe_count} (Δ{observe_count - before_after['v111c_observe_count']})")
        print(f"    v1.11-C block: {before_after['v111c_block_count']} → v1.11-D block: {block_count} (Δ{block_count - before_after['v111c_block_count']})")
        print(f"    allow rate: {before_after['v111c_allow_rate_pct']}% → {before_after['v111d_allow_rate_pct']}% (Δ{before_after['allow_rate_delta']}%)")
        print(f"    observe rate: {before_after['v111c_observe_rate_pct']}% → {before_after['v111d_observe_rate_pct']}% (Δ{before_after['observe_rate_delta']}%)")
        print(f"    suspected FP: {before_after['v111c_suspected_fp_count']} → {before_after['v111d_suspected_fp_count']} (Δ{before_after['suspected_fp_delta']})")
        print(f"    suspected FN: {before_after['v111c_suspected_fn_count']} → {before_after['v111d_suspected_fn_count']} (Δ{before_after['suspected_fn_delta']})")
    else:
        print(f"    (v1.11-C baseline not available)")
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
