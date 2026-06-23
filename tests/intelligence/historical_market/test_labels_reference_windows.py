"""Test that every label has a window_id that exists in the windows file
and that every window_id in labels corresponds to an existing window."""

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


class TestLabelsReferenceWindows:
    """Validate that every label references an existing window via window_id."""

    def load_jsonl(self, path):
        records = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def test_every_label_has_window_id(self):
        labels = self.load_jsonl(LABELS_FILE)
        missing = [i for i, l in enumerate(labels) if not l.get("window_id")]
        assert not missing, (
            f"Found {len(missing)} label(s) without a window_id field"
        )

    def test_every_label_window_id_exists_in_windows(self):
        """Every label's window_id must match an existing window record."""
        windows = self.load_jsonl(WINDOWS_FILE)
        window_ids = {w["window_id"] for w in windows}

        labels = self.load_jsonl(LABELS_FILE)
        missing = []
        for l in labels:
            wid = l.get("window_id")
            if wid and wid not in window_ids:
                missing.append(
                    f"Label {l.get('label_id', '?')} references "
                    f"non-existent window_id={wid}"
                )
        assert not missing, (
            f"Found {len(missing)} label(s) referencing unknown windows:\n"
            + "\n".join(missing[:10])
        )

    def test_every_window_id_in_labels_corresponds_to_window(self):
        """Every distinct window_id found in labels must exist in windows."""
        windows = self.load_jsonl(WINDOWS_FILE)
        window_ids = {w["window_id"] for w in windows}

        labels = self.load_jsonl(LABELS_FILE)
        label_window_ids = {l["window_id"] for l in labels if l.get("window_id")}
        orphaned = label_window_ids - window_ids
        assert not orphaned, (
            f"Found {len(orphaned)} window_id(s) in labels that do not "
            f"exist in windows: {list(orphaned)[:5]}"
        )

    def test_labels_and_windows_have_same_event_instrument_pairs(self):
        """The set of (event_id, instrument_id) pairs in labels should
        match the set in windows."""
        windows = self.load_jsonl(WINDOWS_FILE)
        labels = self.load_jsonl(LABELS_FILE)

        window_pairs = {(w["event_id"], w["instrument_id"]) for w in windows}
        label_pairs = {(l["event_id"], l["instrument_id"]) for l in labels}

        only_in_windows = window_pairs - label_pairs
        only_in_labels = label_pairs - window_pairs

        assert not only_in_windows, (
            f"Found {len(only_in_windows)} pair(s) in windows but not labels: "
            f"{list(only_in_windows)[:5]}"
        )
        assert not only_in_labels, (
            f"Found {len(only_in_labels)} pair(s) in labels but not windows: "
            f"{list(only_in_labels)[:5]}"
        )

    def test_label_count_matches_window_record_count(self):
        """The total number of labels should equal the total number of
        window records (both 72 for 24 pairs × 3 horizons)."""
        windows = self.load_jsonl(WINDOWS_FILE)
        labels = self.load_jsonl(LABELS_FILE)
        assert len(labels) == len(windows), (
            f"Label count ({len(labels)}) does not match window record count "
            f"({len(windows)})"
        )
