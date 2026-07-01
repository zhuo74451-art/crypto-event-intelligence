"""Vertical case tests for cognition spine."""
import json
from pathlib import Path
from market_radar.cognition.input_loader import load_observations
from market_radar.cognition.event_grouper import group_observations
from market_radar.cognition.assessment import should_abstain
from market_radar.cognition.contracts import EventStatus

FIXTURE_DIR = Path(__file__).parents[2] / "tests" / "fixtures" / "cognition"

def _run_case(case_name):
    path = FIXTURE_DIR / case_name
    obs_list, inventory = load_observations(path / "observations.jsonl")
    events, conflicts = group_observations(obs_list)
    return obs_list, inventory, events, conflicts

def test_regulatory_surprise():
    """Case 1: Regulatory announcement with clear expectation."""
    obs_list, inv, events, conflicts = _run_case("case_regulatory_surprise")
    assert inv.valid_observations == 1
    assert len(events) == 1

def test_macro_release():
    """Case 2: Macro release with numeric consensus."""
    obs_list, inv, events, conflicts = _run_case("case_macro_release")
    assert inv.valid_observations == 1
    assert len(events) >= 1

def test_security_incident():
    """Case 3: Security incident with multiple sources - partial conflict."""
    obs_list, inv, events, conflicts = _run_case("case_security_incident")
    assert inv.valid_observations == 2
    # Different dedup keys = separate events (patch vs vulnerability)
    assert len(events) >= 1

def test_software_release_abstention():
    """Case 4: Software release with no defensible market effect - requires abstention."""
    obs_list, inv, events, conflicts = _run_case("case_software_release")
    assert inv.valid_observations == 1
    ab = should_abstain(expectation_available=False, market_data_available=False, unresolved_conflicts=False, stale=False)
    assert ab is not None
    # Expectation unavailable is expected for routine software releases
    assert "unavailable" in ab.code

def test_duplicate_cross_source_grouping():
    """Case 5: Same event from different sources must group together."""
    obs_list, inv, events, conflicts = _run_case("case_duplicate_cross_source")
    assert inv.valid_observations == 2
    # Same dedup_key => same event group
    assert len(events) == 1, f'Expected 1 event for same dedup_key, got {len(events)}'
    assert len(events[0].observation_ids) == 2
    assert len(events[0].source_ids) >= 2

def test_ambiguous_dates_kept_separate():
    """Case 6: Same title on different dates must remain separate events."""
    obs_list, inv, events, conflicts = _run_case("case_ambiguous_dates")
    assert inv.valid_observations == 2
    # Different dedup_keys => separate events
    assert len(events) >= 2, f'Expected 2 events for different dates, got {len(events)}'
    assert events[0].event_dedup_key != events[1].event_dedup_key