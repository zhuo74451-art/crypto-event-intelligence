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
        assert "schema at v2" in msgs[-1]

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
        assert "v2" in m2[-1]

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
        # v2 indexes
        assert "idx_run_history_parent" in names
        assert "idx_run_history_parent_ordinal" in names
        assert "idx_run_history_kind" in names
        conn.close()

    # ------------------------------------------------------------------
    # v2 schema tests
    # ------------------------------------------------------------------

    def test_v2_columns_exist(self, tmp_path: Path):
        """v2 columns (parent_run_id, run_ordinal, run_kind) are present."""
        db = tmp_path / "v2_cols.db"
        initialize_sqlite(db)
        conn = get_connection(db)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(run_history)").fetchall()}
        assert "parent_run_id" in cols
        assert "run_ordinal" in cols
        assert "run_kind" in cols
        conn.close()

    def test_v2_columns_have_correct_defaults(self, tmp_path: Path):
        """New columns are nullable; run_kind defaults to 'standalone'."""
        db = tmp_path / "v2_defaults.db"
        initialize_sqlite(db)
        conn = get_connection(db)
        # Insert a row without specifying v2 columns
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at) VALUES (?, ?, ?, ?)",
            ("test-defaults", "test", "ok", "2025-01-01T00:00:00"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM run_history WHERE run_id='test-defaults'").fetchone()
        assert row["parent_run_id"] is None
        assert row["run_ordinal"] is None
        assert row["run_kind"] == "standalone"
        conn.close()

    def test_v1_migration_preserves_data(self, tmp_path: Path):
        """Simulate v1 schema, add data, migrate to v2, verify data survives."""
        import sqlite3
        db = tmp_path / "v1_to_v2.db"
        # Create v1 schema manually with PRAGMA user_version=1
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA user_version = 1")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS run_history (
                run_id TEXT PRIMARY KEY,
                runner_label TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                summary_json TEXT,
                error TEXT
            );
        """)
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at) "
            "VALUES ('v1-run', 'test', 'completed', '2025-01-01T00:00:00')",
        )
        conn.commit()
        conn.close()

        # Now migrate with initialize_sqlite
        msgs = initialize_sqlite(db)
        assert any("migrated" in m for m in msgs), f"migration message missing: {msgs}"

        # Verify data survived and v2 columns exist
        conn2 = get_connection(db)
        row = conn2.execute("SELECT * FROM run_history WHERE run_id='v1-run'").fetchone()
        assert row is not None
        assert row["runner_label"] == "test"
        # v2 columns should be present
        # Just access the column — KeyError if it doesn't exist
        _ = row["parent_run_id"]
        conn2.close()

    def test_repeated_initialize_idempotent_v2(self, tmp_path: Path):
        """Multiple initialize_sqlite calls on v2 DB must be safe."""
        db = tmp_path / "idempotent_v2.db"
        initialize_sqlite(db)
        for _ in range(3):
            msgs = initialize_sqlite(db)
            assert any("v2" in m for m in msgs), f"v2 not confirmed: {msgs}"
        # Verify data insertion still works
        conn = get_connection(db)
        conn.execute(
            "INSERT INTO run_history (run_id, runner_label, status, started_at, "
            "parent_run_id, run_ordinal, run_kind) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("v2-run", "test", "ok", "2025-01-01", "parent-1", 1, "shadow_child"),
        )
        conn.commit()
        conn.close()
