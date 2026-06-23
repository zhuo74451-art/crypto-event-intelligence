"""Test hourly alignment invariants: no pre_bar_close after event_time,
all alignment_error values <= 60 minutes, and all timestamps end with 'Z'."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest
from datetime import datetime, timezone

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v2")
WINDOWS_FILE = PILOT_DIR / "event_asset_windows_v2.jsonl"
ALIGNMENT_REPORT = PILOT_DIR / "pilot_alignment_report_v2.json"

MAX_ALIGNMENT_ERROR_MINUTES = 60


class TestHourlyAlignmentNoLeakage:
    """Ensure no temporal leakage in the alignment."""

    def load_windows(self):
        records = []
        with open(WINDOWS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def test_no_pre_bar_close_after_event_time(self):
        """No window may have pre_bar_close_time_utc >= event_time_utc."""
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            pre = w["pre_bar_close_time_utc"]
            evt = w["event_time_utc"]
            if pre >= evt:
                errors.append(
                    f"Record {i} (event={w['event_id']}, inst={w['instrument_id']}, "
                    f"horizon={w['horizon']}): {pre} >= {evt}"
                )
        assert not errors, (
            f"Found {len(errors)} window(s) with pre_bar_close >= event_time:\n" +
            "\n".join(errors[:10])
        )

    def test_alignment_error_within_60_minutes(self):
        """All alignment_error values must be <= 60 minutes.

        Since the windows file does not carry an explicit alignment_error field,
        we compute the difference between event_time_utc and pre_bar_close_time_utc
        and verify it is within the permissible range (<= 60 minutes).
        """
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            pre_str = w["pre_bar_close_time_utc"]
            evt_str = w["event_time_utc"]
            # Parse ISO timestamps
            pre_dt = datetime.fromisoformat(pre_str.replace("Z", "+00:00"))
            evt_dt = datetime.fromisoformat(evt_str.replace("Z", "+00:00"))
            diff_minutes = (evt_dt - pre_dt).total_seconds() / 60.0
            if diff_minutes > MAX_ALIGNMENT_ERROR_MINUTES:
                errors.append(
                    f"Record {i} (event={w['event_id']}, inst={w['instrument_id']}): "
                    f"alignment gap {diff_minutes:.1f}m exceeds {MAX_ALIGNMENT_ERROR_MINUTES}m"
                )
            if diff_minutes < 0:
                errors.append(
                    f"Record {i}: negative alignment gap ({diff_minutes:.1f}m) — "
                    "event_time before pre_bar_close"
                )
        assert not errors, (
            f"Found {len(errors)} alignment error(s):\n" + "\n".join(errors[:10])
        )

    def test_all_timestamps_end_with_z(self):
        """Every timestamp field must end with 'Z' (UTC indicator)."""
        windows = self.load_windows()
        timestamp_fields = [
            "event_time_utc", "pre_bar_close_time_utc",
            "event_bar_close_time_utc", "post_bar_close_time_utc"
        ]
        errors = []
        for i, w in enumerate(windows):
            for field in timestamp_fields:
                val = w.get(field, "")
                if not val.endswith("Z"):
                    errors.append(
                        f"Record {i} field '{field}': '{val}' does not end with 'Z'"
                    )
        assert not errors, (
            f"Found {len(errors)} timestamp(s) not ending with Z:\n" +
            "\n".join(errors[:10])
        )
