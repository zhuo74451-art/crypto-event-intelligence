"""Test that shared release groups exist for CPI+CoreCPI and NFP+Unemployment
combinations, that events at the same release time share group IDs,
and that no event that shares a release time with another event is orphaned
(missing a group). Standalone events (FOMC, Core PCE) are not expected to
belong to release groups.

NOTE: The PRODUCER_LOCK.yaml file is not valid YAML (the manifest_hash_note
contains unquoted colons). We parse it as raw text instead of using yaml.safe_load.
"""

import sys
import re
import json
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pytest

LOCK_FILE = Path("data/intelligence/historical_market/pilot_v2/lane_a_input/PRODUCER_LOCK.yaml")
EVENTS_FILE = Path("data/intelligence/historical_market/pilot_v2/lane_a_input/macro_release_events_v1.jsonl")


def _read_lock_text():
    with open(LOCK_FILE, "r", encoding="utf-8") as f:
        return f.read()


def _get_lock_value(key, text):
    pattern = re.compile(r'^' + re.escape(key) + r':\s*(.+)$', re.MULTILINE)
    m = pattern.search(text)
    if m:
        return m.group(1).strip()
    return None


def _load_lock_groups():
    """Parse the shared_release_groups JSON dict from the lock file."""
    text = _read_lock_text()
    groups_str = _get_lock_value("shared_release_groups", text)
    assert groups_str is not None, "shared_release_groups not found in lock file"
    return json.loads(groups_str)


def _load_events():
    records = []
    with open(EVENTS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


class TestSharedReleaseGroups:
    """Validate shared release group assignments."""

    def test_cpi_corecpi_has_two_groups(self):
        """CPI and CoreCPI should form 2 shared release groups."""
        groups = _load_lock_groups()
        events = _load_events()
        event_family_map = {e["event_id"]: e["event_family"] for e in events}

        group_ids = {}
        for eid, info in groups.items():
            gid = info["group_id"]
            group_ids.setdefault(gid, set()).add(eid)

        cpi_groups = 0
        for gid, eids in group_ids.items():
            families_in_group = {event_family_map[eid] for eid in eids if eid in event_family_map}
            if "us_cpi" in families_in_group or "us_core_cpi" in families_in_group:
                cpi_groups += 1
                assert families_in_group == {"us_cpi", "us_core_cpi"}, (
                    f"Group {gid} contains {families_in_group}, expected both us_cpi and us_core_cpi"
                )
        assert cpi_groups == 2, (
            f"Expected 2 CPI+CoreCPI shared release groups, found {cpi_groups}"
        )

    def test_nfp_unemployment_has_two_groups(self):
        """NFP and Unemployment should form 2 shared release groups."""
        groups = _load_lock_groups()
        events = _load_events()
        event_family_map = {e["event_id"]: e["event_family"] for e in events}

        group_ids = {}
        for eid, info in groups.items():
            gid = info["group_id"]
            group_ids.setdefault(gid, set()).add(eid)

        nfp_groups = 0
        for gid, eids in group_ids.items():
            families_in_group = {event_family_map[eid] for eid in eids if eid in event_family_map}
            if "us_nonfarm_payrolls" in families_in_group or "us_unemployment_rate" in families_in_group:
                nfp_groups += 1
                assert families_in_group == {"us_nonfarm_payrolls", "us_unemployment_rate"}, (
                    f"Group {gid} contains {families_in_group}, "
                    "expected both us_nonfarm_payrolls and us_unemployment_rate"
                )
        assert nfp_groups == 2, (
            f"Expected 2 NFP+Unemployment shared release groups, found {nfp_groups}"
        )

    def test_events_at_same_time_have_matching_group_ids(self):
        """Events released at the same time must belong to the same group."""
        groups = _load_lock_groups()
        time_to_groups = {}
        for eid, info in groups.items():
            rt = info["release_time"]
            gid = info["group_id"]
            time_to_groups.setdefault(rt, set()).add(gid)
        for rt, gids in time_to_groups.items():
            assert len(gids) == 1, (
                f"Release time {rt} has multiple group IDs: {gids}. "
                "Events at the same release time should share one group."
            )

    def test_co_released_events_are_not_orphaned(self):
        """Every event that shares a release time with another event
        must belong to a shared release group. Standalone events
        (FOMC, Core PCE) are excluded."""
        groups = _load_lock_groups()
        events = _load_events()

        # Find standalone release times (only 1 event at that time)
        time_counts = {}
        for e in events:
            t = e["actual_release_at_utc"]
            time_counts[t] = time_counts.get(t, 0) + 1

        standalone_times = {t for t, c in time_counts.items() if c == 1}

        event_ids_in_groups = set(groups.keys())
        all_event_ids = {e["event_id"] for e in events}
        # Orphaned = events NOT in groups AND NOT standalone
        orphaned = set()
        for e in events:
            if e["event_id"] not in event_ids_in_groups and e["actual_release_at_utc"] not in standalone_times:
                orphaned.add(e["event_id"])
        assert not orphaned, (
            f"Found {len(orphaned)} event(s) that share a release time but lack a group: {orphaned}"
        )

    def test_group_sizes_are_two(self):
        """Every shared release group must have size exactly 2."""
        groups = _load_lock_groups()
        group_sizes = {}
        for eid, info in groups.items():
            gid = info["group_id"]
            group_sizes.setdefault(gid, 0)
            group_sizes[gid] += 1
        for gid, size in group_sizes.items():
            assert size == 2, f"Group {gid} has size {size}, expected 2"
        assert len(group_sizes) == 4, (
            f"Expected 4 shared release groups, found {len(group_sizes)}"
        )

    def test_standalone_events_have_unique_times(self):
        """Standalone events (FOMC, Core PCE) must each have a unique release time
        not shared with any other event."""
        events = _load_events()
        time_counts = {}
        for e in events:
            t = e["actual_release_at_utc"]
            time_counts[t] = time_counts.get(t, 0) + 1
        standalone_families = {"us_fomc_rate_decision", "us_core_pce"}
        for e in events:
            if e["event_family"] in standalone_families:
                assert time_counts[e["actual_release_at_utc"]] == 1, (
                    f"Event {e['event_id']} ({e['event_family']}) at {e['actual_release_at_utc']} "
                    "shares its release time with another event but is not in a group"
                )
