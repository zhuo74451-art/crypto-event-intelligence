"""Test V3 pipeline produces identical hashes on clean rebuild."""
import subprocess, sys, pathlib, hashlib, tempfile

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"


def test_v3_idempotency():
    """Run pipeline twice into temp dirs, compare hashes."""
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        # Run 1
        r1 = subprocess.run([sys.executable, "-X", "utf8", str(SD / "run_verified_validation_pilot_v3.py"),
                             "--output-dir", str(pathlib.Path(tmp1) / "pilot_v3"),
                             "--no-clean"], capture_output=True, text=True)
        assert r1.returncode == 0, f"Run 1 failed: {r1.stderr[:200]}"

        # Run 2
        r2 = subprocess.run([sys.executable, "-X", "utf8", str(SD / "run_verified_validation_pilot_v3.py"),
                             "--output-dir", str(pathlib.Path(tmp2) / "pilot_v3"),
                             "--no-clean"], capture_output=True, text=True)
        assert r2.returncode == 0, f"Run 2 failed: {r2.stderr[:200]}"

        # Compare
        files = ["datasets/directional_validation_dataset_v3.jsonl", "datasets/macro_abstention_dataset_v3.jsonl",
                 "folds/walkforward_fold_evaluations_v3.jsonl", "baselines/paired_baseline_comparison_v3.jsonl",
                 "evaluations/leave_one_release_unit_out_v3.jsonl"]
        mismatches = []
        for f in files:
            h1 = hashlib.sha256((pathlib.Path(tmp1) / "pilot_v3" / f).read_bytes()).hexdigest()
            h2 = hashlib.sha256((pathlib.Path(tmp2) / "pilot_v3" / f).read_bytes()).hexdigest()
            if h1 != h2:
                mismatches.append(f)
        assert len(mismatches) == 0, f"Hash mismatches: {mismatches}"
