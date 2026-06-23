"""Test that horizon windows and labels have shared_release_group_id field.
CPI+CoreCPI and NFP+Unemployment share group IDs.
Non-shared events have group_size=1."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v3")
WINDOWS_FILE = PILOT_DIR / "horizon_windows_v3.jsonl"
LABELS_FILE = PILOT_DIR / "reaction_labels_v3.jsonl"
EVENTS_FILE = PILOT_DIR / "lane_a_input/macro_release_events_v1.jsonl"

# Event families that are co-released (share a release time)
CO_RELEASE_PAIRS = [
    ("us_cpi", "us_core_cpi"),
    ("us_nonfarm_payrolls", "us_unemployment_rate"),
]
STANDALONE_FAMILIES = {"us_fomc_rate_decision", "us_core_pce"}


class TestSharedGroupFieldsInOutputs:
    """Validate shared_release_group_id presence and grouping semantics."""

    def load_jsonl(self, path):
        records = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def load_events(self):
        events = self.load_jsonl(EVENTS_FILE)
        return {e["event_id"]: e for e in events}

    def test_windows_have_shared_release_group_id(self):
        windows = self.load_jsonl(WINDOWS_FILE)
        missing = [i for i, w in enumerate(windows) if "shared_release_group_id" not in w]
        assert not missing, (
            f"Found {len(missing)} window record(s) without shared_release_group_id"
        )

    def test_labels_have_shared_release_group_id(self):
        labels = self.load_jsonl(LABELS_FILE)
        missing = [i for i, l in enumerate(labels) if "shared_release_group_id" not in l]
        assert not missing, (
            f"Found {len(missing)} label record(s) without shared_release_group_id"
        )

    def test_cpi_corecpi_share_group_ids(self):
        """CPI and CoreCPI events that share a release time must share
        the same shared_release_group_id."""
        windows = self.load_jsonl(WINDOWS_FILE)
        events = self.load_events()

        # Map event_id -> (group_id, family)
        event_group_map = {}
        for w in windows:
            eid = w["event_id"]
            if eid not in event_group_map:
                gid = w.get("shared_release_group_id", "")
                family = events.get(eid, {}).get("event_family", "")
                event_group_map[eid] = (gid, family)

        # Find CPI+CoreCPI pairs that share a release time
        time_to_events = {}
        for eid, e in events.items():
            t = e["actual_release_at_utc"]
            time_to_events.setdefault(t, []).append(eid)

        errors = []
        for t, eids in time_to_events.items():
            families_at_time = {events[eid]["event_family"] for eid in eids}
            if "us_cpi" in families_at_time and "us_core_cpi" in families_at_time:
                gids = {event_group_map.get(eid, (None,))[0] for eid in eids}
                if len(gids) != 1:
                    errors.append(
                        f"At release time {t}: CPI+CoreCPI events have "
                        f"multiple group IDs: {gids}"
                    )
        assert not errors, (
            "CPI+CoreCPI group ID sharing errors:\n" + "\n".join(errors)
        )

    def test_nfp_unemployment_share_group_ids(self):
        """NFP and Unemployment events that share a release time must share
        the same shared_release_group_id."""
        windows = self.load_jsonl(WINDOWS_FILE)
        events = self.load_events()

        event_group_map = {}
        for w in windows:
            eid = w["event_id"]
            if eid not in event_group_map:
                gid = w.get("shared_release_group_id", "")
                family = events.get(eid, {}).get("event_family", "")
                event_group_map[eid] = (gid, family)

        time_to_events = {}
        for eid, e in events.items():
            t = e["actual_release_at_utc"]
            time_to_events.setdefault(t, []).append(eid)

        errors = []
        for t, eids in time_to_events.items():
            families_at_time = {events[eid]["event_family"] for eid in eids}
            if "us_nonfarm_payrolls" in families_at_time and "us_unemployment_rate" in families_at_time:
                gids = {event_group_map.get(eid, (None,))[0] for eid in eids}
                if len(gids) != 1:
                    errors.append(
                        f"At release time {t}: NFP+Unemployment events have "
                        f"multiple group IDs: {gids}"
                    )
        assert not errors, (
            "NFP+Unemployment group ID sharing errors:\n" + "\n".join(errors)
        )

    def test_non_shared_events_have_group_size_one(self):
        """Events that do not share their release time with another event
        (standalone: FOMC, Core PCE) must have shared_release_group_size=1."""
        windows = self.load_jsonl(WINDOWS_FILE)
        events = self.load_events()

        # Determine which event_ids are standalone (only 1 event at that time)
        time_counts = {}
        for e in events.values():
            t = e["actual_release_at_utc"]
            time_counts[t] = time_counts.get(t, 0) + 1

        standalone_times = {t for t, c in time_counts.items() if c == 1}
        standalone_event_ids = {
            e["event_id"] for e in events.values()
            if e["actual_release_at_utc"] in standalone_times
        }

        errors = []
        seen = set()
        for w in windows:
            eid = w["event_id"]
            if eid in seen:
                continue
            seen.add(eid)
            if eid in standalone_event_ids:
                gsz = w.get("shared_release_group_size")
                if gsz != 1:
                    errors.append(
                        f"Standalone event {eid} ({events.get(eid, {}).get('event_family', '?')}) "
                        f"has shared_release_group_size={gsz}, expected 1"
                    )
        assert not errors, (
            "Standalone event group size errors:\n" + "\n".join(errors)
        )
