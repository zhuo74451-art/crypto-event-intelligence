"""Test validation pipeline produces identical hashes on clean rebuild."""
import subprocess, sys, pathlib, hashlib

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v2"

FILES = ["datasets/directional_validation_dataset_v2.jsonl", "datasets/macro_abstention_dataset_v2.jsonl",
         "folds/walkforward_fold_evaluations_v2.jsonl", "baselines/paired_baseline_comparison_v2.jsonl",
         "evaluations/leave_one_release_unit_out_v2.jsonl", "failed_experiments/failed_experiments_v2.jsonl"]


def test_idempotency():
    # Run 1
    subprocess.run([sys.executable, "-X", "utf8", str(SD / "run_verified_validation_pilot_v2.py")],
                    capture_output=True, check=True)
    h1 = {f: hashlib.sha256((VD / f).read_bytes()).hexdigest() for f in FILES}

    # Run 2
    subprocess.run([sys.executable, "-X", "utf8", str(SD / "run_verified_validation_pilot_v2.py")],
                    capture_output=True, check=True)
    mismatches = [f for f in FILES if hashlib.sha256((VD / f).read_bytes()).hexdigest() != h1[f]]
    assert len(mismatches) == 0, f"Hash mismatches: {mismatches}"
