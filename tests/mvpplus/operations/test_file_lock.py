"""Tests for file_lock."""

import os
import time
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from market_radar.operations.file_lock import FileLock, STALE_LOCK_SECONDS, _pid_is_alive


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
        # Create an old lock file with a dead PID
        old_pid = 99999999  # extremely unlikely to be alive
        lock_path.write_text(f"{old_pid}|{time.time() - 600}|ops", encoding="utf-8")
        lock = FileLock(lock_path, stale_seconds=300)
        err = lock.try_acquire()
        assert err is None, f"stale lock should be overridden: {err}"
        assert lock.is_held
        lock.release()

    def test_active_pid_lock_not_overridden(self, tmp_path: Path):
        """A lock whose PID is alive must NOT be overridden even if timestamp is old."""
        lock_path = tmp_path / "active_stale.lock"
        own_pid = os.getpid()
        # Simulate old lock owned by current process (alive)
        lock_path.write_text(f"{own_pid}|{time.time() - 600}|ops", encoding="utf-8")
        lock = FileLock(lock_path, stale_seconds=300)
        err = lock.try_acquire()
        # Since we own the lock and we're alive, we should be able to re-acquire
        # Actually — our own PID is alive. The stale recovery policy says:
        # if PID is alive, don't recover. But since it's OUR PID, _is_self
        # should match, and the lock might still be acquired...
        # Wait no — try_acquire should return error because lock is held by a live PID
        # and that PID is NOT us... but it IS us.
        # Let me re-read the code:
        # Phase 2: if lock_pid is alive -> return error
        # Since it's our own PID, it's alive, and we CAN'T acquire.
        # Actually this is correct behavior — the lock says a live process holds it.
        # But in practice, if OUR process made the lock and WE are re-acquiring,
        # we should be able to override.
        # Hmm, actually the stale recovery policy says we don't recover if PID is alive.
        # But it's OUR PID! Let me re-read...
        # _pid_is_alive(os.getpid()) returns True. So error is returned.
        # This is intentionally conservative — release first, then re-acquire.
        assert err is not None
        assert "alive" in err.lower() or "held" in err.lower()
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

    def test_release_only_owned(self, tmp_path: Path):
        """release must not delete a lock owned by a different holder."""
        lock_path = tmp_path / "ownership.lock"
        lock1 = FileLock(lock_path)
        lock1.try_acquire()

        # Manually overwrite lock with another PID (simulate re-acquisition by other)
        other_pid = 99999998
        lock_path.write_text(f"{other_pid}|{time.time()}|ops-other", encoding="utf-8")

        # Acquire on lock1 should fail — other holds it
        # But when we release, we should NOT delete the file
        lock1.release()
        assert lock_path.exists(), "release should not delete another holder's lock"
        assert not lock1.is_held

        # Cleanup
        lock_path.unlink()

    def test_race_concurrent_acquire(self, tmp_path: Path):
        """Two simultaneous O_EXCL attempts must produce exactly one winner."""
        import threading as _threading
        lock_path = tmp_path / "race.lock"
        n_workers = 8
        winners: list[int] = []
        barrier = _threading.Barrier(n_workers)
        lock = _threading.Lock()

        def try_acquire(idx: int) -> None:
            fl = FileLock(lock_path, stale_seconds=30)
            # Wait until all threads are ready before racing
            barrier.wait()
            err = fl.try_acquire()
            if err is None:
                with lock:
                    winners.append(idx)
                # Hold until the barrier is satisfied so others race too
                time.sleep(0.2)
                fl.release()

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            pool.map(try_acquire, range(n_workers))

        assert len(winners) == 1, (
            f"expected exactly 1 winner, got {len(winners)}: winners={winners}"
        )

    def test_try_acquire_blocked_by_live_pid(self, tmp_path: Path):
        """Even with a very old timestamp, a live PID blocks acquisition."""
        lock_path = tmp_path / "live_stale.lock"
        own_pid = os.getpid()
        # Write a lock that claims to be from "long ago" but with OUR pid (which is alive)
        lock_path.write_text(f"{own_pid}|{time.time() - 3600}|ops", encoding="utf-8")
        lock = FileLock(lock_path, stale_seconds=300)
        err = lock.try_acquire()
        # Our PID is alive, so the lock must NOT be overridden just because it's old
        assert err is not None
        assert "alive" in err


class TestPidIsAlive:
    def test_own_pid(self):
        assert _pid_is_alive(os.getpid()) is True

    def test_nonexistent_pid(self):
        # Max PID on Linux is usually 2^22; on Windows 2^32.
        # Use a value that almost certainly doesn't exist.
        assert _pid_is_alive(999999999) is False
