
import json, sys, pathlib, argparse, sqlite3, hashlib, yaml

LANE_C_SHA = "72984d8b0fe17dc188239c3c050e082c180853b4"

def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]

def audit(pilot_dir):
    out = pathlib.Path(pilot_dir)
    up = out / "upstream"
    reasons = {}

    # 0. Required artifacts
    REQUIRED = [
        "upstream/LANE_C_PRODUCER_LOCK.yaml", "datasets/directional_validation_dataset_v3.jsonl",
        "datasets/macro_abstention_dataset_v3.jsonl", "folds/walkforward_fold_evaluations_v3.jsonl",
        "splits/split_manifest_v3.json", "baselines/paired_baseline_comparison_v3.jsonl",
        "evaluations/leave_one_release_unit_out_v3.jsonl", "failed_experiments/failed_experiments_v3.jsonl",
        "reports/descriptive_metrics_v3.json", "reports/validation_pilot_report_v3.json",
        "bootstrap/cluster_bootstrap_summary_v3.json", "indexes/validation_pilot_v3.sqlite",
    ]
    missing = [a for a in REQUIRED if not (out / a).exists()]
    if missing:
        reasons["missing_artifacts"] = missing

    # 1. Producer lock — recompute SHA-256 from actual files
    lock_path = up / "LANE_C_PRODUCER_LOCK.yaml"
    if not lock_path.exists():
        reasons["producer_lock_missing"] = True
    else:
        lock = yaml.safe_load(lock_path.read_text("utf-8"))
        artifacts = lock.get("artifacts", {})

        if lock.get("producer_final_sha") != LANE_C_SHA:
            reasons["producer_sha_mismatch"] = lock.get("producer_final_sha")

        # Real hash recomputation — don't trust source_and_copy_equal
        hash_mismatches = []
        for fname, a in artifacts.items():
            expected = a.get("actual_git_object_sha256", "")
            actual_file = up / fname
            if actual_file.exists():
                actual_hash = hashlib.sha256(actual_file.read_bytes()).hexdigest()
                if actual_hash != expected:
                    hash_mismatches.append(fname)
            else:
                hash_mismatches.append(f"{fname}_file_missing")
        if hash_mismatches:
            reasons["producer_hash_mismatch"] = hash_mismatches

        # YAML types
        yaml_fail = []
        for fname, a in artifacts.items():
            if not isinstance(a.get("source_and_copy_equal"), bool):
                yaml_fail.append(f"{fname}_bool")
            if not isinstance(a.get("record_count"), int):
                yaml_fail.append(f"{fname}_int")
        if yaml_fail:
            reasons["producer_yaml_type_invalid"] = yaml_fail

        # Record counts
        count_fail = []
        for fname, exp in [("release_units_v1.jsonl", 8), ("strategy_hypotheses_v2.jsonl", 32),
            ("evaluation_outcomes_v1.jsonl", 32), ("baseline_evaluations_v1.jsonl", 128)]:
            if artifacts.get(fname, {}).get("record_count", 0) != exp:
                count_fail.append(fname)
        if count_fail:
            reasons["producer_record_count_mismatch"] = count_fail

    # 2. Directional dataset invariants
    try:
        rows = load_jsonl(out / "datasets" / "directional_validation_dataset_v3.jsonl")
        if len(rows) != 32:
            reasons["directional_row_count"] = len(rows)

        # Duplicate IDs — index check, not set dedup
        seen = {}
        dups = []
        for i, r in enumerate(rows):
            vid = r.get("validation_row_id", "")
            if vid in seen:
                dups.append({"line": i, "id": vid, "first_line": seen[vid]})
            seen[vid] = i
        if dups:
            reasons["duplicate_validation_row_id"] = dups

        # precision_class on every row
        missing_pc = [i for i, r in enumerate(rows) if not r.get("precision_class")]
        if missing_pc:
            reasons["missing_precision_class_rows"] = missing_pc

        # release_unit_ids
        ru_ids = set(r.get("release_unit_id", "") for r in rows)
        if len(ru_ids) != 8:
            reasons["independent_release_units"] = len(ru_ids)
        unknown_ru = [r.get("release_unit_id") for r in rows if not r.get("release_unit_id")]
        if unknown_ru:
            reasons["unknown_release_unit_ids"] = unknown_ru

        # decision_cutoff <= outcome_start
        time_fail = []
        for i, r in enumerate(rows):
            dc = r.get("decision_cutoff_utc", "")
            os = r.get("outcome_start_time_utc", "")
            if dc and os and dc > os:
                time_fail.append({"row": i, "cutoff": dc, "start": os})
        if time_fail:
            reasons["decision_cutoff_after_outcome_start"] = time_fail
    except Exception as e:
        reasons["directional_dataset_error"] = str(e)

    # 3. Failed experiments
    try:
        fe = load_jsonl(out / "failed_experiments" / "failed_experiments_v3.jsonl")
        if len(fe) != 6:
            reasons["failed_experiments_count"] = len(fe)
        expected_ids = {"naive_random_row_split", "unclustered_row_bootstrap",
            "probability_claim_without_probability_scores",
            "significance_claim_with_insufficient_release_units",
            "full_walkforward_claim_on_partial_folds", "causal_claim_from_observational_pilot"}
        actual_ids = set(e.get("experiment_id", "") for e in fe)
        if actual_ids != expected_ids:
            reasons["failed_experiment_ids_mismatch"] = {
                "missing": list(expected_ids - actual_ids),
                "extra": list(actual_ids - expected_ids)}
    except Exception as e:
        reasons["failed_experiments_error"] = str(e)

    # 4. Walkforward folds
    try:
        folds = load_jsonl(out / "folds" / "walkforward_fold_evaluations_v3.jsonl")
        total_test = sum(f.get("test_directional_rows", 0) for f in folds)
        if total_test != 16:
            reasons["total_test_rows"] = total_test
        for f in folds:
            train = set(f.get("train_release_unit_ids", []))
            test = set(f.get("test_release_unit_ids", []))
            if train & test:
                reasons.setdefault("walkforward_release_unit_leakage", []).append(
                    f.get("fold_id", ""))
    except Exception as e:
        reasons["walkforward_error"] = str(e)

    # 5. Bootstrap multiplicity
    try:
        boot = json.loads((out / "bootstrap" / "cluster_bootstrap_summary_v3.json").read_text("utf-8"))
        if boot.get("minimum_sampled_row_count", 0) != 32:
            reasons["bootstrap_min_rows"] = boot.get("minimum_sampled_row_count")
        if boot.get("maximum_sampled_row_count", 0) != 32:
            reasons["bootstrap_max_rows"] = boot.get("maximum_sampled_row_count")
        if boot.get("duplicate_cluster_draws_observed") is not True:
            reasons["bootstrap_multiplicity_not_preserved"] = True
    except Exception as e:
        reasons["bootstrap_error"] = str(e)

    # 6. Baseline pairing and coverage
    try:
        bases = load_jsonl(out / "baselines" / "paired_baseline_comparison_v3.jsonl")
        pair_fail = [b.get("baseline_id") for b in bases if b.get("paired_rows", 0) != 32]
        if pair_fail:
            reasons["baseline_pairing_mismatch"] = pair_fail
        for b in bases:
            sc = b.get("strategy_coverage", {})
            bc = b.get("baseline_coverage", {})
            bid = b.get("baseline_id", "")
            if sc.get("numerator", 0) != 32:
                reasons.setdefault("baseline_coverage_mismatch", []).append(f"{bid}_strategy_coverage")
            if bid == "always_abstain":
                if bc.get("numerator", -1) != 0:
                    reasons.setdefault("baseline_coverage_mismatch", []).append(f"{bid}_abstain_coverage")
            else:
                if bc.get("numerator", 0) != 32:
                    reasons.setdefault("baseline_coverage_mismatch", []).append(f"{bid}_baseline_coverage")
    except Exception as e:
        reasons["baseline_error"] = str(e)

    # 7. SQLite counts
    try:
        db = out / "indexes" / "validation_pilot_v3.sqlite"
        conn = sqlite3.connect(str(db))
        sqlite_fail = []
        for table, fname in [("directional_validation", "datasets/directional_validation_dataset_v3.jsonl"),
            ("macro_abstentions", "datasets/macro_abstention_dataset_v3.jsonl"),
            ("fold_evaluations", "folds/walkforward_fold_evaluations_v3.jsonl"),
            ("baseline_comparisons", "baselines/paired_baseline_comparison_v3.jsonl"),
            ("leave_one_unit_out", "evaluations/leave_one_release_unit_out_v3.jsonl"),
            ("failed_experiments", "failed_experiments/failed_experiments_v3.jsonl")]:
            fc = len(load_jsonl(out / fname))
            dc = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            if fc != dc:
                sqlite_fail.append(f"{table}: file={fc} db={dc}")
        conn.close()
        if sqlite_fail:
            reasons["sqlite_count_mismatch"] = sqlite_fail
    except Exception as e:
        reasons["sqlite_error"] = str(e)

    # Verdict — explicit invariant list
    invariant_checks = [
        "missing_artifacts", "producer_sha_mismatch", "producer_hash_mismatch",
        "producer_record_count_mismatch", "producer_yaml_type_invalid",
        "directional_row_count", "duplicate_validation_row_id",
        "missing_precision_class_rows", "independent_release_units",
        "unknown_release_unit_ids", "decision_cutoff_after_outcome_start",
        "failed_experiments_count", "failed_experiment_ids_mismatch",
        "total_test_rows", "walkforward_release_unit_leakage",
        "bootstrap_min_rows", "bootstrap_max_rows",
        "bootstrap_multiplicity_not_preserved",
        "baseline_pairing_mismatch", "baseline_coverage_mismatch",
        "sqlite_count_mismatch",
    ]
    present = [k for k in invariant_checks if k in reasons]
    reasons["overall_verdict"] = "fail" if present else "pass"
    reasons["failed_invariants"] = present

    # Write report
    rp = out / "reports" / "validation_integrity_audit_v3.json"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(reasons, indent=2), encoding="utf-8")

    print(json.dumps(reasons, indent=2))
    print(f"\nOverall verdict: {reasons['overall_verdict']}")
    sys.exit(0 if reasons["overall_verdict"] == "pass" else 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot-dir", required=True)
    args = parser.parse_args()
    audit(args.pilot_dir)
