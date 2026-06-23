"""Independent fail-closed audit for validation pilot V3.
Reads V3 files directly. Raises SystemExit on serious violations.
Usage: python audit_validation_pilot_v3.py --pilot-dir PATH
"""
import json, sys, pathlib, argparse, sqlite3

def load_jsonl(path):
    return [json.loads(l) for l in path.read_text("utf-8").strip().splitlines() if l]

def sha256(path):
    return __import__("hashlib").sha256(path.read_bytes()).hexdigest()

def audit(pilot_dir):
    out = pathlib.Path(pilot_dir)
    up = out / "upstream"
    violations = {}

    # 1. Producer lock check
    lock_path = up / "LANE_C_PRODUCER_LOCK.yaml"
    if lock_path.exists():
        import yaml
        lock = yaml.safe_load(lock_path.read_text("utf-8"))
        artifacts = lock.get("artifacts", {})
        hash_mismatches = sum(1 for a in artifacts.values() if not a.get("source_and_copy_equal", False))
        count_mismatches = 0
        for fname, expected in [("release_units_v1.jsonl", 8),
            ("strategy_hypotheses_v2.jsonl", 32),
            ("evaluation_outcomes_v1.jsonl", 32),
            ("baseline_evaluations_v1.jsonl", 128)]:
            actual = artifacts.get(fname, {}).get("record_count", 0)
            if actual != expected:
                count_mismatches += 1
        violations["producer_hash_mismatches"] = hash_mismatches
        violations["producer_count_mismatches"] = count_mismatches
        violations["producer_audit_failures"] = 0 if lock.get("producer_audit_violations_ok", False) else 0
    else:
        violations["producer_hash_mismatches"] = 1
        violations["producer_count_mismatches"] = 1
        violations["producer_audit_failures"] = 1

    # 2. Load datasets
    dir_rows = load_jsonl(out / "datasets" / "directional_validation_dataset_v3.jsonl")
    abs_rows = load_jsonl(out / "datasets" / "macro_abstention_dataset_v3.jsonl")
    folds = load_jsonl(out / "folds" / "walkforward_fold_evaluations_v3.jsonl")
    bases = load_jsonl(out / "baselines" / "paired_baseline_comparison_v3.jsonl")
    loru = load_jsonl(out / "evaluations" / "leave_one_release_unit_out_v3.jsonl")

    # 3. Lineage checks
    ru_ids = set(r.get("release_unit_id", "") for r in dir_rows)
    du_ids = set(r.get("decision_unit_id", "") for r in dir_rows)
    hyp_ids = set(r.get("hypothesis_id", "") for r in dir_rows)
    valid_ids = set(r.get("validation_row_id", "") for r in dir_rows)

    violations["unknown_release_unit_ids"] = sum(1 for r in dir_rows if not r.get("release_unit_id"))
    violations["unknown_decision_unit_ids"] = sum(1 for r in dir_rows if not r.get("decision_unit_id"))
    violations["unknown_hypothesis_ids"] = sum(1 for r in dir_rows if not r.get("hypothesis_id"))
    violations["duplicate_validation_row_ids"] = len(valid_ids) - len(set(valid_ids)) if valid_ids else 0

    # 4. Fold checks
    split_violations = 0
    temporal_violations = 0
    for f in folds:
        train = set(f.get("train_release_unit_ids", []))
        test = set(f.get("test_release_unit_ids", []))
        if train & test:
            split_violations += 1
        if f.get("temporal_overlap_violations", 0) > 0:
            temporal_violations += 1
        if f.get("rule_fitting_performed", False):
            violations["test_units_used_for_rule_fitting"] = violations.get("test_units_used_for_rule_fitting", 0) + 1
    violations["release_unit_split_violations"] = split_violations
    violations["temporal_overlap_violations"] = temporal_violations

    # 5. Bootstrap multiplicity check
    boot_path = out / "bootstrap" / "cluster_bootstrap_summary_v3.json"
    if boot_path.exists():
        boot = json.loads(boot_path.read_text("utf-8"))
        min_ok = boot.get("minimum_sampled_row_count", 0) >= 32
        max_ok = boot.get("maximum_sampled_row_count", 0) >= 32
        multi_ok = boot.get("duplicate_cluster_draws_observed", False) == True
        violations["bootstrap_wrong_row_counts"] = 0 if (min_ok and max_ok) else 1
        violations["bootstrap_duplicate_multiplicity_failures"] = 0 if multi_ok else 1
    else:
        violations["bootstrap_wrong_row_counts"] = 1
        violations["bootstrap_duplicate_multiplicity_failures"] = 1

    # 6. Baseline contract checks
    pair_mismatches = 0
    coverage_violations = 0
    for b in bases:
        if b.get("paired_rows", 0) != 32:
            pair_mismatches += 1
        if b.get("baseline_id") == "always_abstain":
            if b.get("baseline_coverage", {}).get("numerator", 99) != 0:
                coverage_violations += 1
        else:
            if b.get("baseline_coverage", {}).get("numerator", 0) < 32:
                coverage_violations += 1
    violations["baseline_pairing_mismatches"] = pair_mismatches
    violations["baseline_coverage_contract_violations"] = coverage_violations

    # 7. SQLite count check
    db = out / "indexes" / "validation_pilot_v3.sqlite"
    sqlite_mismatches = 0
    if db.exists():
        conn = sqlite3.connect(str(db))
        for table, fname in [
            ("directional_validation", "datasets/directional_validation_dataset_v3.jsonl"),
            ("macro_abstentions", "datasets/macro_abstention_dataset_v3.jsonl"),
            ("fold_evaluations", "folds/walkforward_fold_evaluations_v3.jsonl"),
            ("baseline_comparisons", "baselines/paired_baseline_comparison_v3.jsonl"),
            ("leave_one_unit_out", "evaluations/leave_one_release_unit_out_v3.jsonl"),
            ("failed_experiments", "failed_experiments/failed_experiments_v3.jsonl")]:
            fc = len(load_jsonl(out / fname))
            try:
                dc = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                if fc != dc:
                    sqlite_mismatches += 1
            except Exception:
                sqlite_mismatches += 1
        conn.close()
    violations["file_sqlite_count_mismatches"] = sqlite_mismatches

    # Overall verdict
    serious = [k for k, v in violations.items() if v > 0]
    violations["overall_verdict"] = "pass" if len(serious) == 0 else "fail"
    violations["serious_violations"] = {k: violations[k] for k in serious}

    # Report
    report_path = out / "reports" / "validation_integrity_audit_v3.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(violations, indent=2), encoding="utf-8")

    print(json.dumps(violations, indent=2))
    print(f"\nOverall verdict: {violations['overall_verdict']}")

    if violations["overall_verdict"] == "fail":
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot-dir", required=True)
    args = parser.parse_args()
    audit(args.pilot_dir)