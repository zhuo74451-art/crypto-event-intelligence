"""Core cognition tests."""
import json, tempfile, os
from pathlib import Path
from market_radar.cognition.contracts import EventState, EventRevision, ExpectationState, MarketSnapshot, Assessment, Abstention, AbstentionCode, EventStatus, ExpectationType
from market_radar.cognition.event_grouper import group_observations
from market_radar.cognition.event_store import EventStore
from market_radar.cognition.expectation import calculate_gap, detect_stale
from market_radar.cognition.confirmation import evaluate_price_direction, evaluate_volume_expansion
from market_radar.cognition.transmission import determine_paths
from market_radar.cognition.assessment import build_assessment, should_abstain

def test_contracts_import():
    assert EventState is not None
    assert EventRevision is not None
    assert ExpectationState is not None

def test_event_state_roundtrip():
    es = EventState(event_id="evt1", status=EventStatus.ACTIVE.value, title="Test Event")
    d = es.to_dict()
    es2 = EventState.from_dict(d)
    assert es2.event_id == "evt1"
    assert es2.title == "Test Event"

def test_expectation_gap():
    state = calculate_gap(expected=100.0, actual=110.0)
    assert state.signed_surprise == 10.0
    assert state.absolute_surprise == 10.0
    assert state.surprise_pct == 10.0

def test_expectation_no_baseline():
    state = calculate_gap(expected=None, actual=110.0)
    assert state.expectation_type == ExpectationType.UNAVAILABLE.value

def test_price_confirmation_supports():
    state = evaluate_price_direction(pre_price=100.0, post_price=105.0, threshold_pct=1.0)
    assert state.verdict == "supports"

def test_price_confirmation_contradicts():
    state = evaluate_price_direction(pre_price=100.0, post_price=95.0, threshold_pct=1.0)
    assert state.verdict == "contradicts"

def test_price_confirmation_unavailable():
    state = evaluate_price_direction(pre_price=None, post_price=105.0)
    assert state.verdict == "unavailable"

def test_should_abstain_unavailable_expectation():
    ab = should_abstain(expectation_available=False, market_data_available=True, unresolved_conflicts=False, stale=False)
    assert ab is not None
    assert ab.code == AbstentionCode.EXPECTATION_UNAVAILABLE.value

def test_should_abstain_none():
    ab = should_abstain(expectation_available=True, market_data_available=True, unresolved_conflicts=False, stale=False)
    assert ab is None

def test_transmission_regulatory():
    paths = determine_paths("SEC announces new crypto regulations", ["BTC", "ETH"])
    assert any(p.channel == "regulatory_liquidity" for p in paths)

def test_transmission_no_path():
    paths = determine_paths("Unrelated weather report", [])
    assert any(p.channel == "no_defensible_path" for p in paths)

def test_event_store_create():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
    try:
        store = EventStore(db_path)
        es = EventState(event_id="evt1", status=EventStatus.CANDIDATE.value, title="Test")
        store.upsert_event(es)
        loaded = store.get_event("evt1")
        assert loaded is not None
        assert loaded.title == "Test"
        store.close()
    finally:
        if os.path.exists(db_path): os.unlink(db_path)

def test_event_grouping():
    class MockObs:
        def __init__(self, oid, dk, source):
            self.observation_id = oid
            self.event_dedup_key = dk
            self.source = source
            self.observed_at = "2026-01-01T00:00:00+00:00"
            self.event_time = "2026-01-01T00:00:00+00:00"
            self.normalized_payload = {"title": "Test"}
            self.affected_assets = []
    class MockVO:
        def __init__(self, oid, dk, source):
            self.valid = True
            self.observation = MockObs(oid, dk, source)
            self.source_origin = type("SO", (), {"value": "fixture"})()
    vos = [MockVO("o1", "key1", "cisa"), MockVO("o2", "key1", "sec")]
    events, conflicts = group_observations(vos)
    assert len(events) == 1  # same dedup_key
    assert len(events[0].observation_ids) == 2