import subprocess, sys, pathlib, shutil, tempfile, json

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_bootstrap_multiplicity_fails():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d), ignore=shutil.ignore_patterns("validation_pilot_v3.sqlite"))
        bp = d / "bootstrap" / "cluster_bootstrap_summary_v3.json"
        data = json.loads(bp.read_text("utf-8"))
        data["duplicate_cluster_draws_observed"] = False
        data["minimum_sampled_row_count"] = 8
        bp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        output = r.stdout; result = json.loads(output.split(chr(10)+chr(10))[0]) if output.strip().startswith("{") else {}
        assert r.returncode != 0
        assert any(k in result.get("failed_invariants", []) for k in ["bootstrap_min_rows", "bootstrap_max_rows", "bootstrap_multiplicity_not_preserved"])