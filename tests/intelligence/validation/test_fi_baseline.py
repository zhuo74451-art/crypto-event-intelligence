import subprocess, sys, pathlib, shutil, tempfile, json

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_baseline_pairing_fail():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d), ignore=shutil.ignore_patterns("validation_pilot_v3.sqlite"))

        bp = d / "baselines" / "paired_baseline_comparison_v3.jsonl"
        comps = [json.loads(l) for l in bp.read_text("utf-8").strip().splitlines()]
        for c in comps:
            if c["baseline_id"] != "always_abstain":
                c["paired_rows"] = 0
        bp.write_text("\n".join(json.dumps(c, sort_keys=True) for c in comps), encoding="utf-8")

        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        output = r.stdout; result = json.loads(output.split(chr(10)+chr(10))[0]) if output.strip().startswith("{") else {}
        assert r.returncode != 0, f"Expected non-zero exit, got {r.returncode}"
        assert result.get("overall_verdict") == "fail", f"Expected verdict=fail, got {result.get('overall_verdict')}"
        assert "baseline_pairing_mismatch" in result.get("failed_invariants", []) or "baseline_pairing_mismatch" in result,             f"Expected reason code 'baseline_pairing_mismatch' not found in {list(result.keys())}"