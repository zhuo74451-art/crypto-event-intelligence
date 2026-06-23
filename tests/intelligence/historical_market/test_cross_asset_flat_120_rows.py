"""Test cross_asset_context_v3.jsonl has exactly 120 records and each
has series_id, event_id, previous_available_close, next_available_close."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v3")
CROSS_ASSET_FILE = PILOT_DIR / "cross_asset_context_v3.jsonl"

EXPECTED_RECORD_COUNT = 120
REQUIRED_FIELDS = [
    "series_id",
    "event_id",
    "previous_available_close",
    "next_available_close",
]


class TestCrossAssetFlat120Rows:
    """Validate cross-asset context record count and required fields."""

    def load_records(self):
        records = []
        with open(CROSS_ASSET_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def test_record_count_is_120(self):
        records = self.load_records()
        assert len(records) == EXPECTED_RECORD_COUNT, (
            f"Expected {EXPECTED_RECORD_COUNT} cross-asset context records, "
            f"got {len(records)}"
        )

    def test_all_records_have_series_id(self):
        records = self.load_records()
        missing = [i for i, r in enumerate(records) if not r.get("series_id")]
        assert not missing, (
            f"Found {len(missing)} record(s) without series_id"
        )

    def test_all_records_have_event_id(self):
        records = self.load_records()
        missing = [i for i, r in enumerate(records) if not r.get("event_id")]
        assert not missing, (
            f"Found {len(missing)} record(s) without event_id"
        )

    def test_all_records_have_previous_available_close(self):
        records = self.load_records()
        missing = [i for i, r in enumerate(records) if "previous_available_close" not in r]
        assert not missing, (
            f"Found {len(missing)} record(s) without previous_available_close"
        )

    def test_all_records_have_next_available_close(self):
        records = self.load_records()
        missing = [i for i, r in enumerate(records) if "next_available_close" not in r]
        assert not missing, (
            f"Found {len(missing)} record(s) without next_available_close"
        )

    def test_all_records_have_all_required_fields(self):
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            for field in REQUIRED_FIELDS:
                if field not in r:
                    errors.append(
                        f"Record {i} (event={r.get('event_id', '?')}, "
                        f"series={r.get('series_id', '?')}) missing '{field}'"
                    )
        assert not errors, (
            f"Found {len(errors)} missing field(s):\n" + "\n".join(errors[:10])
        )

    def test_previous_available_close_is_numeric(self):
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            val = r.get("previous_available_close")
            if val is not None and not isinstance(val, (int, float)):
                errors.append(
                    f"Record {i}: previous_available_close is not numeric: {type(val).__name__}"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with non-numeric previous_available_close"
        )

    def test_next_available_close_is_numeric(self):
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            val = r.get("next_available_close")
            if val is not None and not isinstance(val, (int, float)):
                errors.append(
                    f"Record {i}: next_available_close is not numeric: {type(val).__name__}"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with non-numeric next_available_close"
        )
