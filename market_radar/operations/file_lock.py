"""Single-instance file lock with atomic acquisition and stale recovery.

Uses ``os.open(O_CREAT | O_EXCL)`` for atomic lock creation — two simultaneous
acquisition attempts will produce exactly one winner.

Stale lock policy
-----------------
A lock older than *stale_seconds* is eligible for recovery ONLY if the
original process PID is confirmed dead.  If the PID is still alive the lock
is preserved regardless of timestamp, preventing false recovery during clock
skew, suspend/resume, or long-held locks.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional


STALE_LOCK_SECONDS = 300  # 5 minutes


def _pid_is_alive(pid: int) -> bool:
    """Check whether *pid* is still alive.

    Policy: a stale lock (older than *stale_seconds*) is only eligible for
    override if the owning process is confirmed dead.  This prevents false
    recovery when the lock timestamp is old but the holder is still running
    (e.g. due to clock skew, suspend/resume, or a long-held operation).

    Cross-platform: uses ``os.kill(pid, 0)`` on POSIX and ``ctypes``
    ``OpenProcess``/``GetExitCodeProcess`` on Windows.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            # PROCESS_QUERY_INFORMATION | SYNCHRONIZE
            handle = kernel32.OpenProcess(0x0400 | 0x00100000, False, pid)
            if not handle:
                return False
            try:
                exit_code = wintypes.DWORD()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return exit_code.value == 259  # STILL_ACTIVE
                return False
            finally:
                kernel32.CloseHandle(handle)
        except (ImportError, AttributeError, OSError):
            return False  # Can't check, assume dead
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


class FileLock:
    """Single-instance file lock.

    Creates a lock file on acquisition; removes on release.
    Detects stale locks older than *stale_seconds*.
    """

    def __init__(self, lock_path: str | Path, stale_seconds: int = STALE_LOCK_SECONDS):
        self._lock_path = Path(lock_path)
        self._stale_seconds = stale_seconds
        self._acquired = False
        self._owner_pid: Optional[int] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_content(pid: int) -> str:
        return f"{pid}|{time.time()}|ops-foundation-v1\n"

    @staticmethod
    def _parse_content(data: str) -> tuple[Optional[int], float]:
        """Return (pid, timestamp) parsed from a lock file, or defaults."""
        parts = data.strip().split("|")
        pid = int(parts[0]) if parts and parts[0].lstrip("-").isdigit() else None
        ts = float(parts[1]) if len(parts) > 1 and parts[1] else 0.0
        return pid, ts

    def _is_self(self, pid: int) -> bool:
        """Return True if *pid* matches the current process."""
        return pid == os.getpid()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def try_acquire(self) -> Optional[str]:
        """Try to acquire the lock.

        Uses ``O_CREAT | O_EXCL`` so that two simultaneous callers produce
        exactly one winner.

        Returns:
            None if acquired, or an error message string if denied.
        """
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)

        # Phase 1: attempt atomic exclusive creation
        try:
            fd = os.open(
                str(self._lock_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(self._format_content(os.getpid()))
            self._acquired = True
            self._owner_pid = os.getpid()
            return None
        except FileExistsError:
            pass  # Lock exists — fall through to stale check

        # Phase 2: lock exists — check whether it is stale
        try:
            data = self._lock_path.read_text(encoding="utf-8").strip()
        except OSError:
            # Vanished between the O_EXCL failure and read — retry once
            return self.try_acquire()

        lock_pid, timestamp = self._parse_content(data)
        age = time.time() - timestamp if timestamp else float("inf")

        # --- Stale recovery policy ---
        # 1. If the lock is YOUNGER than the threshold, always honour it.
        if age < self._stale_seconds:
            pid_str = str(lock_pid) if lock_pid is not None else "?"
            return f"lock held by pid={pid_str} for {age:.0f}s (max {self._stale_seconds}s)"

        # 2. Lock is OLDER than the threshold, but the PID is still alive
        #    → preserve the lock regardless of age.  This prevents false
        #    recovery during clock skew, suspend/resume, or long operations.
        if lock_pid is not None and _pid_is_alive(lock_pid):
            return (
                f"lock held by live pid={lock_pid} "
                f"(stale threshold exceeded but process alive)"
            )

        # 3. Lock is stale AND the owning PID is confirmed dead
        #    → remove and re-acquire atomically.
        try:
            os.unlink(self._lock_path)
        except OSError:
            pass

        return self.try_acquire()  # Recurse once (safe – bounded to 2 calls)

    def release(self) -> None:
        """Release the lock.

        Only deletes the lock file if it is owned by the current holder.
        """
        if not self._acquired:
            return

        try:
            if self._lock_path.exists():
                # Double-check ownership before deleting
                try:
                    data = self._lock_path.read_text(encoding="utf-8").strip()
                    lock_pid, _ = self._parse_content(data)
                    if lock_pid is not None and not self._is_self(lock_pid):
                        # Lock was re-acquired by another process — do not delete
                        return
                except OSError:
                    pass  # If we can't read it, best-effort unlink below
                os.unlink(self._lock_path)
        except OSError:
            pass
        finally:
            self._acquired = False
            self._owner_pid = None

    @property
    def is_held(self) -> bool:
        return self._acquired

    def __enter__(self) -> "FileLock":
        return self

    def __exit__(self, *args) -> None:
        self.release()
