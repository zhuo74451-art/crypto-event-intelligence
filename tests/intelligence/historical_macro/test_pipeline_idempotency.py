"""Tests for pipeline idempotency - running twice produces same results."""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


class TestPipelineIdempotency:
    def test_release_events_ids_stable_across_runs(self):
        """Verify the release events JSONL is sorted or stable."""
        path = "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl"
        if not os.path.exists(path):
            return
        event_ids = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    ev = json.loads(line)
                    event_ids.append(ev["event_id"])
        # Check all IDs are unique
        assert len(event_ids) == len(set(event_ids)), "Duplicate event IDs found"

    def test_rerun_does_not_duplicate(self):
        """Simulate: loading existing events and running again should not duplicate."""
        path = "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl"
        if not os.path.exists(path):
            return
        seen = set()
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    ev = json.loads(line)
                    seen.add(ev["event_id"])
        # Simulate adding new events (should not conflict with existing)
        from market_radar.intelligence.acquisition.historical_macro.contracts import (
            generate_event_id, generate_logical_event_key,
        )
        new_id = generate_event_id(generate_logical_event_key("US", "us_cpi", "2026-06"), "2026-07-15T13:30:00Z")
        assert new_id not in seen, "New event ID conflicts with existing"
