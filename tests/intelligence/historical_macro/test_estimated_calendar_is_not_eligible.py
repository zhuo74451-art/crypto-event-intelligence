"""Test: estimated calendar events must not be in formal dataset."""
import json
import os

FORMAL_EVENTS = "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl"


class TestEstimatedCalendarIsNotEligible:
    def test_no_estimated_events_in_formal(self):
        if not os.path.exists(FORMAL_EVENTS) or os.path.getsize(FORMAL_EVENTS) == 0:
            return  # Empty dataset is valid
        with open(FORMAL_EVENTS) as f:
            events = [json.loads(l) for l in f if l.strip()]
        estimated = [e for e in events if e.get("release_time_quality") in (
            "estimated_unusable", "reconstructed_official_date_only", "missing", ""
        )]
        assert len(estimated) == 0, f"{len(estimated)} estimated events in formal dataset"

    def test_no_estimated_marked_verified(self):
        if not os.path.exists(FORMAL_EVENTS) or os.path.getsize(FORMAL_EVENTS) == 0:
            return
        with open(FORMAL_EVENTS) as f:
            events = [json.loads(l) for l in f if l.strip()]
        bad = [e for e in events if e.get("release_time_quality") == "reconstructed_official_date_only" and e.get("release_time_verified") == True]
        assert len(bad) == 0, f"{len(bad)} reconstructed dates marked verified"

    def test_no_estimated_marked_alignment_eligible(self):
        if not os.path.exists(FORMAL_EVENTS) or os.path.getsize(FORMAL_EVENTS) == 0:
            return
        with open(FORMAL_EVENTS) as f:
            events = [json.loads(l) for l in f if l.strip()]
        bad = [e for e in events if e.get("release_time_quality") in ("estimated_unusable", "missing", "") and e.get("event_alignment_eligible") == True]
        assert len(bad) == 0, f"{len(bad)} estimated events marked alignment-eligible"
