"""Test that the SQLite index database has the expected pilot_v2 tables,
column names, and row counts."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import sqlite3
import pytest

DB_PATH = Path("data/intelligence/historical_market/indexes/historical_market_v1.sqlite")

EXPECTED_TABLES = {
    "pilot_v2_alignment": {
        "cols": ["run_id", "pilot_version", "started_at_utc", "event_count",
                 "asset_count", "horizon_count", "expected_windows",
                 "actual_windows", "expected_labels", "actual_labels",
                 "report_generated_at_utc"],
        "rows": 1,
    },
    "pilot_v2_event_asset_windows": {
        "cols": ["window_id", "event_id", "event_family", "event_time_utc",
                 "instrument_id", "symbol", "horizon", "pre_bar_close",
                 "event_bar_open", "event_bar_close", "post_bar_close",
                 "return_pct", "direction"],
        "rows": 72,
    },
    "pilot_v2_reaction_labels": {
        "cols": ["label_id", "event_id", "instrument_id", "symbol",
                 "event_time_utc", "horizon", "return_pct", "direction",
                 "label_availability"],
        "rows": 72,
    },
    "pilot_v2_funding_context": {
        "cols": ["id", "event_id", "event_time_utc", "instrument_id",
                 "symbol", "funding_rate"],
        "rows": 24,
    },
    "pilot_v2_cross_asset_context": {
        "cols": ["id", "event_id", "event_time_utc", "instrument_id",
                 "symbol", "series_name", "series_close"],
        "rows": 0,
    },
}


class TestPilotSqliteIndex:
    """Validate the historical_market_v1.sqlite index database."""

    def test_db_file_exists(self):
        assert DB_PATH.exists(), f"SQLite database not found: {DB_PATH}"

    def test_pilot_v2_tables_exist(self):
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name LIKE 'pilot_v2_%' ORDER BY name"
        )
        tables_found = {row[0] for row in cursor.fetchall()}
        conn.close()
        for expected in EXPECTED_TABLES:
            assert expected in tables_found, (
                f"Expected table '{expected}' not found in database"
            )

    def test_table_columns_and_row_counts(self):
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        errors = []
        for table_name, spec in EXPECTED_TABLES.items():
            # Check columns
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            actual_cols = [row[1] for row in cursor.fetchall()]
            expected_cols = spec["cols"]
            if actual_cols != expected_cols:
                errors.append(
                    f"Table '{table_name}' columns mismatch:\n"
                    f"  Expected: {expected_cols}\n"
                    f"  Got:      {actual_cols}"
                )
            # Check row count
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            actual_rows = cursor.fetchone()[0]
            expected_rows = spec["rows"]
            if actual_rows != expected_rows:
                errors.append(
                    f"Table '{table_name}' row count mismatch: "
                    f"expected {expected_rows}, got {actual_rows}"
                )
        conn.close()
        assert not errors, "SQLite table validation errors:\n" + "\n".join(errors)

    def test_no_unexpected_pilot_v2_tables(self):
        """Only the expected pilot_v2 tables should exist (no orphan tables)."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name LIKE 'pilot_v2_%' ORDER BY name"
        )
        tables_found = {row[0] for row in cursor.fetchall()}
        conn.close()
        expected_set = set(EXPECTED_TABLES.keys())
        unexpected = tables_found - expected_set
        assert not unexpected, (
            f"Unexpected pilot_v2 tables found: {unexpected}"
        )
