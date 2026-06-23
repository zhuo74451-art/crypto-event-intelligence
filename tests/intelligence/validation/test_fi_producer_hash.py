import subprocess, sys, pathlib, shutil, tempfile, json

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_producer_hash_fail():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d), ignore=shutil.ignore_patterns("validation_pilot_v3.sqlite"))

        # Corrupt an actual upstream file so real hash recomputation fails
        f = d / "upstream" / "release_units_v1.jsonl"
        f.write_text(f.read_text("utf-8") + "\ncorrupted\n", encoding="utf-8")

        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        output = r.stdout; result = json.loads(output.split(chr(10)+chr(10))[0]) if output.strip().startswith("{") else {}
        assert r.returncode != 0, f"Expected non-zero exit, got {r.returncode}"
        assert result.get("overall_verdict") == "fail", f"Expected verdict=fail, got {result.get('overall_verdict')}"
        assert "producer_hash_mismatch" in result.get("failed_invariants", []) or "producer_hash_mismatch" in result,             f"Expected reason code 'producer_hash_mismatch' not found in {list(result.keys())}"