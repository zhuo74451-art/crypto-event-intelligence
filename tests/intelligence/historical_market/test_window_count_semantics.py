"""Test window count semantics: event_count=12, event_asset_pairs=24,
horizon_window_records=72, and all records have a window_id."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v3")
WINDOWS_FILE = PILOT_DIR / "horizon_windows_v3.jsonl"
REPORT_FILE = PILOT_DIR / "pilot_alignment_report_v3.json"

EXPECTED_EVENT_COUNT = 12
EXPECTED_EVENT_ASSET_PAIRS = 24
EXPECTED_HORIZON_WINDOW_RECORDS = 72


class TestWindowCountSemantics:
    """Validate window record counts and the presence of window_id on every record."""

    def load_jsonl(self, path):
        records = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def load_report(self):
        with open(REPORT_FILE, "r") as f:
            return json.load(f)

    def test_report_event_count(self):
        report = self.load_report()
        assert report.get("event_count") == EXPECTED_EVENT_COUNT, (
            f"Report event_count: expected {EXPECTED_EVENT_COUNT}, "
            f"got {report.get('event_count')}"
        )

    def test_report_event_asset_pairs(self):
        report = self.load_report()
        assert report.get("event_asset_pairs") == EXPECTED_EVENT_ASSET_PAIRS, (
            f"Report event_asset_pairs: expected {EXPECTED_EVENT_ASSET_PAIRS}, "
            f"got {report.get('event_asset_pairs')}"
        )

    def test_report_horizon_window_records(self):
        report = self.load_report()
        assert report.get("horizon_window_records") == EXPECTED_HORIZON_WINDOW_RECORDS, (
            f"Report horizon_window_records: expected {EXPECTED_HORIZON_WINDOW_RECORDS}, "
            f"got {report.get('horizon_window_records')}"
        )

    def test_actual_event_count(self):
        windows = self.load_jsonl(WINDOWS_FILE)
        unique_events = {w["event_id"] for w in windows}
        assert len(unique_events) == EXPECTED_EVENT_COUNT, (
            f"Expected {EXPECTED_EVENT_COUNT} unique events, "
            f"got {len(unique_events)}"
        )

    def test_actual_event_asset_pairs(self):
        windows = self.load_jsonl(WINDOWS_FILE)
        pairs = {(w["event_id"], w["instrument_id"]) for w in windows}
        assert len(pairs) == EXPECTED_EVENT_ASSET_PAIRS, (
            f"Expected {EXPECTED_EVENT_ASSET_PAIRS} (event_id, instrument_id) pairs, "
            f"got {len(pairs)}"
        )

    def test_actual_horizon_window_record_count(self):
        windows = self.load_jsonl(WINDOWS_FILE)
        assert len(windows) == EXPECTED_HORIZON_WINDOW_RECORDS, (
            f"Expected {EXPECTED_HORIZON_WINDOW_RECORDS} horizon window records, "
            f"got {len(windows)}"
        )

    def test_all_records_have_window_id(self):
        windows = self.load_jsonl(WINDOWS_FILE)
        missing = [i for i, w in enumerate(windows) if not w.get("window_id")]
        assert not missing, (
            f"Found {len(missing)} record(s) without a window_id: indices {missing}"
        )

    def test_window_ids_are_unique(self):
        windows = self.load_jsonl(WINDOWS_FILE)
        ids = [w["window_id"] for w in windows]
        duplicates = {wid for wid in ids if ids.count(wid) > 1}
        assert not duplicates, (
            f"Found {len(duplicates)} duplicate window_id(s): {list(duplicates)[:5]}"
        )
