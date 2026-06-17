"""Tests for file_lock."""

import os
import time
from pathlib import Path

from market_radar.operations.file_lock import FileLock, STALE_LOCK_SECONDS


class TestFileLock:
    def test_acquire_release(self, tmp_path: Path):
        lock_path = tmp_path / "test.lock"
        lock = FileLock(lock_path)
        err = lock.try_acquire()
        assert err is None
        assert lock.is_held
        lock.release()
        assert not lock.is_held
        assert not lock_path.exists()

    def test_second_instance_rejected(self, tmp_path: Path):
        lock_path = tmp_path / "test2.lock"
        lock1 = FileLock(lock_path)
        lock2 = FileLock(lock_path)
        assert lock1.try_acquire() is None
        err = lock2.try_acquire()
        assert err is not None
        assert "lock held" in err
        lock1.release()

    def test_stale_lock_allowed(self, tmp_path: Path):
        lock_path = tmp_path / "stale.lock"
        # Create an old lock file manually
        lock_path.write_text(f"12345|{time.time() - 600}|ops", encoding="utf-8")
        lock = FileLock(lock_path, stale_seconds=300)
        err = lock.try_acquire()
        assert err is None, f"stale lock should be overridden: {err}"
        assert lock.is_held
        lock.release()

    def test_context_manager(self, tmp_path: Path):
        lock_path = tmp_path / "ctx.lock"
        with FileLock(lock_path) as lock:
            assert lock.try_acquire() is None
            assert lock.is_held
        assert not lock_path.exists()

    def test_corrupted_lock(self, tmp_path: Path):
        lock_path = tmp_path / "corrupt.lock"
        lock_path.write_text("not_a_valid_format", encoding="utf-8")
        lock = FileLock(lock_path)
        err = lock.try_acquire()
        assert err is None
        lock.release()
