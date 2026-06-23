import subprocess, sys, pathlib, shutil, tempfile, json

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_duplicate_id_fail():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d), ignore=shutil.ignore_patterns("validation_pilot_v3.sqlite"))

        dp = d / "datasets" / "directional_validation_dataset_v3.jsonl"
        lines = dp.read_text("utf-8").strip().splitlines()
        rows = [json.loads(l) for l in lines]
        rows[0]["validation_row_id"] = rows[1]["validation_row_id"]
        dp.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows), encoding="utf-8")

        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        output = r.stdout; result = json.loads(output.split(chr(10)+chr(10))[0]) if output.strip().startswith("{") else {}
        assert r.returncode != 0, f"Expected non-zero exit, got {r.returncode}"
        assert result.get("overall_verdict") == "fail", f"Expected verdict=fail, got {result.get('overall_verdict')}"
        assert "duplicate_validation_row_id" in result.get("failed_invariants", []) or "duplicate_validation_row_id" in result,             f"Expected reason code 'duplicate_validation_row_id' not found in {list(result.keys())}"