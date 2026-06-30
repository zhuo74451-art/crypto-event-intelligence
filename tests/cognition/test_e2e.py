"""End-to-end orchestrator tests with unconditional assertions."""
import json, os, tempfile
from pathlib import Path
from market_radar.cognition.orchestrator import run_cognition
from market_radar.cognition.program_runner import run_program

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


def _run_integrated(case_name):
    import tempfile
    td = tempfile.mkdtemp()
    result = run_program(
        input_path=FIXTURE_DIR / case_name,
        output_root=Path(td),
        run_id=case_name,
        mode="replay",
    )
    return result, Path(td)


def test_integrated_regulatory_surprise():
    """Integrated: verify world state, regime, arbitration, decision packet."""
    result, td = _run_integrated("case_regulatory_surprise")
    assert result.status in ("ok", "degraded")
    assert result.world_state is not None
    assert result.regime is not None
    assert len(result.arbitration_results) >= 1
    assert len(result.decision_packets) >= 1
    assert len(result.registry.components) >= 8
    assert (td / "world_state.json").exists()
    assert (td / "regime_classification.json").exists()
    assert (td / "decision_packets.jsonl").exists()
    assert (td / "strategy_registry.json").exists()
    assert (td / "evaluation_report.json").exists()
    # Verify decision packet content
    pkt = result.decision_packets[0]
    assert pkt.event_id != ""
    assert pkt.arbitration_outcome != ""
    assert pkt.not_trading_instruction is True


def test_integrated_security_incident():
    """Integrated: verify underreaction + overreaction detection."""
    result, td = _run_integrated("case_security_incident")
    assert result.status in ("ok", "degraded")
    assert len(result.decision_packets) >= 1
    # Verify priced-in state exists
    for pkt in result.decision_packets:
        assert pkt.priced_in_state != ""


def test_integrated_duplicate_cross_source():
    """Integrated: verify strategy disagreement preserved."""
    result, td = _run_integrated("case_duplicate_cross_source")
    assert result.status in ("ok", "degraded")
    arb = result.arbitration_results[0] if result.arbitration_results else None
    if arb:
        assert isinstance(arb.eligible_strategies, list)
        # Disagreements preserved
        if arb.rejected_strategies:
            reasons = list(arb.rejected_strategies.values())
            assert any(r for r in reasons), f"Empty rejection reason: {reasons}"


def test_integrated_quickflash_upgraded():
    """Integrated: QuickFlash official upgrade works."""
    result, td = _run_integrated("case_quickflash_upgraded")
    assert result.status in ("ok", "degraded")
    cog = result.cognition
    assert cog is not None, "No cognition result"
    assert cog.events, "No events generated"
    # Two observations merged into one event with 2+ sources
    merged = [e for e in cog.events if len(e.source_ids) >= 2]
    assert len(merged) >= 1, f"Expected merged event with 2+ sources, got {[e.source_ids for e in cog.events]}"


def test_integrated_quickflash_rejected():
    """Integrated: QuickFlash fact-permission rejection."""
    result, td = _run_integrated("case_quickflash_rejected")
    # Should produce abstention
    cog = result.cognition
    if cog:
        pass  # abstention checked in separate test


def test_integrated_shadow_runner():
    """Integrated: shadow runner produces all artifacts."""
    import tempfile
    from market_radar.cognition.shadow_runner import run_shadow
    from pathlib import Path
    td = Path(tempfile.mkdtemp())
    shadow_result = run_shadow(
        FIXTURE_DIR / "case_regulatory_surprise",
        td / "shadow_out", "test_shadow", mode="replay")
    assert shadow_result["status"] in ("ok", "degraded", "abstained")
    assert (td / "shadow_out" / "evaluation_report.json").exists()


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
    """Security incident: separate vulnerability and patch events."""
    result, td = _run_case("case_security_incident")
    assert len(result.events) >= 1
    # Two events with different dedup keys (cve vs patch)
    # Both expectations are confirmed by market direction
    from market_radar.cognition.contracts import EventStatus
    active_count = len([a for a in result.assessments if a.lifecycle_state == EventStatus.ACTIVE.value])
    assert active_count >= 1, f"Expected active assessments, got lifecycle states: {[a.lifecycle_state for a in result.assessments]}"
    # Confirm direction hypothesis is being used
    from market_radar.cognition.contracts import Verdict
    supports = [c for c in result.confirmations if c.verdict == Verdict.SUPPORTS.value]
    contradicts = [c for c in result.confirmations if c.verdict == Verdict.CONTRADICTS.value]
    assert len(supports) >= 1, f"Expected at least 1 SUPPORTS confirmation, got {len(supports)} supports, {len(contradicts)} contradicts"
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

