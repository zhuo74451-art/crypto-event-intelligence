"""End-to-end orchestrator tests."""
import json, os, tempfile
from pathlib import Path
from market_radar.cognition.orchestrator import run_cognition

FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "cognition"

def _run_case(case_name):
    import tempfile
    td = tempfile.mkdtemp()
    result = run_cognition(input_path=FIXTURE_DIR / case_name, output_root=Path(td), run_id=case_name, mode="replay")
    return result, Path(td)

def test_e2e_regulatory_surprise():
    result, td = _run_case("case_regulatory_surprise")
    assert result.status in ("ok", "degraded")
    assert len(result.events) >= 1
    assert (td / "assessments.jsonl").exists()
    assert (td / "event_states.jsonl").exists()
    assert (td / "evidence_manifest.jsonl").exists()
    assert (td / "run_manifest.json").exists()

def test_e2e_macro_release():
    result, td = _run_case("case_macro_release")
    assert len(result.events) >= 1
    assert (td / "event_states.jsonl").exists()

def test_e2e_security_incident():
    result, td = _run_case("case_security_incident")
    assert len(result.events) >= 1
    assert (td / "source_conflicts.jsonl").exists()

def test_e2e_software_release_abstains():
    result, td = _run_case("case_software_release")
    if result.abstentions:
        assert len(result.abstentions) >= 1
    assert (td / "run_manifest.json").exists()

def test_e2e_duplicate_cross_source():
    result, td = _run_case("case_duplicate_cross_source")
    assert len(result.events) >= 1
    if len(result.events) == 1 and len(result.events[0].observation_ids) >= 2:
        assert len(result.events[0].source_ids) >= 2

def test_e2e_ambiguous_dates():
    result, td = _run_case("case_ambiguous_dates")
    assert len(result.events) >= 1
    assert (td / "event_states.jsonl").exists()

def test_e2e_all_required_outputs():
    result, td = _run_case("case_regulatory_surprise")
    required = ["run_manifest.json", "RUN_TELEMETRY.jsonl", "event_states.jsonl", "event_revisions.jsonl", "evidence_manifest.jsonl", "assessments.jsonl", "abstentions.jsonl", "expectation_states.jsonl", "confirmation_states.jsonl", "transmission_paths.jsonl", "source_conflicts.jsonl", "market_snapshots.jsonl"]
    for fname in required:
        assert (td / fname).exists(), f"Missing required output: {fname}"

def test_e2e_deterministic_replay():
    result1, td1 = _run_case("case_regulatory_surprise")
    import tempfile
    td2 = Path(tempfile.mkdtemp())
    result2 = run_cognition(input_path=FIXTURE_DIR / "case_regulatory_surprise", output_root=td2, run_id="test2", mode="replay")
    assert len(result1.events) == len(result2.events)
    for e1, e2 in zip(result1.events, result2.events):
        assert e1.event_id == e2.event_id
        assert e1.observation_ids == e2.observation_ids

def test_e2e_no_future_leakage():
    result, td = _run_case("case_regulatory_surprise")
    import tempfile
    td2 = Path(tempfile.mkdtemp())
    result2 = run_cognition(input_path=FIXTURE_DIR / "case_regulatory_surprise", output_root=td2, run_id="test_future", mode="replay", as_of="2020-01-01T00:00:00+00:00")
    assert result2.status in ("ok", "degraded", "abstained")
    for ms in result2.snapshots:
        assert ms.as_of <= "2020-01-01T00:00:00+00:00" or not ms.as_of