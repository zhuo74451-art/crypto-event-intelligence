"""Test that previous_available_close_time_utc <= event_time_utc
for all 120 cross-asset records. Test no future_value_used_as_previous."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v3")
CROSS_ASSET_FILE = PILOT_DIR / "cross_asset_context_v3.jsonl"


class TestCrossAssetPreviousValueNotFuture:
    """Validate that no cross-asset record uses a future close time as
    the 'previous_available_close_time_utc'."""

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
        assert len(records) == 120, (
            f"Expected 120 cross-asset records, got {len(records)}"
        )

    def test_all_records_have_both_time_fields(self):
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            if "previous_available_close_time_utc" not in r:
                errors.append(
                    f"Record {i}: missing previous_available_close_time_utc"
                )
            if "event_time_utc" not in r:
                errors.append(
                    f"Record {i}: missing event_time_utc"
                )
        assert not errors, (
            f"Found {len(errors)} records with missing time fields:\n"
            + "\n".join(errors[:10])
        )

    def test_previous_available_close_time_not_future(self):
        """previous_available_close_time_utc must be <= event_time_utc
        for every record. No future_value_used_as_previous."""
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            prev = r.get("previous_available_close_time_utc", "")
            evt = r.get("event_time_utc", "")
            if prev and evt and prev > evt:
                errors.append(
                    f"Record {i} (event={r['event_id']}, series={r['series_id']}): "
                    f"previous_close_time ({prev}) > event_time ({evt})"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with future previous_close_time:\n"
            + "\n".join(errors[:10])
        )

    def test_no_future_value_used_as_previous(self):
        """Alias: no record should have a previous_available_close_time_utc
        that is after event_time_utc (future value leak)."""
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            prev = r.get("previous_available_close_time_utc", "")
            evt = r.get("event_time_utc", "")
            if prev and evt and prev > evt:
                errors.append(
                    f"Record {i} (event={r['event_id']}, series={r['series_id']}): "
                    f"future previous_close_time ({prev}) > event_time ({evt})"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with future value as previous:\n"
            + "\n".join(errors[:10])
        )

    def test_all_timestamps_end_with_z(self):
        """Both time fields should end with 'Z' (UTC indicator)."""
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            prev = r.get("previous_available_close_time_utc", "")
            evt = r.get("event_time_utc", "")
            if prev and not prev.endswith("Z"):
                errors.append(
                    f"Record {i}: previous_available_close_time_utc='{prev}' "
                    "does not end with 'Z'"
                )
            if evt and not evt.endswith("Z"):
                errors.append(
                    f"Record {i}: event_time_utc='{evt}' does not end with 'Z'"
                )
        assert not errors, (
            f"Found {len(errors)} timestamp(s) not ending with 'Z':\n"
            + "\n".join(errors[:10])
        )
