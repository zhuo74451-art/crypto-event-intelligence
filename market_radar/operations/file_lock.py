"""Single-instance file lock with stale detection.

Uses a PID file with timestamp to prevent concurrent ops runs.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

STALE_LOCK_SECONDS = 300  # 5 minutes


class FileLock:
    """Single-instance file lock.

    Creates a lock file on acquisition; removes on release.
    Detects stale locks older than *stale_seconds*.
    """

    def __init__(self, lock_path: str | Path, stale_seconds: int = STALE_LOCK_SECONDS):
        self._lock_path = Path(lock_path)
        self._stale_seconds = stale_seconds
        self._acquired = False

    def try_acquire(self) -> Optional[str]:
        """Try to acquire the lock.

        Returns:
            None if acquired, or an error message string if denied.
        """
        if self._lock_path.exists():
            try:
                data = self._lock_path.read_text(encoding="utf-8").strip()
                parts = data.split("|")
                pid = parts[0] if parts else "?"
                timestamp = float(parts[1]) if len(parts) > 1 and parts[1] else 0
                age = time.time() - timestamp

                if age < self._stale_seconds:
                    return f"lock held by pid={pid} for {age:.0f}s (max {self._stale_seconds}s)"

                # Stale — allow override
                os.unlink(self._lock_path)
            except (OSError, ValueError, IndexError):
                # Corrupted lock file — remove and retry
                try:
                    os.unlink(self._lock_path)
                except OSError:
                    pass

        try:
            self._lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._lock_path.write_text(
                f"{os.getpid()}|{time.time()}|ops-foundation-v1",
                encoding="utf-8",
            )
            self._acquired = True
            return None
        except OSError as e:
            return f"cannot write lock: {e}"

    def release(self) -> None:
        """Release the lock."""
        if self._acquired:
            try:
                if self._lock_path.exists():
                    os.unlink(self._lock_path)
            except OSError:
                pass
            self._acquired = False

    @property
    def is_held(self) -> bool:
        return self._acquired

    def __enter__(self) -> "FileLock":
        return self

    def __exit__(self, *args) -> None:
        self.release()
