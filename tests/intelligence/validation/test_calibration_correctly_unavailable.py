"""Test calibration is correctly unavailable."""
import json, pathlib

VD = pathlib.Path(__file__).parents[3] / "data" / "intelligence" / "validation" / "pilot_v2"


def test_calibration_unavailable():
    p = VD / "calibration" / "calibration_status_v2.json"
    assert p.exists(), "calibration_status_v2.json not found"
    data = json.loads(p.read_text("utf-8"))
    assert data["status"] == "unavailable"
    assert data["brier_score"] is None
    assert data["ece"] is None


def test_multiple_testing_unavailable():
    p = VD / "multiple_testing" / "multiple_testing_status_v2.json"
    assert p.exists()
    data = json.loads(p.read_text("utf-8"))
    assert data["status"] == "unavailable"
    assert data["raw_p_values"] == []


def test_drift_unavailable():
    p = VD / "drift" / "drift_status_v2.json"
    assert p.exists()
    data = json.loads(p.read_text("utf-8"))
    assert data["status"] == "unavailable"
    assert data["psi"] is None
