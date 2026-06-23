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
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d), ignore=shutil.ignore_patterns("validation_pilot_v3.sqlite"))
        target = d / rel_path
        if target.exists():
            target.unlink()
        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        output = r.stdout
        if chr(10) + chr(10) in output:
            output = output.split(chr(10) + chr(10))[0]
        result = json.loads(output) if output.strip().startswith("{") else {}
        assert r.returncode != 0, f"Exit code {r.returncode} for {rel_path}"
        assert result.get("overall_verdict") == "fail", f"verdict not fail for {rel_path}"
        assert "missing_artifacts" in result.get("failed_invariants", []),             f"missing_artifacts not in failed_invariants for {rel_path}: {result.get('failed_invariants')}"