"""Test V3 audit detects failures."""
import subprocess, sys, pathlib, json, shutil, tempfile

SD = pathlib.Path(__file__).parents[3] / "scripts" / "intelligence" / "validation"
VD3 = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v3"


def test_audit_passes_on_valid_data():
    result = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                             "--pilot-dir", str(VD3)], capture_output=True, text=True)
    assert result.returncode == 0, f"Audit should pass on valid data: {result.stderr[:200]}"


def test_audit_fails_on_missing_outcome():
    """Inject a missing outcome by removing directional dataset."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_d = pathlib.Path(tmp) / "pilot_v3"
        shutil.copytree(str(VD3), str(tmp_d), ignore=shutil.ignore_patterns("directional_validation_dataset_v3.jsonl"))
        (tmp_d / "datasets").mkdir(parents=True, exist_ok=True)
        result = subprocess.run([sys.executable, "-X", "utf8", str(SD / "audit_validation_pilot_v3.py"),
                                 "--pilot-dir", str(tmp_d)], capture_output=True, text=True)
        assert result.returncode != 0, "Audit should fail when directional dataset is missing"
