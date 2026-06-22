"""Test that real fetched data passes contract validation."""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))


RELEASE_EVENTS_PATH = "data/intelligence/historical_macro/normalized/macro_release_events_v1.jsonl"
SNAPSHOTS_PATH = "data/intelligence/historical_macro/normalized/macro_source_snapshots_v1.jsonl"


class TestRealSampleContract:
    def test_release_events_file_exists(self):
        assert os.path.exists(RELEASE_EVENTS_PATH), f"Missing: {RELEASE_EVENTS_PATH}"

    def test_release_events_have_required_fields(self):
        if not os.path.exists(RELEASE_EVENTS_PATH):
            return
        count = 0
        with open(RELEASE_EVENTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                assert "event_id" in ev, f"Missing event_id"
                assert len(ev["event_id"]) == 24, f"Invalid event_id length: {ev['event_id']}"
                assert "event_family" in ev
                assert "actual_release_at_utc" in ev
                assert "reference_period" in ev
                count += 1
        assert count >= 30, f"Only {count} events, need at least 30"
        print(f"  Validated {count} release events")

    def test_release_events_have_all_families(self):
        if not os.path.exists(RELEASE_EVENTS_PATH):
            return
        families = set()
        with open(RELEASE_EVENTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                families.add(ev.get("event_family"))
        required = {"us_cpi", "us_core_cpi", "us_nonfarm_payrolls",
                     "us_unemployment_rate", "us_core_pce", "us_fomc_rate_decision"}
        missing = required - families
        assert not missing, f"Missing event families: {missing}"
        print(f"  All 6 families present: {families}")

    def test_no_duplicate_event_ids(self):
        if not os.path.exists(RELEASE_EVENTS_PATH):
            return
        seen = set()
        dupes = []
        with open(RELEASE_EVENTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                eid = json.loads(line).get("event_id")
                if eid in seen:
                    dupes.append(eid)
                seen.add(eid)
        assert not dupes, f"Duplicate event IDs: {dupes}"
        print(f"  No duplicates among {len(seen)} events")

    def test_actual_initial_present(self):
        if not os.path.exists(RELEASE_EVENTS_PATH):
            return
        null_count = 0
        total = 0
        with open(RELEASE_EVENTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                total += 1
                if ev.get("actual_initial") is None:
                    null_count += 1
        # Some events may have null initial (FOMC decisions with 0 values)
        # But most should have values
        assert null_count <= total * 0.1, f"Too many null actual_initial: {null_count}/{total}"
        print(f"  actual_initial present: {total - null_count}/{total}")

    def test_all_utc_times(self):
        if not os.path.exists(RELEASE_EVENTS_PATH):
            return
        violations = 0
        total = 0
        with open(RELEASE_EVENTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                total += 1
                ts = ev.get("actual_release_at_utc", "")
                if ts and not ts.endswith("Z"):
                    violations += 1
        assert violations == 0, f"{violations}/{total} events have non-UTC time format"
        print(f"  All {total} events have UTC times")

    def test_snapshots_have_hashes(self):
        if not os.path.exists(SNAPSHOTS_PATH):
            return
        missing_hash = 0
        total = 0
        with open(SNAPSHOTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                snap = json.loads(line)
                total += 1
                if not snap.get("sha256"):
                    missing_hash += 1
        assert missing_hash == 0, f"{missing_hash}/{total} snapshots missing sha256"
        print(f"  All {total} snapshots have content hashes")

    def test_event_ids_deterministic(self):
        """Verify that re-creating events gives same IDs."""
        if not os.path.exists(RELEASE_EVENTS_PATH):
            return
        from market_radar.intelligence.acquisition.historical_macro.contracts import (
            generate_event_id, generate_logical_event_key,
        )
        mismatches = 0
        count = 0
        with open(RELEASE_EVENTS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ev = json.loads(line)
                lek = generate_logical_event_key(
                    ev.get("country", "US"),
                    ev.get("event_family", ""),
                    ev.get("reference_period", ""),
                )
                eid = generate_event_id(lek, ev.get("actual_release_at_utc", ""))
                if eid != ev.get("event_id"):
                    mismatches += 1
                count += 1
                if count >= 100:
                    break
        assert mismatches == 0, f"{mismatches} ID mismatches in {count} events"
        print(f"  All {count} event IDs deterministic")
