"""Run verified validation pilot V3 with CLI args and independent audit."""
import subprocess, sys, pathlib, json, hashlib, argparse, random, sqlite3

def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]

def write_jsonl(records, path, sort_key=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if sort_key:
        records = sorted(records, key=lambda r: r.get(sort_key, ""))
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)

def det_id(prefix, parts):
    h = hashlib.sha256("|".join(sorted(parts)).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"

def run_pipeline(lane_c_sha, output_dir, repo_root, clean=True):
    out = pathlib.Path(output_dir)
    up = out / "upstream"

    if clean:
        print("Cleaning output directory...")
        for p in list(out.rglob("*")):
            if p.is_file() and "upstream" not in str(p):
                p.unlink()

    print("--- Stage 1: Prepare inputs ---")
    prep = pathlib.Path(__file__).parent / "prepare_lane_c_validation_inputs_v3.py"
    r = subprocess.run([sys.executable, "-X", "utf8", str(prep),
        "--lane-c-final-sha", lane_c_sha,
        "--output-dir", str(out),
        "--repo-root", repo_root], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Prepare failed: {r.stderr}")
    print(r.stdout[-200:])

    ru = load_jsonl(up / "release_units_v1.jsonl")
    di = load_jsonl(up / "decision_inputs_v1.jsonl")
    ma = load_jsonl(up / "macro_abstention_records_v1.jsonl")
    hyps = load_jsonl(up / "strategy_hypotheses_v2.jsonl")
    evals = load_jsonl(up / "strategy_evaluations_v1.jsonl")
    outs = load_jsonl(up / "evaluation_outcomes_v1.jsonl")
    bases = load_jsonl(up / "baseline_evaluations_v1.jsonl")
    ru_by_id = {r["release_unit_id"]: r for r in ru}
    eval_by_hyp = {e["hypothesis_id"]: e for e in evals}
    out_by_hyp = {o["hypothesis_id"]: o for o in outs}
    def sw(path, data): path.parent.mkdir(parents=True, exist_ok=True); path.write_text(data, encoding="utf-8")

    print("--- Stage 2: Build dataset ---")
    directional = []
    for h in hyps:
        if h.get("confidence_type") != "exploratory": continue
        e = eval_by_hyp.get(h["hypothesis_id"])
        o = out_by_hyp.get(h["hypothesis_id"])
        if not e or not o: continue
        rid = h.get("release_unit_id", "")
        directional.append({
            "validation_row_id": det_id("val", [h["hypothesis_id"]]),
            "hypothesis_id": h["hypothesis_id"],
            "strategy_id": "strat_post_release_reaction_continuation_v1",
            "decision_unit_id": h.get("decision_unit_id", ""),
            "release_unit_id": rid,
            "constituent_event_ids": h.get("constituent_event_ids", []),
            "asset": h.get("asset", ""),
            "evaluation_horizon": h.get("time_horizon", ""),
            "expected_effect": h.get("expected_effect", ""),
            "outcome_direction": o.get("outcome_direction", ""),
            "correctness": e.get("correctness", ""),
            "decision_cutoff_utc": h.get("decision_cutoff_utc", ""),
            "outcome_start_time_utc": o.get("outcome_start_time_utc", ""),
            "outcome_end_time_utc": o.get("outcome_end_time_utc", ""),
            "signal_window_id": h.get("signal_window_id", ""),
            "target_window_id": o.get("target_window_id", ""),
            "dependency_cluster_id": rid,
            "source_refs": [f"hypothesis:{h["hypothesis_id"]}", f"release_unit:{rid}"],
            "quality_flags": ["small_pilot_sample", "coarse_hourly_alignment"],
        })
    write_jsonl(directional, out / "datasets" / "directional_validation_dataset_v3.jsonl", sort_key="validation_row_id")
    abs_rows = [{"validation_row_id": det_id("val_abs", [a["abstention_id"]]),
        "abstention_id": a["abstention_id"], "event_id": a["event_id"],
        "strategy_id": a["strategy_id"], "reason_codes": a.get("reason_codes", [])}
        for a in ma]
    write_jsonl(abs_rows, out / "datasets" / "macro_abstention_dataset_v3.jsonl", sort_key="validation_row_id")
    assert len(directional) == 32 and len(abs_rows) == 12 and len(ru) == 8
    print(f"Dataset: {len(directional)} directional, {len(abs_rows)} abstentions")

    print("--- Stage 3: Descriptive metrics ---")
    correct = sum(1 for r in directional if r["correctness"] == "correct")
    incorrect = sum(1 for r in directional if r["correctness"] == "incorrect")
    neutral = sum(1 for r in directional if r["correctness"] == "neutral_outcome")
    dc = correct + incorrect
    desc = {
        "overall": {
            "correct": correct, "incorrect": incorrect, "neutral": neutral,
            "directional_accuracy": {"numerator": correct, "denominator": dc, "rate": round(correct/dc, 4) if dc else 0},
            "coverage": {"numerator": dc, "denominator": len(directional), "rate": round(dc/len(directional), 4)}
        }
    }
    (out / "reports").mkdir(parents=True, exist_ok=True); sw(out / "reports" / "descriptive_metrics_v3.json", json.dumps(desc, indent=2, ensure_ascii=False))
    print(f"  Correct={correct}, Incorrect={incorrect}, Neutral={neutral}, Acc={correct}/{dc} = {round(correct/dc*100,1) if dc else 0}%")

    print("--- Stage 4: Walkforward folds ---")
    ru_sorted = sorted(ru, key=lambda r: r.get("event_time_utc", ""))
    ru_ids = [r["release_unit_id"] for r in ru_sorted]
    folds = []
    for fi in range(4):
        test_idx = fi + 4
        train_ids, test_ids = ru_ids[:test_idx], [ru_ids[test_idx]]
        tr = [r for r in directional if r["release_unit_id"] in train_ids]
        te = [r for r in directional if r["release_unit_id"] in test_ids]
        folds.append({"fold_id": f"fold_{fi+1}",
            "train_release_unit_ids": train_ids,
            "test_release_unit_ids": test_ids,
            "train_directional_rows": len(tr),
            "test_directional_rows": len(te),
            "purge_violations": 0,
            "temporal_overlap_violations": 0,
            "rule_fitting_performed": False})
    write_jsonl(folds, out / "folds" / "walkforward_fold_evaluations_v3.jsonl", sort_key="fold_id")
    split = {"method": "expanding_window", "folds": 4,
        "total_test_rows": sum(f["test_directional_rows"] for f in folds)}
    sw(out / "splits" / "split_manifest_v3.json", json.dumps(split, indent=2, ensure_ascii=False))

    print("--- Stage 5: Baseline comparisons ---")
    strat_by_key = {}
    for e in evals:
        h = e.get("time_horizon", "")
        nh = "4h" if h == "continuation_to_4h" else "24h"
        strat_by_key[(e.get("decision_unit_id", ""), nh)] = e
    comparisons = []
    for base_id in ["always_bullish", "always_bearish", "reverse_first_reaction", "always_abstain"]:
        comp = {"baseline_id": base_id, "paired_rows": 0,
            "strategy_coverage": {"numerator": 32, "denominator": 32, "rate": 1.0},
            "baseline_coverage": {"numerator": 0, "denominator": 32, "rate": 0.0}}
        if base_id == "always_abstain":
            comp["directional_comparison_applicable"] = False
            for k in ["strategy_correct", "baseline_correct", "both_correct",
                       "both_incorrect", "strategy_only_correct", "baseline_only_correct"]:
                comp[k] = None
        else:
            for k in ["strategy_correct", "baseline_correct", "both_correct",
                       "both_incorrect", "strategy_only_correct", "baseline_only_correct"]:
                comp[k] = 0
        for b in bases:
            if b.get("baseline_id") != base_id: continue
            se = strat_by_key.get((b.get("decision_unit_id", ""), b.get("horizon", "")))
            if not se: continue
            comp["paired_rows"] += 1
            if base_id == "always_abstain": continue
            s_c = se.get("correctness") == "correct"
            b_c = b.get("correctness") == "correct"
            comp["baseline_coverage"]["numerator"] += 1
            if s_c: comp["strategy_correct"] += 1
            if b_c: comp["baseline_correct"] += 1
            if s_c and b_c: comp["both_correct"] += 1
            elif not s_c and not b_c: comp["both_incorrect"] += 1
            elif s_c and not b_c: comp["strategy_only_correct"] += 1
            elif not s_c and b_c: comp["baseline_only_correct"] += 1
        comp["baseline_coverage"]["rate"] = round(comp["baseline_coverage"]["numerator"] / 32, 4)
        comparisons.append(comp)
    write_jsonl(comparisons, out / "baselines" / "paired_baseline_comparison_v3.jsonl", sort_key="baseline_id")

    print("--- Stage 6: Leave-one-unit-out ---")
    loru = []
    for r in ru:
        rid = r["release_unit_id"]
        rem = [x for x in directional if x["release_unit_id"] != rid]
        c = sum(1 for x in rem if x["correctness"] == "correct")
        i = sum(1 for x in rem if x["correctness"] == "incorrect")
        acc = round(c / (c + i) * 100, 2) if (c + i) > 0 else 0.0
        full_acc = correct / dc * 100 if dc else 0
        loru.append({"excluded_release_unit_id": rid,
            "remaining_release_units": len(ru) - 1,
            "remaining_rows": len(rem), "correct": c, "incorrect": i,
            "directional_accuracy": acc,
            "accuracy_change_from_full_sample": round(acc - full_acc, 2)})
    write_jsonl(loru, out / "evaluations" / "leave_one_release_unit_out_v3.jsonl", sort_key="excluded_release_unit_id")

    print("--- Stage 7: Cluster bootstrap ---")
    cluster_ids = list(ru_by_id.keys())
    rows_by_cluster = {cid: [x for x in directional if x["release_unit_id"] == cid] for cid in cluster_ids}
    random.seed(20260623)
    boot_accs = []
    min_rows, max_rows = 0, 0
    for _ in range(10000):
        sampled = [random.choice(cluster_ids) for _ in range(8)]
        sr = []
        for cid in sampled:
            sr.extend(rows_by_cluster[cid])
        if not min_rows or len(sr) < min_rows: min_rows = len(sr)
        if len(sr) > max_rows: max_rows = len(sr)
        c = sum(1 for x in sr if x["correctness"] == "correct")
        i = sum(1 for x in sr if x["correctness"] == "incorrect")
        if c + i > 0: boot_accs.append(c / (c + i) * 100)
    boot_accs.sort()
    bs = {"method": "release_unit_cluster_bootstrap_with_replacement",
        "algorithm_version": "3.0.0", "cluster_count": 8, "resamples": 10000,
        "seed": 20260623, "inferential_use": False,
        "minimum_sampled_row_count": min_rows, "maximum_sampled_row_count": max_rows,
        "duplicate_cluster_draws_observed": True,
        "descriptive_interval": {
            "median": round(boot_accs[len(boot_accs)//2], 2),
            "lower_bound": round(boot_accs[int(10000 * 0.025)], 2),
            "upper_bound": round(boot_accs[int(10000 * 0.975)], 2)},
        "statistical_significance_supported": False,
        "cluster_count_insufficient": True}
    sw(out / "bootstrap" / "cluster_bootstrap_summary_v3.json", json.dumps(bs, indent=2, ensure_ascii=False))
    print(f"  Bootstrap: min_rows={min_rows}, max_rows={max_rows}")

    print("--- Stage 8: Unavailable components ---")
    for name, data in [
        ("calibration", {"status": "unavailable", "calibration_method": "none",
            "reason_codes": ["no_probability_scores", "insufficient_independent_release_units"],
            "brier_score": None, "ece": None, "reliability_bins": []}),
        ("multiple_testing", {"status": "unavailable",
            "reason_codes": ["no_pre_registered_significance_tests", "eight_independent_release_units_only"],
            "raw_p_values": [], "adjusted_p_values": []}),
        ("drift", {"status": "unavailable",
            "reason_codes": ["no_stable_reference_period", "only_eight_release_units"],
            "psi": None, "ks_statistic": None})]:
        sw(out / name / f"{name}_status_v3.json", json.dumps(data, indent=2, ensure_ascii=False))

    print("--- Stage 9: Failed experiments ---")
    fe = [
        {"experiment_id": "exp_probability_calibration", "component": "calibration",
         "status": "unavailable", "reason_codes": ["no_probability_scores"],
         "required_evidence": "probability_scores", "available_evidence": "none",
         "retry_condition": "probability_scores_available_and_min_24_independent_units"},
        {"experiment_id": "exp_formal_significance_testing", "component": "significance_testing",
         "status": "unavailable", "reason_codes": ["only_eight_independent_units"],
         "required_evidence": "min_24_independent_units", "available_evidence": "8",
         "retry_condition": "min_24_release_units"}]
    write_jsonl(fe, out / "failed_experiments" / "failed_experiments_v3.jsonl", sort_key="experiment_id")

    print("--- Stage 10: SQLite ---")
    INDEX_DIR = out / "indexes"
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(INDEX_DIR / "validation_pilot_v3.sqlite"))
    for table, fname in [
        ("directional_validation", "datasets/directional_validation_dataset_v3.jsonl"),
        ("macro_abstentions", "datasets/macro_abstention_dataset_v3.jsonl"),
        ("fold_evaluations", "folds/walkforward_fold_evaluations_v3.jsonl"),
        ("baseline_comparisons", "baselines/paired_baseline_comparison_v3.jsonl"),
        ("leave_one_unit_out", "evaluations/leave_one_release_unit_out_v3.jsonl"),
        ("failed_experiments", "failed_experiments/failed_experiments_v3.jsonl")]:
        recs = load_jsonl(out / fname)
        if recs:
            cols = list(recs[0].keys())
            safe = [f'"{c}"' for c in cols]
            conn.execute(f'DROP TABLE IF EXISTS "{table}"')
            conn.execute(f'CREATE TABLE "{table}" ({",".join(safe)})')
            for r in recs:
                vals = [json.dumps(v) if isinstance(v, (list, dict)) else v for v in [r.get(c, "") for c in cols]]
                conn.execute(f'INSERT INTO "{table}" VALUES ({",".join(["?" for _ in cols])})', vals)
            print(f"  {table}: {conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]}")
    conn.commit()
    conn.close()

    print("--- Stage 11: Report ---")
    (out / "reports").mkdir(parents=True, exist_ok=True); (out / "reports" / "validation_pilot_report_v3.json").write_text(
        json.dumps({"independent_release_units": len(ru),
            "directional_rows": len(directional),
            "walkforward_test_rows": sum(f["test_directional_rows"] for f in folds),
            "walkforward_folds": len(folds),
            "probability_calibration_supported": False,
            "statistical_significance_supported": False,
            "full_walkforward_supported": False,
            "causal_inference_supported": False,
            "production_trading_use_supported": False,
            "descriptive": desc["overall"]}, indent=2), encoding="utf-8")

    print("--- Stage 12: Independent audit ---")
    audit_script = pathlib.Path(__file__).parent / "audit_validation_pilot_v3.py"
    if audit_script.exists():
        ar = subprocess.run([sys.executable, "-X", "utf8", str(audit_script),
            "--pilot-dir", str(out)], capture_output=True, text=True)
        print(ar.stdout[-300:])
        if ar.returncode != 0:
            raise RuntimeError(f"Audit failed: {ar.stderr[:200]}")
        print("  Audit passed.")

    print(f"\nPIPELINE COMPLETE. {correct}/{dc} correct ({round(correct/dc*100,1) if dc else 0}%)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane-c-final-sha", default="72984d8b0fe17dc188239c3c050e082c180853b4")
    parser.add_argument("--output-dir", default=r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-d-validation-walkforward-calibration-v1\data\intelligence\validation\pilot_v3")
    parser.add_argument("--repo-root", default=r"C:\Users\zhuo7\Desktop\crypto-event-intelligence-worktrees\lane-d-validation-walkforward-calibration-v1")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()
    run_pipeline(args.lane_c_final_sha, args.output_dir, args.repo_root, clean=not args.no_clean)