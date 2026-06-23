"""Test verified event alignment: distinct (event_id, instrument_id) pairs,
reaction label count, temporal ordering of pre_bar_close before event_time,
and absence of pre_bar_close_after_event."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v2")
WINDOWS_FILE = PILOT_DIR / "event_asset_windows_v2.jsonl"
LABELS_FILE = PILOT_DIR / "market_reaction_labels_v2.jsonl"

EXPECTED_DISTINCT_PAIRS = 24  # 12 events × 2 instruments
EXPECTED_LABEL_COUNT = 72     # 24 pairs × 3 horizons


class TestVerifiedEventAlignment:
    """Validate event-window alignment invariants."""

    def load_windows(self):
        records = []
        with open(WINDOWS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def load_labels(self):
        records = []
        with open(LABELS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def test_distinct_event_instrument_pairs(self):
        windows = self.load_windows()
        pairs = {(w["event_id"], w["instrument_id"]) for w in windows}
        assert len(pairs) == EXPECTED_DISTINCT_PAIRS, (
            f"Expected {EXPECTED_DISTINCT_PAIRS} distinct (event_id, instrument_id) pairs, "
            f"got {len(pairs)}"
        )

    def test_reaction_label_count(self):
        labels = self.load_labels()
        assert len(labels) == EXPECTED_LABEL_COUNT, (
            f"Expected {EXPECTED_LABEL_COUNT} reaction label records, got {len(labels)}"
        )

    def test_pre_bar_close_before_event_time(self):
        """pre_bar_close_time_utc must be strictly before event_time_utc."""
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            pre = w["pre_bar_close_time_utc"]
            evt = w["event_time_utc"]
            if pre >= evt:
                errors.append(
                    f"Window {i} (event={w['event_id']}, instrument={w['instrument_id']}): "
                    f"pre_bar_close_time_utc {pre} >= event_time_utc {evt}"
                )
        assert not errors, (
            f"Found {len(errors)} window(s) where pre_bar_close >= event_time:\n" +
            "\n".join(errors[:10])
        )

    def test_no_pre_bar_close_after_event(self):
        """No window should have a 'pre_bar_close_after_event' flag or equivalent."""
        windows = self.load_windows()
        for i, w in enumerate(windows):
            # Fail if any record carries a flag indicating the pre-bar close was after the event
            assert not w.get("pre_bar_close_after_event", False), (
                f"Window {i} has pre_bar_close_after_event=True"
            )
            # Also enforce that pre_bar_close_time_utc < event_time_utc (duplicate safety check)
            pre = w["pre_bar_close_time_utc"]
            evt = w["event_time_utc"]
            assert pre < evt, (
                f"Window {i}: pre_bar_close_time_utc {pre} is not before event_time_utc {evt}"
            )