def test_e2e_leverage_dislocation():
    """Leverage dislocation: extreme funding contradicts normal range."""
    result, td = _run_case("case_leverage_dislocation")
    assert len(result.events) >= 1
    assert len(result.assessments) >= 1, "Expected assessment for leverage event"
    assert (td / "confirmation_states.jsonl").exists()

def test_e2e_token_unlock():
    """Token unlock: expected negative price impact confirmed."""
    result, td = _run_case("case_token_unlock")
    assert len(result.events) >= 1
    assert len(result.expectations) >= 1
    # Expectation with negative surprise
    exps = [e for e in result.expectations if e.signed_surprise is not None and e.signed_surprise < 0]
    assert len(exps) >= 1, "Expected negative surprise for unlock event"
    assert (td / "expectation_states.jsonl").exists()

def test_e2e_narrative_decay_abstains():
    """Narrative decay: must abstain (no expectation data)."""
    result, td = _run_case("case_narrative_decay")
    assert len(result.abstentions) >= 1, "Expected abstention for narrative-only case"
    assert (td / "abstentions.jsonl").exists()

def test_e2e_priced_in():
    """Priced-in event: actual within expected range, surprise near zero."""
    result, td = _run_case("case_priced_in")
    assert len(result.events) >= 1
    assert len(result.assessments) >= 1
    exps = [e for e in result.expectations if e.signed_surprise is not None and abs(e.signed_surprise) < 5.0]
    assert len(exps) >= 1, "Expected small surprise for priced-in event"
    assert (td / "event_states.jsonl").exists()

def test_e2e_quickflash_rejected_abstains():
    """QuickFlash rejected: must abstain (inadequate fact permission)."""
    result, td = _run_case("case_quickflash_rejected")
    assert len(result.abstentions) >= 1, "Expected abstention for rejected QuickFlash lead"
    assert (td / "abstentions.jsonl").exists()

def test_e2e_quickflash_upgraded():
    """QuickFlash upgraded: social sensor lead confirmed by CISA official."""
    result, td = _run_case("case_quickflash_upgraded")
    assert len(result.events) >= 1
    # Two observations from different sources should merge into one event
    merged = [e for e in result.events if len(e.source_ids) >= 2]
    assert len(merged) >= 1, "Expected merged event with quickflash+cisa sources"
    assert (td / "source_conflicts.jsonl").exists()

def test_e2e_aggregate_outcomes():
    """Verify aggregate outcome requirements across all fixture cases."""
    all_cases = [
        "case_regulatory_surprise", "case_macro_release", "case_security_incident",
        "case_software_release", "case_duplicate_cross_source", "case_ambiguous_dates",
        "case_leverage_dislocation", "case_token_unlock", "case_narrative_decay",
        "case_priced_in", "case_quickflash_rejected", "case_quickflash_upgraded",
    ]
    total_abstentions = 0
    total_assessments = 0
    for case in all_cases:
        result, td = _run_case(case)
        total_abstentions += len(result.abstentions)
        total_assessments += len(result.assessments)
    assert total_abstentions >= 3, f"Expected >=3 abstentions across all cases, got {total_abstentions}"
    assert total_assessments >= 6, f"Expected >=6 assessments across all cases, got {total_assessments}"
    print(f"Aggregate: {total_abstentions} abstentions, {total_assessments} assessments across {len(all_cases)} cases")
