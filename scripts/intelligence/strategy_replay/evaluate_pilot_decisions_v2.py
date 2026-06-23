"""Evaluate pilot decisions V3 — Stage 2: reads sealed hypotheses, computes incremental outcomes.
Repaired: dual-window outcome lineage, no pre-event baseline usage.
"""
import json, pathlib, hashlib

WORKTREE = pathlib.Path(r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-c-macro-strategy-replay-v1")
OUT = WORKTREE / "data" / "intelligence" / "strategy_replay" / "pilot_v2"
UP = OUT / "upstream"

EPSILON_PCT = 0.001


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def write_jsonl(records, path, sort_key=None):
    if path is None:
        return
    if sort_key:
        records = sorted(records, key=lambda r: r.get(sort_key, ""))
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def run_evaluation():
    # Step 1: Read sealed hypotheses (phase separation)
    hypotheses = load_jsonl(OUT / "strategy_hypotheses_v2.jsonl")
    results = load_jsonl(OUT / "strategy_replay_results_v2.jsonl")
    decision_inputs = load_jsonl(OUT / "decision_inputs_v1.jsonl")
    horizon_windows = load_jsonl(UP / "lane_b_horizon_windows_v3.jsonl")

    print(f"Read {len(hypotheses)} sealed hypotheses")
    print(f"Read {len(results)} sealed results")
    print(f"Read {len(decision_inputs)} decision inputs")

    du_by_id = {d["decision_unit_id"]: d for d in decision_inputs}

    # Index horizon windows by (event_id, symbol, nominal_horizon)
    window_index = {}
    for w in horizon_windows:
        window_index[(w["event_id"], w["symbol"], w["nominal_horizon"])] = w

    outcomes = []
    evaluations = []

    for hyp in hypotheses:
        if hyp.get("confidence_type") != "exploratory":
            continue

        hyp_id = hyp["hypothesis_id"]
        horizon = hyp["time_horizon"]
        expected_effect = hyp["expected_effect"]
        asset = hyp["asset"]

        # Get signal window info from hypothesis lineage fields
        signal_window_id = hyp.get("signal_window_id", "")
        signal_dir = hyp.get("signal_direction", "neutral")
        signal_return = hyp.get("signal_return_pct", 0.0)
        signal_endpoint_price = hyp.get("signal_endpoint_price", 0)
        signal_endpoint_time = hyp.get("signal_endpoint_time_utc", "")
        decision_cutoff = hyp.get("decision_cutoff_utc", "")

        # Fallback to decision_inputs if lineage fields not populated
        if not signal_window_id:
            matching_res = [r for r in results if hyp_id in r.get("hypotheses", [])]
            if matching_res:
                du_id = matching_res[0].get("decision_unit_id", "")
                du = du_by_id.get(du_id, {})
                signal_window_id = du.get("signal_window_id", "")
                signal_endpoint_price = du.get("signal_endpoint_price", 0)
                signal_endpoint_time = du.get("signal_endpoint_time_utc", "")

        # Determine target horizon
        target_nh = "4h" if horizon == "continuation_to_4h" else "24h" if horizon == "continuation_to_24h" else None
        if not target_nh:
            continue

        # Find the target window
        eid = hyp.get("constituent_event_ids", [hyp.get("event_id", "")])[0]
        asset_sym = f"{asset}USDT"
        target_key = (eid, asset_sym, target_nh)
        target_win = window_index.get(target_key)

        if not target_win or not signal_endpoint_price:
            continue

        target_window_id = target_win.get("window_id", "")
        target_endpoint_price = target_win.get("post_bar_close", target_win.get("endpoint_price", 0))
        if not target_endpoint_price:
            continue

        # Incremental return from 1h endpoint (not pre-event baseline)
        incremental_return_pct = (target_endpoint_price / signal_endpoint_price - 1) * 100

        # Direction
        if incremental_return_pct > EPSILON_PCT:
            outcome_dir = "positive"
        elif incremental_return_pct < -EPSILON_PCT:
            outcome_dir = "negative"
        else:
            outcome_dir = "neutral"

        # Correctness
        if outcome_dir == "neutral":
            correctness = "neutral_outcome"
        elif (expected_effect == "bullish" and outcome_dir == "positive") or \
             (expected_effect == "bearish" and outcome_dir == "negative"):
            correctness = "correct"
        else:
            correctness = "incorrect"

        outcome = {
            "outcome_id": f"outcome_{hyp_id}",
            "hypothesis_id": hyp_id,
            "decision_unit_id": hyp.get("decision_unit_id", ""),
            "release_unit_id": hyp.get("release_unit_id", ""),
            "asset": asset,
            "evaluation_horizon": target_nh,
            "signal_window_id": signal_window_id,
            "target_window_id": target_window_id,
            "source_window_ids": [signal_window_id, target_window_id],
            "outcome_start_time_utc": signal_endpoint_time,
            "outcome_end_time_utc": target_win.get("endpoint_price_time_utc", ""),
            "outcome_start_price": signal_endpoint_price,
            "outcome_end_price": target_endpoint_price,
            "outcome_start_price_source": {
                "field": "signal_endpoint_price",
                "window_id": signal_window_id,
            },
            "outcome_end_price_source": {
                "field": "post_bar_close",
                "window_id": target_window_id,
            },
            "incremental_return_pct": round(incremental_return_pct, 6),
            "outcome_direction": outcome_dir,
            "precision_class": "coarse_hourly_alignment",
        }
        outcomes.append(outcome)

        evaluation = {
            "evaluation_id": f"eval_{hyp_id}",
            "hypothesis_id": hyp_id,
            "strategy_id": "strat_post_release_reaction_continuation_v1",
            "decision_unit_id": hyp.get("decision_unit_id", ""),
            "asset": asset,
            "time_horizon": horizon,
            "expected_effect": expected_effect,
            "outcome_direction": outcome_dir,
            "incremental_return_pct": round(incremental_return_pct, 6),
            "correctness": correctness,
            "precision_class": "coarse_hourly_alignment",
        }
        evaluations.append(evaluation)

    # ── Baseline evaluations ──
    baseline_defs = [
        ("always_bullish", "bullish"),
        ("always_bearish", "bearish"),
        ("reverse_first_reaction", None),
        ("always_abstain", None),
    ]

    baseline_evaluations = []
    for du in decision_inputs:
        du_id = du["decision_unit_id"]
        for horizon_nh in ["4h", "24h"]:
            for base_id, base_dir in baseline_defs:
                if base_id == "always_abstain":
                    baseline_evaluations.append({
                        "evaluation_id": f"be_{base_id}_{du_id}_{horizon_nh}",
                        "baseline_id": base_id, "decision_unit_id": du_id,
                        "asset": du["asset"], "horizon": horizon_nh,
                        "correctness": "abstained", "precision_class": "coarse_hourly_alignment",
                    })
                    continue

                if base_id == "reverse_first_reaction":
                    signal_dir = du.get("signal_direction", "neutral")
                    expected = "bullish" if signal_dir == "negative" else "bearish" if signal_dir == "positive" else "neutral"
                else:
                    expected = base_dir

                if expected == "neutral":
                    baseline_evaluations.append({
                        "evaluation_id": f"be_{base_id}_{du_id}_{horizon_nh}",
                        "baseline_id": base_id, "decision_unit_id": du_id,
                        "asset": du["asset"], "horizon": horizon_nh,
                        "correctness": "neutral_outcome", "precision_class": "coarse_hourly_alignment",
                    })
                    continue

                btc_pre = du.get("signal_endpoint_price", 0)
                if not btc_pre:
                    continue

                first_eid = du["constituent_event_ids"][0]
                asset_sym = f"{du['asset']}USDT"
                target_win = window_index.get((first_eid, asset_sym, horizon_nh))
                if not target_win:
                    continue

                target_end = target_win.get("post_bar_close", target_win.get("endpoint_price", 0))
                if not target_end:
                    continue

                inc_return = (target_end / btc_pre - 1) * 100
                odir = "positive" if inc_return > EPSILON_PCT else "negative" if inc_return < -EPSILON_PCT else "neutral"

                if odir == "neutral":
                    correctness = "neutral_outcome"
                elif (expected == "bullish" and odir == "positive") or (expected == "bearish" and odir == "negative"):
                    correctness = "correct"
                else:
                    correctness = "incorrect"

                baseline_evaluations.append({
                    "evaluation_id": f"be_{base_id}_{du_id}_{horizon_nh}",
                    "baseline_id": base_id, "decision_unit_id": du_id,
                    "asset": du["asset"], "horizon": horizon_nh,
                    "correctness": correctness, "precision_class": "coarse_hourly_alignment",
                })

    # Write
    write_jsonl(outcomes, OUT / "evaluation_outcomes_v1.jsonl", sort_key="outcome_id")
    write_jsonl(evaluations, OUT / "strategy_evaluations_v1.jsonl", sort_key="evaluation_id")
    write_jsonl(baseline_evaluations, OUT / "baseline_evaluations_v1.jsonl", sort_key="evaluation_id")

    # Verify outcome window lineage
    sig_ok = sum(1 for o in outcomes if o.get("signal_window_id"))
    tgt_ok = sum(1 for o in outcomes if o.get("target_window_id"))
    dual_ok = sum(1 for o in outcomes if len(o.get("source_window_ids", [])) == 2)
    start_is_1h = sum(1 for o in outcomes if "1h" in (o.get("signal_window_id", "")))
    print(f"\nEvaluation complete:")
    print(f"  Outcomes: {len(outcomes)} (signal_window={sig_ok}, target_window={tgt_ok}, dual_refs={dual_ok})")
    print(f"  Strategy evaluations: {len(evaluations)}")
    print(f"  Baseline evaluations: {len(baseline_evaluations)}")

    assert sig_ok == 32, f"Expected 32 outcomes with signal_window_id, got {sig_ok}"
    assert tgt_ok == 32, f"Expected 32 outcomes with target_window_id, got {tgt_ok}"
    assert dual_ok == 32, f"Expected 32 outcomes with dual window refs, got {dual_ok}"

    return {
        "outcomes": len(outcomes),
        "signal_window_set": sig_ok,
        "target_window_set": tgt_ok,
        "dual_refs": dual_ok,
        "evaluations": len(evaluations),
        "baseline_evaluations": len(baseline_evaluations),
    }


if __name__ == "__main__":
    result = run_evaluation()
    print(json.dumps(result, indent=2))
