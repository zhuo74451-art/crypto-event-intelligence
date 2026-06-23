"""Test full pipeline produces identical outputs on clean rebuild."""
import subprocess, sys, pathlib, hashlib

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "strategy_replay"
D = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "strategy_replay" / "pilot_v2"


def test_pipeline_idempotent():
    # Run 1
    result1 = subprocess.run([sys.executable, "-X", "utf8", str(SD / "run_verified_replay_pilot_v2.py")],
                              capture_output=True, text=True)
    assert result1.returncode == 0, f"Pipeline run 1 failed: {result1.stderr[:200]}"

    hashes1 = {}
    for fname in ["release_units_v1.jsonl", "decision_inputs_v1.jsonl",
                   "macro_abstention_records_v1.jsonl", "strategy_replay_results_v2.jsonl",
                   "strategy_hypotheses_v2.jsonl", "kernel_input_packages_v2.jsonl",
                   "evaluation_outcomes_v1.jsonl", "strategy_evaluations_v1.jsonl",
                   "baseline_evaluations_v1.jsonl"]:
        hashes1[fname] = hashlib.sha256((D / fname).read_bytes()).hexdigest()

    # Run 2
    result2 = subprocess.run([sys.executable, "-X", "utf8", str(SD / "run_verified_replay_pilot_v2.py")],
                              capture_output=True, text=True)
    assert result2.returncode == 0, f"Pipeline run 2 failed: {result2.stderr[:200]}"

    # Compare
    mismatches = []
    for fname, expected in hashes1.items():
        current = hashlib.sha256((D / fname).read_bytes()).hexdigest()
        if current != expected:
            mismatches.append(fname)

    assert len(mismatches) == 0, f"Hash mismatches: {mismatches}"
