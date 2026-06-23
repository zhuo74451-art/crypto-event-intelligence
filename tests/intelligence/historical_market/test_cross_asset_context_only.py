"""Test that cross-asset context records have immediate_reaction_eligible=False,
context_only=True, and that all 10 series are represented per event."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

CROSS_ASSET_FILE = Path(
    "data/intelligence/historical_market/pilot_v2/cross_asset_context_v2.jsonl"
)

EXPECTED_SERIES = [
    "yahoo_sp500_index",
    "yahoo_nasdaq_composite",
    "yahoo_gold_futures",
    "yahoo_silver_futures",
    "yahoo_us_dollar_index",
    "yahoo_us5y_yield",
    "yahoo_us10y_yield",
    "yahoo_us30y_yield",
    "yahoo_vix_index",
    "yahoo_wti_crude",
]

EXPECTED_RECORD_COUNT = 120  # 12 events × 10 series


class TestCrossAssetContextOnly:
    """Validate cross-asset context record invariants."""

    def load_records(self):
        records = []
        with open(CROSS_ASSET_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def test_record_count(self):
        records = self.load_records()
        assert len(records) == EXPECTED_RECORD_COUNT, (
            f"Expected {EXPECTED_RECORD_COUNT} records, got {len(records)}"
        )

    def test_all_immediate_reaction_ineligible(self):
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            if r.get("immediate_reaction_eligible") is not False:
                errors.append(
                    f"Record {i} (event={r['event_id']}, series={r['series_id']}): "
                    f"immediate_reaction_eligible={r.get('immediate_reaction_eligible')}"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) where immediate_reaction_eligible is not False:\n"
            + "\n".join(errors[:10])
        )

    def test_all_context_only(self):
        records = self.load_records()
        errors = []
        for i, r in enumerate(records):
            if r.get("context_only") is not True:
                errors.append(
                    f"Record {i} (event={r['event_id']}, series={r['series_id']}): "
                    f"context_only={r.get('context_only')}"
                )
        assert not errors, (
            f"Found {len(errors)} record(s) where context_only is not True:\n"
            + "\n".join(errors[:10])
        )

    def test_all_ten_series_per_event(self):
        records = self.load_records()
        event_series = {}
        for r in records:
            event_series.setdefault(r["event_id"], set()).add(r["series_id"])

        errors = []
        for eid, series_set in event_series.items():
            missing = sorted(set(EXPECTED_SERIES) - series_set)
            extra = sorted(series_set - set(EXPECTED_SERIES))
            if missing:
                errors.append(f"Event {eid} missing series: {missing}")
            if extra:
                errors.append(f"Event {eid} has extra series: {extra}")
            if len(series_set) != len(EXPECTED_SERIES):
                errors.append(
                    f"Event {eid} has {len(series_set)} series, expected {len(EXPECTED_SERIES)}"
                )
        assert not errors, (
            f"Series coverage errors:\n" + "\n".join(errors)
        )

    def test_all_records_have_required_fields(self):
        records = self.load_records()
        required = [
            "event_id", "event_time_utc", "series_id",
            "previous_available_close", "next_available_close",
            "immediate_reaction_eligible", "context_only"
        ]
        errors = []
        for i, r in enumerate(records):
            for field in required:
                if field not in r:
                    errors.append(f"Record {i} missing field '{field}'")
        assert not errors, (
            f"Found {len(errors)} records with missing fields:\n" + "\n".join(errors[:10])
        )
