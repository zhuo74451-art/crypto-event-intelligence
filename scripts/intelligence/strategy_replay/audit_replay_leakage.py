#!/usr/bin/env python
"""Audit replay outputs for future information leakage - V4 hardened."""
import json, sys, argparse, hashlib

def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def sha256_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def check_leakage(results_path, hypotheses_path, decision_inputs_path,
                  horizon_windows_path, decision_seal_path,
                  evaluation_outcomes_path=None, strategy_evaluations_path=None):
    violations = {"cutoff_mismatches": [], "non_1h_signal_windows": [],
                  "future_window_references": [], "evaluation_references": [],
                  "seal_hash_mismatches": [], "outcome_lineage_mismatches": []}
    vc = [0]

    def add_v(key, item):
        violations[key].append(item)
        vc[0] += 1

    results = load_jsonl(results_path)
    hypotheses = load_jsonl(hypotheses_path)
    decision_inputs = load_jsonl(decision_inputs_path)
    windows = load_jsonl(horizon_windows_path)
    seal = json.load(open(decision_seal_path, encoding="utf-8"))
    outcomes = load_jsonl(evaluation_outcomes_path) if evaluation_outcomes_path else []

    windows_by_id = {w["window_id"]: w for w in windows}
    di_by_id = {d["decision_unit_id"]: d for d in decision_inputs}
    hypotheses_by_id = {h["hypothesis_id"]: h for h in hypotheses}

    # 1. Decision seal
    seal_checks = {"checked": 4, "failures": 0}
    seal_map = {"decision_inputs_sha256": decision_inputs_path,
                "hypotheses_sha256": hypotheses_path,
                "replay_results_sha256": results_path}
    for key, path in seal_map.items():
        actual = sha256_file(path)
        expected = seal.get(key, "")
        if actual != expected:
            seal_checks["failures"] += 1
            add_v("seal_hash_mismatches", f"{key}: expected {expected[:16]} got {actual[:16]}")
    if not seal.get("sealed_before_evaluation", False):
        seal_checks["failures"] += 1
        add_v("seal_hash_mismatches", "sealed_before_evaluation is False")

    # 2. Decision Inputs
    for di in decision_inputs:
        duid = di.get("decision_unit_id", "")
        swid = di.get("signal_window_id", "")
        sh = di.get("signal_horizon", "")
        ic = di.get("information_cutoff_utc", "")
        sep = di.get("signal_endpoint_time_utc", "")
        if swid not in windows_by_id:
            add_v("future_window_references", f"DI {duid}: signal_window not in windows")
        elif sh != "1h":
            add_v("non_1h_signal_windows", f"DI {duid}: horizon={sh}")
        if ic and sep and ic != sep:
            add_v("cutoff_mismatches", f"DI {duid}: cutoff {ic} != endpoint {sep}")

    # 3. Hypotheses
    for h in hypotheses:
        hid = h.get("hypothesis_id", "")
        duid = h.get("decision_unit_id", "")
        swid = h.get("signal_window_id", "")
        dc = h.get("decision_cutoff_utc", "")
        sig_dir = h.get("signal_direction", "")
        di_obj = di_by_id.get(duid)
        if not di_obj:
            add_v("future_window_references", f"Hyp {hid}: decision_unit {duid} not found")
            continue
        if swid not in windows_by_id:
            add_v("future_window_references", f"Hyp {hid}: signal_window not in windows")
        elif windows_by_id[swid].get("nominal_horizon") != "1h":
            add_v("non_1h_signal_windows", f"Hyp {hid}: signal window not 1h")
        di_cutoff = di_obj.get("information_cutoff_utc", "")
        if dc and dc != di_cutoff:
            add_v("cutoff_mismatches", f"Hyp {hid}: cutoff {dc} != DI {di_cutoff}")
        di_swid = di_obj.get("signal_window_id", "")
        if swid and di_swid and swid != di_swid:
            add_v("future_window_references", f"Hyp {hid}: signal_window differs from DI")
        di_sig = di_obj.get("signal_direction", "")
        if sig_dir and di_sig and sig_dir != di_sig:
            add_v("cutoff_mismatches", f"Hyp {hid}: direction {sig_dir} != DI {di_sig}")
        for ref in h.get("supporting_evidence_refs", []) + h.get("opposing_evidence_refs", []):
            rl = ref.lower()
            if "4h" in rl or "24h" in rl or "evaluation" in rl or "outcome" in rl:
                add_v("future_window_references", f"Hyp {hid}: ref {ref[:60]}")

    # 4. Replay Results
    for rr in results:
        rrid = rr.get("replay_result_id", "")
        status = rr.get("replay_status", "")
        duid = rr.get("decision_unit_id", "")
        cutoff = rr.get("available_information_cutoff_utc", "")
        ref_hids = [h.get("hypothesis_id","") for h in rr.get("hypotheses",[]) if isinstance(h, dict)]
        if status == "completed":
            if duid not in di_by_id:
                add_v("future_window_references", f"RR {rrid}: decision_unit not found")
                continue
            dco = di_by_id[duid].get("information_cutoff_utc", "")
            if cutoff and cutoff != dco:
                add_v("cutoff_mismatches", f"RR {rrid}: cutoff != DI cutoff")
            for hid in ref_hids:
                if hid not in hypotheses_by_id:
                    add_v("future_window_references", f"RR {rrid}: hyp {hid} not found")
                else:
                    h = hypotheses_by_id[hid]
                    if h.get("decision_unit_id","") != duid:
                        add_v("future_window_references", f"RR {rrid}: hyp decision_unit mismatch")
                    hsw = h.get("signal_window_id","")
                    dws = di_by_id.get(duid,{}).get("signal_window_id","")
                    if hsw and dws and hsw != dws:
                        add_v("future_window_references", f"RR {rrid}: hyp signal_window mismatch")
        elif status == "abstained":
            if ref_hids:
                add_v("future_window_references", f"RR {rrid}: abstained but has hyp refs")
            if not rr.get("abstention_record_id",""):
                add_v("future_window_references", f"RR {rrid}: no abstention_record_id")

    # 5. Evaluation Outcomes
    for o in outcomes:
        oid = o.get("outcome_id", "")
        swid = o.get("signal_window_id", "")
        twid = o.get("target_window_id", "")
        if swid not in windows_by_id:
            add_v("outcome_lineage_mismatches", f"Outcome {oid}: signal_window not in windows")
        w = windows_by_id.get(swid, {})
        if w.get("nominal_horizon") != "1h":
            add_v("outcome_lineage_mismatches", f"Outcome {oid}: signal not 1h")
        if twid not in windows_by_id:
            add_v("outcome_lineage_mismatches", f"Outcome {oid}: target_window not in windows")
        if swid == twid:
            add_v("outcome_lineage_mismatches", f"Outcome {oid}: signal==target window")

    # 6. No eval refs in decisions/hypotheses
    eval_refs = {"evaluation_outcomes_v1.jsonl", "strategy_evaluations_v1.jsonl"}
    for di in decision_inputs:
        raw = json.dumps(di)
        for ref in eval_refs:
            if ref in raw:
                add_v("evaluation_references", f"DI {di.get('decision_unit_id','')} contains {ref}")

    return {"results_checked": len(results), "hypotheses_checked": len(hypotheses),
            "decision_inputs_checked": len(decision_inputs),
            "horizon_windows_indexed": len(windows),
            "evaluation_outcomes_checked": len(outcomes),
            "decision_seal_checks": seal_checks,
            "violations": violations, "violation_count": vc[0]}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--results", required=True)
    p.add_argument("--hypotheses", required=True)
    p.add_argument("--decision-inputs", required=True)
    p.add_argument("--horizon-windows", required=True)
    p.add_argument("--decision-seal", required=True)
    p.add_argument("--evaluation-outcomes", default=None)
    p.add_argument("--strategy-evaluations", default=None)
    a = p.parse_args()
    r = check_leakage(a.results, a.hypotheses, a.decision_inputs,
                      a.horizon_windows, a.decision_seal,
                      a.evaluation_outcomes, a.strategy_evaluations)
    print(json.dumps(r, indent=2))
    if r["violation_count"] > 0 or r["decision_seal_checks"]["failures"] > 0:
        sys.exit(1)
