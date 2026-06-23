import subprocess, sys, pathlib, shutil, tempfile, yaml

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_producer_count_fail():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d))
        lock = d / "upstream" / "LANE_C_PRODUCER_LOCK.yaml"
        data = yaml.safe_load(lock.read_text("utf-8"))
        data["artifacts"]["release_units_v1.jsonl"]["record_count"] = 99
        lock.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        assert r.returncode != 0, "Should fail on producer count mismatch"