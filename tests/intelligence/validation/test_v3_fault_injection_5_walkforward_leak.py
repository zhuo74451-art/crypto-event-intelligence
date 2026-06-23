import subprocess, sys, pathlib, shutil, tempfile, json

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_walkforward_leak_fail():
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(d))
        fp = d / "folds" / "walkforward_fold_evaluations_v3.jsonl"
        folds = [json.loads(l) for l in fp.read_text("utf-8").strip().splitlines()]
        folds[0]["train_release_unit_ids"].append(folds[0]["test_release_unit_ids"][0])
        fp.write_text("\n".join(json.dumps(f, sort_keys=True) for f in folds), encoding="utf-8")
        r = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                            "--pilot-dir", str(d)], capture_output=True, text=True)
        assert r.returncode != 0, "Should fail on walkforward leak"