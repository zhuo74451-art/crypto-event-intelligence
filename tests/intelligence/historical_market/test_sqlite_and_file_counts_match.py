"""Test SQLite tables have same counts as JSONL files.
Test V3 tables exist. Test non-V3 tables were not deleted."""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import sqlite3
import pytest

PILOT_DIR = Path("data/intelligence/historical_market/pilot_v3")
DB_PATH = Path("data/intelligence/historical_market/indexes/historical_market_v1.sqlite")

# Mapping: V3 SQLite table name -> (JSONL file path, expected row count)
V3_TABLE_FILE_MAP = {
    "pilot_v3_event_asset_windows": {
        "jsonl": PILOT_DIR / "horizon_windows_v3.jsonl",
        "expected_rows": 72,
    },
    "pilot_v3_reaction_labels": {
        "jsonl": PILOT_DIR / "reaction_labels_v3.jsonl",
        "expected_rows": 72,
    },
    "pilot_v3_cross_asset_context": {
        "jsonl": PILOT_DIR / "cross_asset_context_v3.jsonl",
        "expected_rows": 120,
    },
    "pilot_v3_funding_context": {
        "jsonl": PILOT_DIR / "funding_context_v3.jsonl",
        "expected_rows": 24,
    },
}

V3_ALIGNMENT_TABLE = "pilot_v3_alignment"
V3_ALIGNMENT_EXPECTED_ROWS = 1

# Non-V3 pilot tables that must still exist
NON_V3_PILOT_TABLES = {
    "pilot_v2_alignment",
    "pilot_v2_event_asset_windows",
    "pilot_v2_reaction_labels",
    "pilot_v2_funding_context",
    "pilot_v2_cross_asset_context",
}

# Other non-V3 system tables that should not have been deleted
OTHER_NON_V3_TABLES = {
    "market_bars",
    "market_index",
    "derivatives",
}


class TestSqliteAndFileCountsMatch:
    """Validate that SQLite V3 tables have the same row counts as the
    corresponding JSONL files, and that non-V3 tables were not deleted."""

    def load_jsonl_count(self, path):
        count = 0
        with open(path, "r") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def _get_all_tables(self):
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        return tables

    def test_db_file_exists(self):
        assert DB_PATH.exists(), f"SQLite database not found: {DB_PATH}"

    def test_v3_tables_exist(self):
        tables_found = self._get_all_tables()
        expected_v3 = set(V3_TABLE_FILE_MAP.keys()) | {V3_ALIGNMENT_TABLE}
        missing = expected_v3 - tables_found
        assert not missing, (
            f"Expected V3 table(s) not found: {missing}"
        )

    def test_v3_alignment_table_has_one_row(self):
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM "{V3_ALIGNMENT_TABLE}"')
        count = cursor.fetchone()[0]
        conn.close()
        assert count == V3_ALIGNMENT_EXPECTED_ROWS, (
            f"Table '{V3_ALIGNMENT_TABLE}': expected {V3_ALIGNMENT_EXPECTED_ROWS} row, "
            f"got {count}"
        )

    def test_sqlite_row_counts_match_jsonl(self):
        """For each V3 data table, the SQLite row count must equal the
        JSONL file line count."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        errors = []
        for table_name, spec in V3_TABLE_FILE_MAP.items():
            jsonl_path = spec["jsonl"]
            file_count = self.load_jsonl_count(jsonl_path)
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            db_count = cursor.fetchone()[0]
            if db_count != file_count:
                errors.append(
                    f"Table '{table_name}': SQLite has {db_count} rows, "
                    f"but JSONL has {file_count} rows"
                )
        conn.close()
        assert not errors, (
            "SQLite/JSONL count mismatches:\n" + "\n".join(errors)
        )

    def test_sqlite_expected_row_counts(self):
        """Spot-check the expected row counts for V3 tables match report."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        errors = []
        for table_name, spec in V3_TABLE_FILE_MAP.items():
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            count = cursor.fetchone()[0]
            expected = spec["expected_rows"]
            if count != expected:
                errors.append(
                    f"Table '{table_name}': expected {expected} rows, got {count}"
                )
        conn.close()
        assert not errors, (
            "Row count expectation errors:\n" + "\n".join(errors)
        )

    def test_non_v3_pilot_tables_not_deleted(self):
        """V2 pilot tables must still exist after V3 pipeline."""
        tables_found = self._get_all_tables()
        missing = NON_V3_PILOT_TABLES - tables_found
        assert not missing, (
            f"Non-V3 pilot table(s) were deleted: {missing}"
        )

    def test_other_non_v3_tables_not_deleted(self):
        """System tables like market_bars, market_index, derivatives
        must still exist."""
        tables_found = self._get_all_tables()
        missing = OTHER_NON_V3_TABLES - tables_found
        assert not missing, (
            f"Other non-V3 table(s) were deleted: {missing}"
        )
