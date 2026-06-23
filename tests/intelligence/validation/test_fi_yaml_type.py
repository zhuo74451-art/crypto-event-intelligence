import subprocess, sys, pathlib, shutil, tempfile, json

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_yaml_type_fail():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d), ignore=shutil.ignore_patterns("validation_pilot_v3.sqlite"))

        lock = d / "upstream" / "LANE_C_PRODUCER_LOCK.yaml"
        raw = lock.read_text("utf-8")
        raw = raw.replace("source_and_copy_equal: true", "source_and_copy_equal: yes")
        raw = raw.replace("record_count: 8", "record_count: eight")
        lock.write_text(raw, encoding="utf-8")

        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        output = r.stdout; result = json.loads(output.split(chr(10)+chr(10))[0]) if output.strip().startswith("{") else {}
        assert r.returncode != 0, f"Expected non-zero exit, got {r.returncode}"
        assert result.get("overall_verdict") == "fail", f"Expected verdict=fail, got {result.get('overall_verdict')}"
        assert "producer_yaml_type_invalid" in result.get("failed_invariants", []) or "producer_yaml_type_invalid" in result,             f"Expected reason code 'producer_yaml_type_invalid' not found in {list(result.keys())}"