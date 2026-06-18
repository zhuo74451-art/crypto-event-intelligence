"""Tests for recovery."""

import time
from pathlib import Path

from market_radar.operations.sqlite_schema import initialize_sqlite
from market_radar.operations.run_history import insert_run
from market_radar.operations.recovery import find_interrupted_run, recovery_state


class TestRecovery:
    def test_no_interrupted(self, tmp_path: Path):
        db = tmp_path / "clean.db"
        initialize_sqlite(db)
        insert_run(db, "r1", "t", "ok")
        r = find_interrupted_run(db)
        assert r is None

    def test_failed_run_found(self, tmp_path: Path):
        db = tmp_path / "failed.db"
        initialize_sqlite(db)
        insert_run(db, "r1", "t", "failed", error="oops")
        r = find_interrupted_run(db)
        assert r is not None
        assert r["run_id"] == "r1"

    def test_recovery_state(self, tmp_path: Path):
        db = tmp_path / "state.db"
        initialize_sqlite(db)
        insert_run(db, "r1", "t", "ok")
        state = recovery_state(db)
        assert state["interrupted"] is False

    def test_recovery_with_stale_lock(self, tmp_path: Path):
        db = tmp_path / "lock_state.db"
        initialize_sqlite(db)
        lock_path = tmp_path / "ops.lock"
        # Create old lock
        lock_path.write_text(f"12345|{time.time() - 600}|ops", encoding="utf-8")
        state = recovery_state(db, lock_path=lock_path)
        assert state["lock_stale"] is True
