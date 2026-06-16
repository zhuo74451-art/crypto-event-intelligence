"""MVP+ L6 — Single-Instance Lock.

Prevents two MVP+ runners from running simultaneously and
corrupting state. File-based lock with stale recovery.

Rules:
  - Lock file stored in artifacts/state/
  - Contains PID, hostname, run_id, timestamp
  - Stale lock auto-recovered after LOCK_TTL_SECONDS
  - Never kills other processes
  - Cleanup on normal exit
"""

from __future__ import annotations

import json
import os
import socket
import time
from datetime import datetime, timezone
from typing import Optional

STATE_DIR = "artifacts/state"
LOCK_FILE = "mvpplus_runner.lock"
LOCK_TTL_SECONDS = 300  # 5 min — a run should never take this long


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


class LockError(Exception):
    """Raised when lock cannot be acquired."""


class LockHeldByAnotherInstance(LockError):
    """Raised when another instance holds the lock."""
    def __init__(self, lock_info: dict):
        self.lock_info = lock_info
        super().__init__(
            f"Lock held by run_id={lock_info.get('run_id')} "
            f"(pid={lock_info.get('pid')}, host={lock_info.get('hostname')}) "
            f"since {lock_info.get('acquired_at')}"
        )


class StaleLock(LockError):
    """Raised when lock is stale but recovery already attempted."""
    def __init__(self, lock_info: dict):
        self.lock_info = lock_info
        super().__init__(
            f"Stale lock from {lock_info.get('acquired_at')} could not be recovered: "
            f"run_id={lock_info.get('run_id')}"
        )


class MVPPLock:
    """Single-instance file lock for MVP+ runner.

    Usage:
        lock = MVPPLock()
        try:
            lock.acquire(run_id)
            # ... run logic ...
        finally:
            lock.release()
    """

    def __init__(self, lock_dir: Optional[str] = None, ttl: int = LOCK_TTL_SECONDS):
        self.lock_dir = lock_dir or STATE_DIR
        self.lock_path = os.path.join(self.lock_dir, LOCK_FILE)
        self.ttl = ttl
        self._held = False
        self._run_id: Optional[str] = None
        _ensure_dir(self.lock_path)

    def acquire(self, run_id: str) -> bool:
        """Acquire the lock.

        Returns True if acquired.
        Raises LockHeldByAnotherInstance if another instance holds a valid lock.
        Raises IOError if filesystem error.
        """
        self._run_id = run_id
        lock_info = {
            "run_id": run_id,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "acquired_at": _utc_now(),
        }

        lock_path = self.lock_path

        # Check if lock exists
        if os.path.isfile(lock_path):
            try:
                with open(lock_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, OSError):
                # Corrupted lock file — treat as stale
                existing = {"run_id": "unknown"}

            # Check if stale
            acquired_str = existing.get("acquired_at", "")
            stale = False
            if acquired_str:
                try:
                    acquired_time = datetime.fromisoformat(acquired_str.replace("Z", "+00:00"))
                    age = (datetime.now(timezone.utc) - acquired_time).total_seconds()
                    stale = age > self.ttl
                except (ValueError, TypeError):
                    stale = True  # Unparseable timestamp → stale
            else:
                stale = True

            if stale:
                # Stale lock — remove and re-acquire
                try:
                    os.remove(lock_path)
                except OSError:
                    pass
            else:
                raise LockHeldByAnotherInstance(existing)

        # Write lock file atomically
        tmp_path = lock_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(lock_info, f, indent=2)
            os.replace(tmp_path, lock_path)
        except OSError as e:
            raise IOError(f"Failed to write lock file: {e}")

        self._held = True
        return True

    def release(self):
        """Release the lock. Safe to call multiple times."""
        if self._held and os.path.isfile(self.lock_path):
            try:
                # Verify we own this lock (don't delete someone else's)
                with open(self.lock_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if existing.get("run_id") == self._run_id:
                    os.remove(self.lock_path)
            except (OSError, json.JSONDecodeError):
                # If we can't read it, don't delete it
                pass
        self._held = False
        self._run_id = None

    @property
    def held(self) -> bool:
        return self._held

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False  # Don't suppress exceptions


def create_lock(lock_dir: Optional[str] = None) -> MVPPLock:
    return MVPPLock(lock_dir=lock_dir)
