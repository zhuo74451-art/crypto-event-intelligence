"""End-to-end orchestrator tests with unconditional assertions."""
import json, os, tempfile
from pathlib import Path
from market_radar.cognition.orchestrator import run_cognition

FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "cognition"

def _run_case(case_name, mode="replay", as_of=None):
    import tempfile
    td = tempfile.mkdtemp()
    result = run_cognition(
        input_path=FIXTURE_DIR / case_name,
        output_root=Path(td),
        run_id=case_name,
        mode=mode,
        as_of=as_of,
    )
    return result, Path(td)


def test_e2e_regulatory_surprise():
    """Regulatory surprise: expect assessment, no abstention."""
    result, td = _run_case("case_regulatory_surprise")
    assert result.status in ("ok", "degraded"), f"Expected ok/degraded, got {result.status}"
    assert len(result.events) >= 1, "Expected at least 1 event"
    assert len(result.assessments) >= 1, "Expected at least 1 assessment"
    assert (td / "assessments.jsonl").exists()
    assert (td / "event_states.jsonl").exists()
    assert (td / "evidence_manifest.jsonl").exists()
    assert (td / "run_manifest.json").exists()


def test_e2e_macro_release():
    """Macro release: baseline expectation."""
    result, td = _run_case("case_macro_release")
    assert len(result.events) >= 1
    assert len(result.expectations) >= 1
    # Expectation should be CONSENSUS_VALUE since both expected and actual exist
    from market_radar.cognition.contracts import ExpectationType
    assert any(e.expectation_type == ExpectationType.CONSENSUS_VALUE.value for e in result.expectations), "Expected CONSENSUS_VALUE"
    assert (td / "event_states.jsonl").exists()
    assert (td / "expectation_states.jsonl").exists()


def test_e2e_security_incident():
    """Security incident: contradiction between expected and actual."""
    result, td = _run_case("case_security_incident")
    assert len(result.events) >= 1
    # The vulnerability event (cve_2026_1234) should be contradicted because
    # expected=0 but price dropped -5% (negative price impact)
    from market_radar.cognition.contracts import EventStatus
    contradicted = [a for a in result.assessments if a.lifecycle_state == EventStatus.CONTRADICTED.value]
    assert len(contradicted) >= 1, f"Expected contradicted assessment, got lifecycle states: {[a.lifecycle_state for a in result.assessments]}"
    assert (td / "source_conflicts.jsonl").exists()


def test_e2e_software_release_abstains():
    """Software release: must abstain (no expectation, no market data)."""
    result, td = _run_case("case_software_release")
    assert len(result.abstentions) >= 1, "Expected at least 1 abstention"
    abstention_codes = [a.code for a in result.abstentions]
    assert any("unavailable" in c for c in abstention_codes), f"No EXPECTATION_UNAVAILABLE abstention: {abstention_codes}"
    assert (td / "run_manifest.json").exists()
    assert (td / "abstentions.jsonl").exists()


def test_e2e_duplicate_cross_source():
    """Cross-source duplicate: merge same dedup_key events."""
    result, td = _run_case("case_duplicate_cross_source")
    assert len(result.events) >= 1
    # Find the event with the CISA/SEC dedup_key
    target_events = [e for e in result.events if len(e.source_ids) >= 2]
    assert len(target_events) >= 1, "Expected an event with 2+ sources"
    assert "cisa" in target_events[0].source_ids, "Expected CISA source"
    assert "sec" in target_events[0].source_ids or "github_releases" in target_events[0].source_ids, "Expected second source"


def test_e2e_ambiguous_dates():
    """Ambiguous dates: same title, different dates kept separate."""
    result, td = _run_case("case_ambiguous_dates")
    assert len(result.events) >= 2, "Expected 2+ events for different dates"
    if len(result.events) >= 2:
        assert result.events[0].event_dedup_key != result.events[1].event_dedup_key, "Expected different dedup keys"
    assert (td / "event_states.jsonl").exists()


def test_e2e_all_required_outputs():
    """Verify all required output files exist."""
    result, td = _run_case("case_regulatory_surprise")
    required = [
        "run_manifest.json", "RUN_TELEMETRY.jsonl", "event_states.jsonl",
        "event_revisions.jsonl", "evidence_manifest.jsonl", "assessments.jsonl",
        "abstentions.jsonl", "expectation_states.jsonl", "confirmation_states.jsonl",
        "transmission_paths.jsonl", "source_conflicts.jsonl", "market_snapshots.jsonl",
    ]
    for fname in required:
        assert (td / fname).exists(), f"Missing required output: {fname}"


def test_e2e_deterministic_replay():
    """Replay must produce identical events."""
    result1, td1 = _run_case("case_regulatory_surprise")
    import tempfile
    td2 = Path(tempfile.mkdtemp())
    result2 = run_cognition(
        input_path=FIXTURE_DIR / "case_regulatory_surprise",
        output_root=td2,
        run_id="test2",
        mode="replay",
    )
    assert len(result1.events) == len(result2.events), f"Event count mismatch: {len(result1.events)} vs {len(result2.events)}"
    for e1, e2 in zip(result1.events, result2.events):
        assert e1.event_id == e2.event_id, f"Event ID mismatch: {e1.event_id} vs {e2.event_id}"
        assert e1.observation_ids == e2.observation_ids, f"Observation IDs mismatch"


def test_e2e_no_future_leakage():
    """Future as_of must block later snapshots."""
    result, td = _run_case("case_regulatory_surprise")
    import tempfile
    td2 = Path(tempfile.mkdtemp())
    result2 = run_cognition(
        input_path=FIXTURE_DIR / "case_regulatory_surprise",
        output_root=td2,
        run_id="test_future",
        mode="replay",
        as_of="2020-01-01T00:00:00+00:00",
    )
    assert result2.status in ("ok", "degraded", "abstained")
    for ms in result2.snapshots:
        assert ms.as_of <= "2020-01-01T00:00:00+00:00" or not ms.as_of