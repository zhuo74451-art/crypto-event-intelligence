"""Build pilot decisions V3 — Stage 1: decisions only, no future data.
Repaired: lineage fields, no duplicate hypotheses, no fabricated timestamps.
"""
import json, hashlib, pathlib, sys

WORKTREE = pathlib.Path(r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-c-macro-strategy-replay-v1")
sys.path.insert(0, str(WORKTREE))

UP = WORKTREE / "data" / "intelligence" / "strategy_replay" / "pilot_v2" / "upstream"
OUT = WORKTREE / "data" / "intelligence" / "strategy_replay" / "pilot_v2"

from market_radar.intelligence.strategy_replay.contracts import (
    StrategyHypothesisV1, deterministic_id
)
from market_radar.intelligence.strategy_replay.kernel_adapter import (
    build_arbitration_context, compute_kernel_package_id
)
from market_radar.intelligence.strategy_replay.verified_input_adapter import adapt_macro_event


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]


def write_jsonl(records, path, sort_key=None):
    """Atomically write sorted JSONL — no append mode."""
    if path is None:
        return
    if sort_key:
        records = sorted(records, key=lambda r: r.get(sort_key, ""))
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def run_pilot_decisions():
    # ── Load inputs ──
    release_units = load_jsonl(OUT / "release_units_v1.jsonl")
    decision_inputs = load_jsonl(OUT / "decision_inputs_v1.jsonl")
    events = load_jsonl(UP / "lane_a_macro_release_events_v1.jsonl")

    print(f"Loaded: {len(events)} events, {len(release_units)} RUs, {len(decision_inputs)} DUs")

    # ── Macro strategies — all abstain (no consensus) ──
    macro_abstentions = []
    macro_results = []
    for e in events:
        adapted = adapt_macro_event(e)
        eid = adapted["event_id"]
        family = adapted["event_family"]
        strategy_id = f"strat_{family}"
        si_id = deterministic_id("si", [strategy_id, eid])
        abs_id = deterministic_id("abstain", [eid, strategy_id, "consensus_missing"])

        abstention = {
            "abstention_id": abs_id,
            "event_id": eid,
            "strategy_id": strategy_id,
            "strategy_instance_id": si_id,
            "reason_codes": ["consensus_missing"],
            "missing_inputs": ["consensus_value"],
            "point_in_time_quality": adapted.get("point_in_time_grade", "medium"),
            "information_cutoff_utc": adapted.get("release_time_utc", ""),
            "source_refs": [f"event:{eid}"],
        }
        macro_abstentions.append(abstention)

        result = {
            "replay_result_id": deterministic_id("rr", [si_id, "abstained"]),
            "event_id": eid,
            "strategy_id": strategy_id,
            "strategy_instance_id": si_id,
            "replay_status": "abstained",
            "strategy_state": "insufficient_evidence",
            "hypotheses": [],
            "abstention_record_id": abs_id,
            "kernel_package_id": "",
            "available_information_cutoff_utc": adapted.get("release_time_utc", ""),
            "generated_at_utc": None,
            "warnings": ["no_consensus_available"],
            "quality_flags": ["abstained_no_consensus"],
            "provenance_refs": [f"event:{eid}", f"strategy:{strategy_id}"],
        }
        macro_results.append(result)

    print(f"Macro: {len(macro_abstentions)} abstentions, 0 directional hypotheses")

    # ── Post-release continuation decisions ──
    reaction_results = []
    reaction_hypotheses = []
    reaction_kernel_packages = []
    reaction_abstentions = []

    for du in decision_inputs:
        du_id = du["decision_unit_id"]
        asset = du["asset"]
        signal_dir = du["signal_direction"]
        ru_id = du["release_unit_id"]
        eids = du["constituent_event_ids"]
        fams = du["event_families"]
        cutoff = du["information_cutoff_utc"]
        signal_return = du["signal_return_pct"]
        signal_endpoint_price = du["signal_endpoint_price"]
        window_id = du["signal_window_id"]
        ep_time = du["signal_endpoint_time_utc"]
        precision = du.get("precision_class", "coarse_hourly_alignment")

        si_id = deterministic_id("si", ["strat_post_release_reaction_continuation_v1", du_id])

        # Abstain if neutral
        if signal_dir == "neutral":
            abs_id = deterministic_id("abstain", [du_id, "first_reaction_neutral"])
            abstention = {
                "abstention_id": abs_id, "event_id": "|".join(eids),
                "strategy_id": "strat_post_release_reaction_continuation_v1",
                "strategy_instance_id": si_id,
                "reason_codes": ["first_reaction_neutral"],
                "missing_inputs": [],
                "point_in_time_quality": "medium",
                "information_cutoff_utc": cutoff,
                "source_refs": [f"decision_unit:{du_id}"],
            }
            reaction_abstentions.append(abstention)
            reaction_results.append({
                "replay_result_id": deterministic_id("rr", [si_id, "abstained"]),
                "event_id": "|".join(eids),
                "strategy_id": "strat_post_release_reaction_continuation_v1",
                "strategy_instance_id": si_id,
                "decision_unit_id": du_id,
                "release_unit_id": ru_id,
                "constituent_event_ids": eids,
                "event_families": fams,
                "asset": asset,
                "replay_status": "abstained",
                "strategy_state": "insufficient_evidence",
                "hypotheses": [],
                "abstention_record_id": abs_id,
                "kernel_package_id": "",
                "available_information_cutoff_utc": cutoff,
                "source_refs": [f"decision_unit:{du_id}"],
                "provenance_refs": [f"decision_unit:{du_id}"],
                "warnings": ["first_reaction_neutral"],
                "quality_flags": ["abstained_no_direction"],
                "generated_at_utc": None,
            })
            continue

        # Triggered: generate 2 distinct hypotheses
        expected_effect = "bullish" if signal_dir in ("positive",) else "bearish"

        # ── Hypothesis 1: continuation_to_4h ──
        hyp_4h = StrategyHypothesisV1(
            hypothesis_id=deterministic_id("hyp", [si_id, "continuation_to_4h"]),
            strategy_id="strat_post_release_reaction_continuation_v1",
            strategy_instance_id=si_id,
            event_id="|".join(eids),
            asset=asset,
            time_horizon="continuation_to_4h",
            expected_effect=expected_effect,
            strategy_state="triggered",
            market_confirmation="missing",
            transmission_signature=expected_effect,
            transmission_coherence="missing",
            transmission_conflicts=[],
            confidence_type="exploratory",
            supporting_evidence_refs=[f"window:{window_id}", f"decision_unit:{du_id}"],
            invalidation_conditions=["subsequent_macro_event_confounds"],
            alternative_explanations=["first_reaction_overreaction_reverses"],
            limitations=["small_pilot_sample", "no_historical_consensus", "coarse_hourly_alignment",
                        "post_release_strategy", "no_causal_claim"],
            release_unit_id=ru_id,
            constituent_event_ids=eids,
            event_families=fams,
            decision_unit_id=du_id,
            decision_cutoff_utc=cutoff,
            signal_window_id=window_id,
            signal_direction=signal_dir,
            signal_return_pct=signal_return,
            signal_endpoint_time_utc=ep_time,
            signal_endpoint_price=signal_endpoint_price,
            precision_class=precision,
        )

        # ── Hypothesis 2: continuation_to_24h ──
        hyp_24h = StrategyHypothesisV1(
            hypothesis_id=deterministic_id("hyp", [si_id, "continuation_to_24h"]),
            strategy_id="strat_post_release_reaction_continuation_v1",
            strategy_instance_id=si_id,
            event_id="|".join(eids),
            asset=asset,
            time_horizon="continuation_to_24h",
            expected_effect=expected_effect,
            strategy_state="triggered",
            market_confirmation="missing",
            transmission_signature=expected_effect,
            transmission_coherence="missing",
            transmission_conflicts=[],
            confidence_type="exploratory",
            supporting_evidence_refs=[f"window:{window_id}", f"decision_unit:{du_id}"],
            invalidation_conditions=["subsequent_macro_event_confounds"],
            alternative_explanations=["first_reaction_overreaction_reverses"],
            limitations=["small_pilot_sample", "no_historical_consensus", "coarse_hourly_alignment",
                        "post_release_strategy", "no_causal_claim"],
            release_unit_id=ru_id,
            constituent_event_ids=eids,
            event_families=fams,
            decision_unit_id=du_id,
            decision_cutoff_utc=cutoff,
            signal_window_id=window_id,
            signal_direction=signal_dir,
            signal_return_pct=signal_return,
            signal_endpoint_time_utc=ep_time,
            signal_endpoint_price=signal_endpoint_price,
            precision_class=precision,
        )

        hyp_ids = [hyp_4h.hypothesis_id, hyp_24h.hypothesis_id]
        reaction_hypotheses.extend([hyp_4h, hyp_24h])

        rr_id = deterministic_id("rr", [si_id, "triggered"])
        result = {
            "replay_result_id": rr_id,
            "event_id": "|".join(eids),
            "strategy_id": "strat_post_release_reaction_continuation_v1",
            "strategy_instance_id": si_id,
            "decision_unit_id": du_id,
            "release_unit_id": ru_id,
            "constituent_event_ids": eids,
            "event_families": fams,
            "asset": asset,
            "replay_status": "completed",
            "strategy_state": "triggered",
            "hypotheses": hyp_ids,
            "abstention_record_id": "",
            "kernel_package_id": "",
            "available_information_cutoff_utc": cutoff,
            "provenance_refs": [f"decision_unit:{du_id}"],
            "warnings": [],
            "quality_flags": ["pilot_sample", "exploratory"],
            "generated_at_utc": None,
        }
        reaction_results.append(result)

        # ── Kernel package with explicit distinct hypotheses ──
        kp_id = compute_kernel_package_id("|".join(eids), ["strat_post_release_reaction_continuation_v1"], hyp_ids)
        contexts = {}
        for h in [hyp_4h, hyp_24h]:
            ctx = build_arbitration_context(h, strategy_origin_group="post_release_reaction_continuation")
            contexts[h.hypothesis_id] = ctx.__dict__ if hasattr(ctx, "__dict__") else ctx

        kp = {
            "kernel_package_id": kp_id,
            "event_id": "|".join(eids),
            "asset": asset,
            "release_unit_id": ru_id,
            "decision_unit_id": du_id,
            "constituent_event_ids": eids,
            "event_families": fams,
            "hypotheses": [
                hyp_4h.__dict__,
                hyp_24h.__dict__,
            ],
            "hypothesis_contexts": contexts,
            "evidence_state": {"verdict": "exploratory_pilot", "validated": False},
            "regime_state": {"regime": "unknown", "usable_for_probability": False},
            "source_strategy_ids": ["strat_post_release_reaction_continuation_v1"],
            "source_replay_result_ids": [rr_id],
            "information_cutoff_utc": cutoff,
            "contract_versions": {"strategy_replay": "1.0.0", "pilot": "v3"},
            "quality_flags": ["small_sample", "coarse_hourly_alignment", "no_calibration"],
        }
        reaction_kernel_packages.append(kp)

    triggered = len([r for r in reaction_results if r["replay_status"] == "completed"])
    abstained = len([r for r in reaction_results if r["replay_status"] == "abstained"])
    hyp_count = len(reaction_hypotheses)
    kp_count = len(reaction_kernel_packages)

    print(f"Reaction: {len(reaction_results)} results ({triggered} triggered, {abstained} abstained)")
    print(f"  Hypotheses: {hyp_count} (expected {triggered * 2})")
    print(f"  Kernel packages: {kp_count}")

    # Verify no duplicate hypothesis in any kernel package
    for i, kp in enumerate(reaction_kernel_packages):
        hids = [h["hypothesis_id"] for h in kp["hypotheses"]]
        assert len(hids) == len(set(hids)), f"KP {kp['kernel_package_id']}: duplicate hypothesis IDs: {hids}"
        assert len(hids) == 2, f"KP {kp['kernel_package_id']}: expected 2 hypotheses, got {len(hids)}"

    print("  ✓ All kernel packages have 2 distinct hypotheses")

    # ── Write outputs ──
    write_jsonl(macro_abstentions, OUT / "macro_abstention_records_v1.jsonl", sort_key="abstention_id")
    write_jsonl(macro_results + reaction_results, OUT / "strategy_replay_results_v2.jsonl", sort_key="replay_result_id")
    write_jsonl([h.__dict__ for h in reaction_hypotheses], OUT / "strategy_hypotheses_v2.jsonl", sort_key="hypothesis_id")
    write_jsonl(reaction_kernel_packages, OUT / "kernel_input_packages_v2.jsonl", sort_key="kernel_package_id")
    if reaction_abstentions:
        write_jsonl(reaction_abstentions, OUT / "abstention_records_v2.jsonl", sort_key="abstention_id")

    print(f"\nStage 1 (decisions) complete.")
    return {
        "macro_instances": len(macro_results),
        "macro_abstentions": len(macro_abstentions),
        "macro_directional_hypotheses": 0,
        "reaction_results": len(reaction_results),
        "reaction_triggered": triggered,
        "reaction_abstained": abstained,
        "reaction_hypotheses": hyp_count,
        "reaction_kernel_packages": kp_count,
    }


if __name__ == "__main__":
    result = run_pilot_decisions()
    print(json.dumps(result, indent=2))
