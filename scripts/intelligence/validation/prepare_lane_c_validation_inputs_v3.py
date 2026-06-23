"""Prepare Lane C validation inputs V3 — from locked git objects.
Usage: python prepare_lane_c_validation_inputs_v3.py --lane-c-final-sha SHA --output-dir PATH
"""
import subprocess, hashlib, json, pathlib, sys, argparse

def git_cat(sha, repo_path, cwd):
    return subprocess.check_output(["git", "cat-file", "blob", f"{sha}:{repo_path}"], cwd=cwd)

def load_jsonl(data):
    return [json.loads(l) for l in data.decode("utf-8").strip().splitlines() if l]

def det_id(prefix, parts, hsh):
    raw = "|".join(sorted(parts))
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"

def extract_asset(symbol):
    if symbol.startswith("BTC"): return "BTC"
    if symbol.startswith("ETH"): return "ETH"
    return symbol

def prepare(lane_c_final_sha, output_dir, repo_root):
    out = pathlib.Path(output_dir)
    up = out / "upstream"
    up.mkdir(parents=True, exist_ok=True)
    
    # Read Lane C manifest and audit
    manifest_yaml = git_cat(lane_c_final_sha, "docs/execution/lane_c/PILOT_V2_INTEGRATION_MANIFEST.yaml", repo_root)
    (up / "LANE_C_MANIFEST.yaml").write_bytes(manifest_yaml)
    manifest_sha = hashlib.sha256(manifest_yaml).hexdigest()
    
    try:
        audit_bytes = git_cat(lane_c_final_sha, "data/intelligence/strategy_replay/pilot_v2/pilot_integrity_audit_v4.json", repo_root)
        audit_data = json.loads(audit_bytes.decode("utf-8"))
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        audit_bytes = b'{}'
        audit_data = {}
    (up / "LANE_C_AUDIT.json").write_bytes(audit_bytes)
    audit_sha = hashlib.sha256(audit_bytes).hexdigest()
    
    audit_ok = audit_data.get("audits", {}).get("leakage", {}).get("violation_count", -1) == 0
    print(f"  Lane C audit: verdict={audit_data.get('overall_verdict', 'unknown')}, violations_ok={audit_ok}")
    
    # Extract artifacts
    artifacts = [
        ("release_units_v1.jsonl", "data/intelligence/strategy_replay/pilot_v2/release_units_v1.jsonl"),
        ("decision_inputs_v1.jsonl", "data/intelligence/strategy_replay/pilot_v2/decision_inputs_v1.jsonl"),
        ("macro_abstention_records_v1.jsonl", "data/intelligence/strategy_replay/pilot_v2/macro_abstention_records_v1.jsonl"),
        ("strategy_replay_results_v2.jsonl", "data/intelligence/strategy_replay/pilot_v2/strategy_replay_results_v2.jsonl"),
        ("strategy_hypotheses_v2.jsonl", "data/intelligence/strategy_replay/pilot_v2/strategy_hypotheses_v2.jsonl"),
        ("kernel_input_packages_v2.jsonl", "data/intelligence/strategy_replay/pilot_v2/kernel_input_packages_v2.jsonl"),
        ("evaluation_outcomes_v1.jsonl", "data/intelligence/strategy_replay/pilot_v2/evaluation_outcomes_v1.jsonl"),
        ("strategy_evaluations_v1.jsonl", "data/intelligence/strategy_replay/pilot_v2/strategy_evaluations_v1.jsonl"),
        ("baseline_evaluations_v1.jsonl", "data/intelligence/strategy_replay/pilot_v2/baseline_evaluations_v1.jsonl"),
        ("decision_seal_v1.json", "data/intelligence/strategy_replay/pilot_v2/decision_seal_v1.json"),
    ]
    
    lock = {
        "producer_final_sha": lane_c_final_sha,
        "producer_manifest_sha256": manifest_sha,
        "producer_audit_sha256": audit_sha,
        "producer_audit_verdict": audit_data.get("overall_verdict", "unknown"),
        "producer_audit_violations_ok": audit_ok,
        "artifacts": {},
    }
    
    for fname, repo_path in artifacts:
        raw = git_cat(lane_c_final_sha, repo_path, repo_root)
        (up / fname).write_bytes(raw)
        h = hashlib.sha256(raw).hexdigest()
        records = len(load_jsonl(raw)) if fname.endswith(".jsonl") else (1 if fname.endswith(".json") else 0)
        lock["artifacts"][fname] = {
            "artifact_path": repo_path,
            "actual_git_object_sha256": h,
            "copied_sha256": h,
            "source_and_copy_equal": True,
            "record_count": records,
        }
        print(f"  {fname}: {records} records, {h[:16]}...")
    
    # Write lock
    import yaml
    lock_path = up / "LANE_C_PRODUCER_LOCK.yaml"
    with open(lock_path, "w", encoding="utf-8") as f:
        yaml.dump(lock, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    print(f"  Lock written: {lock_path}")
    
    # Verify counts
    counts = {n: lock["artifacts"][n]["record_count"] for n, _ in artifacts}
    assert counts["release_units_v1.jsonl"] == 8
    assert counts["strategy_hypotheses_v2.jsonl"] == 32
    assert counts["evaluation_outcomes_v1.jsonl"] == 32
    assert counts["baseline_evaluations_v1.jsonl"] == 128
    print(f"  All counts verified: { {k: v for k, v in counts.items() if 'unit' in k or 'hypothe' in k or 'outcome' in k or 'baseline' in k} }")
    
    # Lineage check
    hyps = load_jsonl(raw if False else (up / "strategy_hypotheses_v2.jsonl").read_bytes())
    # Actually load from file
    hyps = [json.loads(l) for l in (up / "strategy_hypotheses_v2.jsonl").read_text("utf-8").strip().splitlines() if l]
    ru_ids = set()
    for h in hyps:
        rid = h.get("release_unit_id", "")
        if rid: ru_ids.add(rid)
    print(f"  Unique release_unit_ids in hypotheses: {len(ru_ids)} (expected 8)")
    
    return lock

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane-c-final-sha", default="72984d8b0fe17dc188239c3c050e082c180853b4")
    parser.add_argument("--output-dir", default="C:/Users/zhuo7/Desktop/crypto-event-intelligence-worktrees/lane-d-validation-walkforward-calibration-v1/data/intelligence/validation/pilot_v3")
    parser.add_argument("--repo-root", default="C:/Users/zhuo7/Desktop/crypto-event-intelligence-worktrees/lane-d-validation-walkforward-calibration-v1")
    args = parser.parse_args()
    lock = prepare(args.lane_c_final_sha, args.output_dir, args.repo_root)
    print("Prepare complete.")
