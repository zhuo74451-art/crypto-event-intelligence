"""Test every window has baseline_offset_from_event_minutes,
endpoint_offset_from_event_minutes, effective_return_span_minutes,
horizon_alignment_error_minutes, and precision_class='coarse_hourly_alignment'.
No 1m/5m claims."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v3")
WINDOWS_FILE = PILOT_DIR / "horizon_windows_v3.jsonl"

REQUIRED_OFFSET_FIELDS = [
    "baseline_offset_from_event_minutes",
    "endpoint_offset_from_event_minutes",
    "effective_return_span_minutes",
    "horizon_alignment_error_minutes",
]
EXPECTED_PRECISION_CLASS = "coarse_hourly_alignment"


class TestAlignmentOffsetMetadata:
    """Validate alignment offset metadata on every horizon window record."""

    def load_windows(self):
        records = []
        with open(WINDOWS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def test_all_records_have_alignment_offset_fields(self):
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            for field in REQUIRED_OFFSET_FIELDS:
                if field not in w:
                    errors.append(
                        f"Record {i} (window_id={w.get('window_id', '?')}) "
                        f"missing field '{field}'"
                    )
        assert not errors, (
            f"Found {len(errors)} records with missing offset fields:\n"
            + "\n".join(errors[:10])
        )

    def test_all_records_have_precision_class(self):
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            pc = w.get("precision_class")
            if pc != EXPECTED_PRECISION_CLASS:
                errors.append(
                    f"Record {i} (window_id={w.get('window_id', '?')}): "
                    f"precision_class='{pc}', expected '{EXPECTED_PRECISION_CLASS}'"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with incorrect precision_class:\n"
            + "\n".join(errors[:10])
        )

    def test_no_one_minute_or_five_minute_horizon_claims(self):
        """No record may claim a 1m or 5m horizon."""
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            h = w.get("nominal_horizon", "")
            if h in ("1m", "5m"):
                errors.append(
                    f"Record {i} (window_id={w.get('window_id', '?')}): "
                    f"unsupported horizon '{h}'"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with 1m/5m horizon claims:\n"
            + "\n".join(errors)
        )

    def test_baseline_offset_is_negative_or_zero(self):
        """Baseline offset from event should be <= 0 (before the event)."""
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            offset = w.get("baseline_offset_from_event_minutes")
            if offset is not None and offset > 0:
                errors.append(
                    f"Record {i}: baseline_offset_from_event_minutes={offset} "
                    "(expected <= 0)"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with positive baseline offset:\n"
            + "\n".join(errors[:10])
        )

    def test_endpoint_offset_is_positive(self):
        """Endpoint offset from event should be > 0 (after the event)."""
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            offset = w.get("endpoint_offset_from_event_minutes")
            if offset is not None and offset <= 0:
                errors.append(
                    f"Record {i}: endpoint_offset_from_event_minutes={offset} "
                    "(expected > 0)"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with non-positive endpoint offset:\n"
            + "\n".join(errors[:10])
        )

    def test_effective_return_span_is_positive(self):
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            span = w.get("effective_return_span_minutes")
            if span is not None and span <= 0:
                errors.append(
                    f"Record {i}: effective_return_span_minutes={span} (expected > 0)"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with non-positive return span:\n"
            + "\n".join(errors[:10])
        )

    def test_horizon_alignment_error_is_nonnegative(self):
        windows = self.load_windows()
        errors = []
        for i, w in enumerate(windows):
            err = w.get("horizon_alignment_error_minutes")
            if err is not None and err < 0:
                errors.append(
                    f"Record {i}: horizon_alignment_error_minutes={err} "
                    "(expected >= 0)"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) with negative alignment error:\n"
            + "\n".join(errors[:10])
        )
