"""Test that the Lane A producer lock file exists, events have correct families,
the artifact SHA matches, and no temporary event IDs exist.

NOTE: The PRODUCER_LOCK.yaml file is not valid YAML (the manifest_hash_note
contains unquoted colons). We parse it as raw text instead of using yaml.safe_load.
"""

import sys
import re
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

LANE_A_DIR = Path("data/intelligence/historical_market/pilot_v2/lane_a_input")
LOCK_FILE = LANE_A_DIR / "PRODUCER_LOCK.yaml"
EVENTS_FILE = LANE_A_DIR / "macro_release_events_v1.jsonl"
KNOWN_ARTIFACT_SHA = "ba93cce3ca298fdb48ecf690247ad449b57a0afe826f8832b587498c8f62fc1c"
EXPECTED_FAMILIES = {
    "us_cpi", "us_core_cpi", "us_nonfarm_payrolls",
    "us_unemployment_rate", "us_core_pce", "us_fomc_rate_decision"
}


def _read_lock_text():
    """Read lock file and parse key-value pairs from the first section
    (before the inline JSON dicts) using regex."""
    with open(LOCK_FILE, "r", encoding="utf-8") as f:
        text = f.read()
    return text


def _get_lock_value(key, text):
    """Extract value for a top-level key from the raw lock text."""
    # Match 'key: value' at start of line, capturing until next key or end
    pattern = re.compile(r'^' + re.escape(key) + r':\s*(.+)$', re.MULTILINE)
    m = pattern.search(text)
    if m:
        return m.group(1).strip()
    return None


def _parse_json_value(text):
    """If the value looks like a JSON dict, parse it; otherwise return raw string."""
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


class TestLaneAPilotLock:
    """Validate the Lane A producer lock and its referenced artifact."""

    def test_lock_file_exists(self):
        assert LOCK_FILE.exists(), f"Lock file not found: {LOCK_FILE}"

    def test_artifact_sha_matches(self):
        text = _read_lock_text()
        actual_sha = _get_lock_value("events_artifact_sha256", text)
        assert actual_sha is not None, "events_artifact_sha256 not found in lock file"
        assert actual_sha == KNOWN_ARTIFACT_SHA, (
            f"Artifact SHA mismatch: expected {KNOWN_ARTIFACT_SHA}, got {actual_sha}"
        )

    def test_event_count_is_12(self):
        text = _read_lock_text()
        count_str = _get_lock_value("event_count", text)
        assert count_str is not None, "event_count not found in lock file"
        assert int(count_str) == 12, f"Expected 12 events, got {count_str}"

    def test_event_families_are_correct(self):
        """Each of the 6 families must have exactly 2 events."""
        text = _read_lock_text()
        families_str = _get_lock_value("event_families", text)
        assert families_str is not None, "event_families not found in lock file"
        families = _parse_json_value(families_str)
        assert isinstance(families, dict), "event_families should be a dict"
        for family in EXPECTED_FAMILIES:
            assert family in families, f"Missing family: {family}"
            assert families[family] == 2, (
                f"Family {family} expected 2 events, got {families[family]}"
            )
        assert len(families) == len(EXPECTED_FAMILIES), (
            f"Expected {len(EXPECTED_FAMILIES)} families, got {len(families)}"
        )

    def test_no_temporary_event_ids(self):
        """No placeholder / temporary event ID values should exist."""
        assert EVENTS_FILE.exists(), f"Events file not found: {EVENTS_FILE}"
        temp_patterns = ("TEMP", "temp", "PLACEHOLDER", "pending", "00000000")
        with open(EVENTS_FILE, "r") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                eid = record.get("event_id", "")
                for pattern in temp_patterns:
                    assert pattern not in eid, (
                        f"Line {i}: event_id '{eid}' contains temporary pattern '{pattern}'"
                    )

    def test_shared_release_groups_present_in_lock(self):
        """Lock must define shared_release_groups."""
        text = _read_lock_text()
        groups_str = _get_lock_value("shared_release_groups", text)
        assert groups_str is not None, "shared_release_groups not found in lock file"
        groups = _parse_json_value(groups_str)
        assert isinstance(groups, dict) and len(groups) > 0, (
            "shared_release_groups missing or empty in lock file"
        )
        assert len(groups) == 8, (
            f"Expected 8 event entries in shared_release_groups, got {len(groups)}"
        )
