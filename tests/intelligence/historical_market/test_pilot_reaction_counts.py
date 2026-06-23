"""Test that pilot v2 record counts match expectations and no duplicate
label IDs exist. Also verify no 1m or 5m precision claims."""

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
CROSS_ASSET_FILE = PILOT_DIR / "cross_asset_context_v2.jsonl"
FUNDING_FILE = PILOT_DIR / "funding_context_v2.jsonl"

EXPECTED_DISTINCT_WINDOWS = 24   # (event_id, instrument_id) pairs
EXPECTED_LABEL_COUNT = 72        # 24 pairs × 3 horizons
EXPECTED_CROSS_ASSET_COUNT = 120  # 12 events × 10 series
EXPECTED_FUNDING_COUNT = 24       # 12 events × 2 instruments


class TestPilotReactionCounts:
    """Validate record counts and ID uniqueness."""

    def load_jsonl(self, path):
        records = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def test_distinct_event_asset_windows(self):
        windows = self.load_jsonl(WINDOWS_FILE)
        pairs = {(w["event_id"], w["instrument_id"]) for w in windows}
        assert len(pairs) == EXPECTED_DISTINCT_WINDOWS, (
            f"Expected {EXPECTED_DISTINCT_WINDOWS} distinct (event_id, instrument_id) pairs, "
            f"got {len(pairs)}"
        )
        # Each pair should have 3 horizon records
        pair_counts = {}
        for w in windows:
            key = (w["event_id"], w["instrument_id"])
            pair_counts[key] = pair_counts.get(key, 0) + 1
        for key, cnt in pair_counts.items():
            assert cnt == 3, f"Pair {key} has {cnt} horizon records, expected 3"

    def test_reaction_label_count(self):
        labels = self.load_jsonl(LABELS_FILE)
        assert len(labels) == EXPECTED_LABEL_COUNT, (
            f"Expected {EXPECTED_LABEL_COUNT} reaction labels, got {len(labels)}"
        )

    def test_cross_asset_context_count(self):
        records = self.load_jsonl(CROSS_ASSET_FILE)
        assert len(records) == EXPECTED_CROSS_ASSET_COUNT, (
            f"Expected {EXPECTED_CROSS_ASSET_COUNT} cross-asset context rows, "
            f"got {len(records)}"
        )

    def test_funding_context_count(self):
        records = self.load_jsonl(FUNDING_FILE)
        assert len(records) == EXPECTED_FUNDING_COUNT, (
            f"Expected {EXPECTED_FUNDING_COUNT} funding context rows, "
            f"got {len(records)}"
        )

    def test_no_duplicate_label_ids(self):
        labels = self.load_jsonl(LABELS_FILE)
        label_ids = [l["label_id"] for l in labels]
        duplicates = {lid for lid in label_ids if label_ids.count(lid) > 1}
        assert not duplicates, (
            f"Found {len(duplicates)} duplicate label_id(s): {duplicates}"
        )

    def test_no_duplicate_window_ids(self):
        windows = self.load_jsonl(WINDOWS_FILE)
        window_ids = [w["window_id"] for w in windows]
        duplicates = {wid for wid in window_ids if window_ids.count(wid) > 1}
        assert not duplicates, (
            f"Found {len(duplicates)} duplicate window_id(s): {duplicates}"
        )

    def test_no_one_minute_or_five_minute_precision_claims(self):
        """No record should claim a 1m or 5m precision horizon."""
        windows = self.load_jsonl(WINDOWS_FILE)
        labels = self.load_jsonl(LABELS_FILE)
        for w in windows:
            h = w.get("horizon", "")
            assert h not in ("1m", "5m"), (
                f"Window {w.get('window_id', '?')} has unsupported horizon '{h}'"
            )
        for l in labels:
            h = l.get("horizon", "")
            assert h not in ("1m", "5m"), (
                f"Label {l.get('label_id', '?')} has unsupported horizon '{h}'"
            )
