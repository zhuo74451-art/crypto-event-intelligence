"""Test idempotency of the pilot v2 alignment: running a second time should
produce the same output. Load existing outputs and verify no duplicate IDs
and consistent counts."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest
from collections import Counter

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v2")
WINDOWS_FILE = PILOT_DIR / "event_asset_windows_v2.jsonl"
LABELS_FILE = PILOT_DIR / "market_reaction_labels_v2.jsonl"
CROSS_ASSET_FILE = PILOT_DIR / "cross_asset_context_v2.jsonl"
FUNDING_FILE = PILOT_DIR / "funding_context_v2.jsonl"


class TestPilotIdempotency:
    """Validate that the existing outputs are self-consistent and idempotent."""

    def load_jsonl(self, path):
        records = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def test_window_count_stable(self):
        """Window count should be deterministic."""
        windows = self.load_jsonl(WINDOWS_FILE)
        assert len(windows) == 72, f"Expected 72 windows, got {len(windows)}"

    def test_label_count_stable(self):
        """Label count should be deterministic."""
        labels = self.load_jsonl(LABELS_FILE)
        assert len(labels) == 72, f"Expected 72 labels, got {len(labels)}"

    def test_no_duplicate_window_ids(self):
        """All window_id values must be unique."""
        windows = self.load_jsonl(WINDOWS_FILE)
        ids = [w["window_id"] for w in windows]
        dupes = {wid for wid, cnt in Counter(ids).items() if cnt > 1}
        assert not dupes, (
            f"Found {len(dupes)} duplicate window_id(s): {list(dupes)[:5]}"
        )

    def test_no_duplicate_label_ids(self):
        """All label_id values must be unique."""
        labels = self.load_jsonl(LABELS_FILE)
        ids = [l["label_id"] for l in labels]
        dupes = {lid for lid, cnt in Counter(ids).items() if cnt > 1}
        assert not dupes, (
            f"Found {len(dupes)} duplicate label_id(s): {list(dupes)[:5]}"
        )

    def test_no_duplicate_funding_ids(self):
        """Funding context records must have unique IDs if present."""
        funding = self.load_jsonl(FUNDING_FILE)
        ids = [r.get("id", r.get("funding_id", "")) for r in funding]
        dupes = {fid for fid, cnt in Counter(ids).items() if cnt > 1 and fid}
        assert not dupes, (
            f"Found {len(dupes)} duplicate funding id(s): {list(dupes)[:5]}"
        )

    def test_consistent_event_instrument_pairs(self):
        """Windows and labels must reference the same set of (event, instrument) pairs."""
        windows = self.load_jsonl(WINDOWS_FILE)
        labels = self.load_jsonl(LABELS_FILE)
        window_pairs = {(w["event_id"], w["instrument_id"]) for w in windows}
        label_pairs = {(l["event_id"], l["instrument_id"]) for l in labels}
        assert window_pairs == label_pairs, (
            "Mismatch between window and label (event_id, instrument_id) pairs.\n"
            f"Windows only: {window_pairs - label_pairs}\n"
            f"Labels only: {label_pairs - window_pairs}"
        )

    def test_cross_asset_events_subset_of_windows(self):
        """Cross-asset context events must be a subset of window events."""
        windows = self.load_jsonl(WINDOWS_FILE)
        cross = self.load_jsonl(CROSS_ASSET_FILE)
        window_events = {w["event_id"] for w in windows}
        cross_events = {c["event_id"] for c in cross}
        extra = cross_events - window_events
        assert not extra, (
            f"Cross-asset context references events not in windows: {extra}"
        )

    def test_funding_events_subset_of_windows(self):
        """Funding context events must be a subset of window events."""
        windows = self.load_jsonl(WINDOWS_FILE)
        funding = self.load_jsonl(FUNDING_FILE)
        window_events = {w["event_id"] for w in windows}
        funding_events = {f["event_id"] for f in funding}
        extra = funding_events - window_events
        assert not extra, (
            f"Funding context references events not in windows: {extra}"
        )

    def test_deterministic_schema_versions(self):
        """All records in each file must share the same schema_version."""
        windows = self.load_jsonl(WINDOWS_FILE)
        labels = self.load_jsonl(LABELS_FILE)
        cross = self.load_jsonl(CROSS_ASSET_FILE)
        funding = self.load_jsonl(FUNDING_FILE)

        for name, records in [
            ("windows", windows),
            ("labels", labels),
            ("cross_asset", cross),
            ("funding", funding),
        ]:
            versions = {r.get("schema_version", "") for r in records}
            assert len(versions) == 1, (
                f"{name}: expected single schema_version, found {versions}"
            )

    def test_window_id_determinism(self):
        """Same (event_id, instrument_id, horizon) should produce same window_id
        if the pipeline is idempotent. Verify that records sharing those three
        keys have consistent values."""
        windows = self.load_jsonl(WINDOWS_FILE)
        # Group by (event_id, instrument_id, horizon) — each group should have 1 record
        groups = {}
        for w in windows:
            key = (w["event_id"], w["instrument_id"], w["horizon"])
            groups.setdefault(key, []).append(w)
        for key, recs in groups.items():
            assert len(recs) == 1, (
                f"Key {key} has {len(recs)} records instead of exactly 1"
            )
