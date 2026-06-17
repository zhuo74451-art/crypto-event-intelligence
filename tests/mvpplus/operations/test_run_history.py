"""Tests for run_history."""

from pathlib import Path

from market_radar.operations.sqlite_schema import initialize_sqlite
from market_radar.operations.run_history import insert_run, get_run, list_runs, update_run_finish


class TestRunHistory:
    def setup_db(self, tmp_path: Path):
        db = tmp_path / "run_hist.db"
        initialize_sqlite(db)
        return db

    def test_insert_and_read(self, tmp_path: Path):
        db = self.setup_db(tmp_path)
        insert_run(db, "run_001", "test_runner", "ok")
        row = get_run(db, "run_001")
        assert row is not None
        assert row["run_id"] == "run_001"
        assert row["runner_label"] == "test_runner"
        assert row["status"] == "ok"

    def test_update_finish(self, tmp_path: Path):
        db = self.setup_db(tmp_path)
        insert_run(db, "run_002", "t", "running")
        ok = update_run_finish(db, "run_002", "ok")
        assert ok
        row = get_run(db, "run_002")
        assert row["status"] == "ok"

    def test_list_runs(self, tmp_path: Path):
        db = self.setup_db(tmp_path)
        insert_run(db, "r1", "t", "ok")
        insert_run(db, "r2", "t", "failed")
        rows = list_runs(db)
        assert len(rows) == 2

    def test_list_with_status_filter(self, tmp_path: Path):
        db = self.setup_db(tmp_path)
        insert_run(db, "r1", "t", "ok")
        insert_run(db, "r2", "t", "failed")
        ok_rows = list_runs(db, status_filter="ok")
        assert len(ok_rows) == 1
        assert ok_rows[0]["run_id"] == "r1"

    def test_get_nonexistent(self, tmp_path: Path):
        db = self.setup_db(tmp_path)
        row = get_run(db, "nonexistent")
        assert row is None
