import subprocess, sys, pathlib, shutil, tempfile, json

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_malformed_json_does_not_crash_audit():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d), ignore=shutil.ignore_patterns("validation_pilot_v3.sqlite"))
        dp = d / "datasets" / "directional_validation_dataset_v3.jsonl"
        dp.write_text("NOT VALID JSON\n", encoding="utf-8")
        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        output = r.stdout
        if chr(10)+chr(10) in output:
            output = output.split(chr(10)+chr(10))[0]
        result = json.loads(output) if output.strip().startswith("{") else {}
        assert r.returncode != 0, f"Expected non-zero, got {r.returncode}"
        assert result.get("overall_verdict") == "fail", f"Expected verdict fail"
        assert "directional_dataset_error" in result.get("failed_invariants", []),             f"Expected directional_dataset_error in failed_invariants: {result.get('failed_invariants')}"