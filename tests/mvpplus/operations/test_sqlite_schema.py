"""Tests for sqlite_schema."""

from pathlib import Path

from market_radar.operations.sqlite_schema import (
    initialize_sqlite,
    get_connection,
    SCHEMA_VERSION,
)


class TestSqliteSchema:
    def test_initialization_creates_tables(self, tmp_path: Path):
        db = tmp_path / "test.db"
        msgs = initialize_sqlite(db)
        assert len(msgs) >= 1
        assert "schema at v1" in msgs[-1]

        conn = get_connection(db)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = {row[0] for row in tables}
        expected = {"schema_version", "run_history", "source_health",
                     "snapshot_metadata", "alert_candidates"}
        assert expected.issubset(names), f"missing tables: {expected - names}"
        conn.close()

    def test_migration_idempotent(self, tmp_path: Path):
        db = tmp_path / "idempotent.db"
        m1 = initialize_sqlite(db)
        m2 = initialize_sqlite(db)
        # Second call should not error and schema stays at same version
        assert len(m2) >= 1
        assert "v1" in m2[-1]

    def test_schema_version(self, tmp_path: Path):
        db = tmp_path / "version.db"
        initialize_sqlite(db)
        conn = get_connection(db)
        ver = conn.execute("PRAGMA user_version").fetchone()[0]
        assert ver == SCHEMA_VERSION
        conn.close()

    def test_indexes_created(self, tmp_path: Path):
        db = tmp_path / "indexes.db"
        initialize_sqlite(db)
        conn = get_connection(db)
        idxs = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
        ).fetchall()
        names = {row[0] for row in idxs}
        assert "idx_run_history_status" in names
        assert "idx_run_history_started" in names
        assert "idx_source_health_name" in names
        assert "idx_alert_candidates_type" in names
        conn.close()
