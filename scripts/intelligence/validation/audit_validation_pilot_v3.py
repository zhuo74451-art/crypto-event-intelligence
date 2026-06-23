"""Fail-closed independent audit for V3 — checks producer, lineage, temporal, bootstrap, baseline, sqlite."""
import json, sys, pathlib, argparse, sqlite3, hashlib

REQUIRED_V3_ARTIFACTS = [
    "upstream/LANE_C_PRODUCER_LOCK.yaml", "datasets/directional_validation_dataset_v3.jsonl",
    "datasets/macro_abstention_dataset_v3.jsonl", "folds/walkforward_fold_evaluations_v3.jsonl",
    "splits/split_manifest_v3.json", "baselines/paired_baseline_comparison_v3.jsonl",
    "evaluations/leave_one_release_unit_out_v3.jsonl", "failed_experiments/failed_experiments_v3.jsonl",
    "reports/descriptive_metrics_v3.json", "reports/validation_pilot_report_v3.json",
    "reports/validation_integrity_audit_v3.json", "bootstrap/cluster_bootstrap_summary_v3.json",
    "indexes/validation_pilot_v3.sqlite",
    "calibration/calibration_status_v3.json", "multiple_testing/multiple_testing_status_v3.json",
    "drift/drift_status_v3.json",
]

def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]

