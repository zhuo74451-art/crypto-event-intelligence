"""Test pilot_alignment_report_v3.json has consistent counts:
event_count=12, event_asset_pairs=24, horizon_window_records=72,
reaction_label_records=72, cross_asset_context_records=120,
funding_context_records=24, precision_class='coarse_hourly_alignment'."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import pytest

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v3")
REPORT_FILE = PILOT_DIR / "pilot_alignment_report_v3.json"

EXPECTED_COUNTS = {
    "event_count": 12,
    "event_asset_pairs": 24,
    "horizon_window_records": 72,
    "reaction_label_records": 72,
    "cross_asset_context_records": 120,
    "funding_context_records": 24,
}

EXPECTED_PRECISION_CLASS = "coarse_hourly_alignment"


class TestReportsHaveConsistentCounts:
    """Validate the pilot alignment report JSON has consistent counts
    matching the expected values for the V3 pipeline."""

    def load_report(self):
        with open(REPORT_FILE, "r") as f:
            return json.load(f)

    def test_report_file_exists(self):
        assert REPORT_FILE.exists(), (
            f"Report file not found: {REPORT_FILE}"
        )

    def test_report_is_valid_json(self):
        try:
            self.load_report()
        except json.JSONDecodeError as e:
            pytest.fail(f"Report is not valid JSON: {e}")

    def test_event_count(self):
        report = self.load_report()
        assert report.get("event_count") == EXPECTED_COUNTS["event_count"], (
            f"event_count: expected {EXPECTED_COUNTS['event_count']}, "
            f"got {report.get('event_count')}"
        )

    def test_event_asset_pairs(self):
        report = self.load_report()
        assert report.get("event_asset_pairs") == EXPECTED_COUNTS["event_asset_pairs"], (
            f"event_asset_pairs: expected {EXPECTED_COUNTS['event_asset_pairs']}, "
            f"got {report.get('event_asset_pairs')}"
        )

    def test_horizon_window_records(self):
        report = self.load_report()
        assert report.get("horizon_window_records") == EXPECTED_COUNTS["horizon_window_records"], (
            f"horizon_window_records: expected {EXPECTED_COUNTS['horizon_window_records']}, "
            f"got {report.get('horizon_window_records')}"
        )

    def test_reaction_label_records(self):
        report = self.load_report()
        assert report.get("reaction_label_records") == EXPECTED_COUNTS["reaction_label_records"], (
            f"reaction_label_records: expected {EXPECTED_COUNTS['reaction_label_records']}, "
            f"got {report.get('reaction_label_records')}"
        )

    def test_cross_asset_context_records(self):
        report = self.load_report()
        assert report.get("cross_asset_context_records") == EXPECTED_COUNTS["cross_asset_context_records"], (
            f"cross_asset_context_records: expected {EXPECTED_COUNTS['cross_asset_context_records']}, "
            f"got {report.get('cross_asset_context_records')}"
        )

    def test_funding_context_records(self):
        report = self.load_report()
        assert report.get("funding_context_records") == EXPECTED_COUNTS["funding_context_records"], (
            f"funding_context_records: expected {EXPECTED_COUNTS['funding_context_records']}, "
            f"got {report.get('funding_context_records')}"
        )

    def test_precision_class(self):
        report = self.load_report()
        assert report.get("precision_class") == EXPECTED_PRECISION_CLASS, (
            f"precision_class: expected '{EXPECTED_PRECISION_CLASS}', "
            f"got '{report.get('precision_class')}'"
        )

    def test_all_expected_fields_present(self):
        """All expected count fields must be present in the report."""
        report = self.load_report()
        missing = [k for k in EXPECTED_COUNTS if k not in report]
        assert not missing, (
            f"Report missing expected fields: {missing}"
        )

    def test_sqlite_counts_match_report(self):
        """SQLite counts in the report must match the report's own
        JSONL counts (cross-check)."""
        report = self.load_report()
        field_pairs = [
            ("sqlite_horizon_windows", "horizon_window_records"),
            ("sqlite_reaction_labels", "reaction_label_records"),
            ("sqlite_cross_asset_context", "cross_asset_context_records"),
            ("sqlite_funding_context", "funding_context_records"),
        ]
        errors = []
        for sqlite_field, jsonl_field in field_pairs:
            sqlite_val = report.get(sqlite_field)
            jsonl_val = report.get(jsonl_field)
            if sqlite_val is not None and jsonl_val is not None and sqlite_val != jsonl_val:
                errors.append(
                    f"{sqlite_field} ({sqlite_val}) != {jsonl_field} ({jsonl_val})"
                )
        assert not errors, (
            "SQLite/file count mismatches in report:\n" + "\n".join(errors)
        )
