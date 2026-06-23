import subprocess, sys, pathlib, shutil, tempfile

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_yaml_type_fail():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d))
        lock = d / "upstream" / "LANE_C_PRODUCER_LOCK.yaml"
        raw = lock.read_text("utf-8")
        raw = raw.replace("source_and_copy_equal: true", "source_and_copy_equal: true_string")
        raw = raw.replace("record_count: 8", "record_count: string_8")
        lock.write_text(raw, encoding="utf-8")
        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        assert r.returncode != 0, "Should fail on YAML type corruption"