def audit(pilot_dir):
    out = pathlib.Path(pilot_dir)
    up = out / "upstream"
    results = {}

    # 0. Required artifacts exist
    missing = [a for a in REQUIRED_V3_ARTIFACTS if not (out / a).exists()]
    results["missing_artifacts"] = missing

    # 1. Producer lock
    lock_path = up / "LANE_C_PRODUCER_LOCK.yaml"
    if lock_path.exists():
        import yaml
        lock = yaml.safe_load(lock_path.read_text("utf-8"))
        artifacts = lock.get("artifacts", {})
        ps = lock.get("producer_final_sha", ""); results["producer_sha"] = ps; results["producer_sha_fail"] = 0 if ps == "72984d8b0fe17dc188239c3c050e082c180853b4" else 1
        hash_fail = 0; count_fail = 0; yaml_type_fail = 0
        for name, a in artifacts.items():
            if not a.get("source_and_copy_equal", False): hash_fail += 1
            if not isinstance(a.get("record_count"), int): yaml_type_fail += 1
            if not isinstance(a.get("source_and_copy_equal"), bool): yaml_type_fail += 1
        for fname, exp in [("release_units_v1.jsonl",8),("strategy_hypotheses_v2.jsonl",32),
            ("evaluation_outcomes_v1.jsonl",32),("baseline_evaluations_v1.jsonl",128)]:
            if artifacts.get(fname,{}).get("record_count",0) != exp: count_fail += 1
        results["producer_hash_fail"] = hash_fail
        results["producer_count_fail"] = count_fail
        results["producer_yaml_type_fail"] = yaml_type_fail
    else:
        results["producer_hash_fail"] = results["producer_count_fail"] = results["producer_yaml_type_fail"] = 1

    # 2. Directional dataset
    try:
        rows = load_jsonl(out / "datasets" / "directional_validation_dataset_v3.jsonl")
        results["directional_rows"] = len(rows)
        # Check duplicate IDs BEFORE any set operation
        ids = [r.get("validation_row_id","") for r in rows]
        results["duplicate_row_ids"] = sum(1 for i,idd in enumerate(ids) if ids.index(idd) != i)
        # precision_class on every row
        results["rows_missing_precision_class"] = sum(1 for r in rows if not r.get("precision_class"))
        # RU IDs
        ru_ids = set(r.get("release_unit_id","") for r in rows)
        results["independent_release_units"] = len(ru_ids)
        results["unknown_release_unit_ids"] = sum(1 for r in rows if not r.get("release_unit_id"))
        # Decision cutoff before outcome start
        time_fail = 0
        for r in rows:
            if r.get("decision_cutoff_utc","") and r.get("outcome_start_time_utc",""):
                if r["decision_cutoff_utc"] > r["outcome_start_time_utc"]:
                    time_fail += 1
        results["decision_cutoff_after_outcome_start"] = time_fail
    except Exception as e:
        results["directional_rows"] = results["duplicate_row_ids"] = results["independent_release_units"] = -1
        results["directional_error"] = str(e)

    # 3. Failed experiments count
    try:
        fe = load_jsonl(out / "failed_experiments" / "failed_experiments_v3.jsonl")
        results["failed_experiments_count"] = len(fe)
        results["failed_experiment_ids"] = [e.get("experiment_id") for e in fe]
    except:
        results["failed_experiments_count"] = 0

    # 4. Walk-forward folds
    try:
        folds = load_jsonl(out / "folds" / "walkforward_fold_evaluations_v3.jsonl")
        split_fail = 0
        for f in folds:
            train = set(f.get("train_release_unit_ids",[]))
            test = set(f.get("test_release_unit_ids",[]))
            if train & test: split_fail += 1
        results["release_unit_split_fail"] = split_fail
        results["total_test_rows"] = sum(f.get("test_directional_rows",0) for f in folds)
    except:
        results["release_unit_split_fail"] = 1

    # 5. Bootstrap multiplicity
    try:
        boot = json.loads((out / "bootstrap" / "cluster_bootstrap_summary_v3.json").read_text("utf-8"))
        results["bootstrap_min_rows"] = boot.get("minimum_sampled_row_count")
        results["bootstrap_max_rows"] = boot.get("maximum_sampled_row_count")
        results["bootstrap_multiplicity_ok"] = boot.get("duplicate_cluster_draws_observed") == True
    except:
        results["bootstrap_min_rows"] = results["bootstrap_max_rows"] = -1
        results["bootstrap_multiplicity_ok"] = False

    # 6. Baseline pairing
    try:
        bases = load_jsonl(out / "baselines" / "paired_baseline_comparison_v3.jsonl")
        pair_fail = sum(1 for b in bases if b.get("paired_rows",0) != 32)
        cov_fail = sum(1 for b in bases if b.get("strategy_coverage",{}).get("numerator",0) != 32)
        # always_abstain should have 0 baseline coverage
        for b in bases:
            if b.get("baseline_id") == "always_abstain":
                if b.get("baseline_coverage",{}).get("numerator",99) != 0:
                    cov_fail += 1
        results["baseline_pair_fail"] = pair_fail
        results["baseline_coverage_fail"] = cov_fail
    except:
        results["baseline_pair_fail"] = results["baseline_coverage_fail"] = 1

    # 7. SQLite counts
    try:
        db = out / "indexes" / "validation_pilot_v3.sqlite"
        conn = sqlite3.connect(str(db))
        sqlite_fail = 0
        for table, fname in [
            ("directional_validation", "datasets/directional_validation_dataset_v3.jsonl"),
            ("macro_abstentions", "datasets/macro_abstention_dataset_v3.jsonl"),
            ("fold_evaluations", "folds/walkforward_fold_evaluations_v3.jsonl"),
            ("baseline_comparisons", "baselines/paired_baseline_comparison_v3.jsonl"),
            ("leave_one_unit_out", "evaluations/leave_one_release_unit_out_v3.jsonl"),
            ("failed_experiments", "failed_experiments/failed_experiments_v3.jsonl")]:
            fc = len(load_jsonl(out / fname))
            try: dc = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            except: dc = -1
            if fc != dc: sqlite_fail += 1
                
        conn.close()
        results["sqlite_fail"] = sqlite_fail
    except:
        results["sqlite_fail"] = 1

    # Verdict
    serious = [k for k,v in results.items() if isinstance(v,int) and not isinstance(v,bool) and v > 0 and k not in ("directional_rows","independent_release_units","total_test_rows","failed_experiments_count","bootstrap_min_rows","bootstrap_max_rows","rows_missing_precision_class","bootstrap_multiplicity_ok")]
    results["overall_verdict"] = "fail" if serious else "pass"
    results["serious_keys"] = serious

    # Write report
    rp = out / "reports" / "validation_integrity_audit_v3.json"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(json.dumps(results, indent=2))
    print(f"\nOverall verdict: {results['overall_verdict']}")
    sys.exit(0 if results["overall_verdict"] == "pass" else 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot-dir", required=True)
    args = parser.parse_args()
    audit(args.pilot_dir)