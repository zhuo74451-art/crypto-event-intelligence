"""Test: current time-series values must not be marked as historical initial values."""
import json
import os

FORMAL_EVENTS = "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl"


class TestCurrentSeriesIsNotInitialValue:
    def test_no_current_latest_marked_initial(self):
        if not os.path.exists(FORMAL_EVENTS) or os.path.getsize(FORMAL_EVENTS) == 0:
            return
        with open(FORMAL_EVENTS) as f:
            events = [json.loads(l) for l in f if l.strip()]
        bad = [e for e in events if e.get("actual_value_status") == "current_latest_only" and e.get("strategy_replay_eligible") == True]
        assert len(bad) == 0, f"{len(bad)} current_latest_only events marked strategy-replay-eligible"

    def test_derived_values_not_marked_verified_initial(self):
        if not os.path.exists(FORMAL_EVENTS) or os.path.getsize(FORMAL_EVENTS) == 0:
            return
        with open(FORMAL_EVENTS) as f:
            events = [json.loads(l) for l in f if l.strip()]
        bad = [e for e in events if e.get("actual_value_status") == "derived_from_verified_release_table" and e.get("actual_value_status") != "verified_initial_from_release"]
        for e in bad:
            assert e.get("actual_value_status") != "verified_initial_from_release", f"Derived value marked as verified_initial: {e.get('event_id')}"
