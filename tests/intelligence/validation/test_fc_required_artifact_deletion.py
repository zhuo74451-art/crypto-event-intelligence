import subprocess, sys, pathlib, shutil, tempfile, json, pytest

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"

DELETABLE = [
    "calibration/calibration_status_v3.json",
    "multiple_testing/multiple_testing_status_v3.json",
    "drift/drift_status_v3.json",
]


@pytest.mark.parametrize("rel_path", DELETABLE)
def test_deleting_required_artifact_fails_audit(rel_path):
    # First verify intact copy passes audit (baseline)
    with tempfile.TemporaryDirectory() as base_tmp:
        base_d = pathlib.Path(base_tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(base_d))
        r_base = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                                 "--pilot-dir", str(base_d)], capture_output=True, text=True)
        assert r_base.returncode == 0, f"Baseline audit failed: {r_base.stderr[:200]}"

    # Now delete the specific artifact from a fresh full copy
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d))
        target = d / rel_path
        assert target.exists(), f"Test artifact does not exist: {rel_path}"
        target.unlink()

        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        output = r.stdout
        if chr(10) + chr(10) in output:
            output = output.split(chr(10) + chr(10))[0]
        result = json.loads(output) if output.strip().startswith("{") else {}

        assert r.returncode != 0, f"Exit code should be non-zero for {rel_path}"
        assert result.get("overall_verdict") == "fail", f"verdict should be fail for {rel_path}"
        assert "missing_artifacts" in result.get("failed_invariants", []),             f"missing_artifacts not in failed_invariants: {result.get("failed_invariants")}"
        assert rel_path in result.get("missing_artifacts", []),             f"{rel_path} not in missing_artifacts: {result.get("missing_artifacts")}"
