"""Atomic JSON artifact helper.

Writes JSON to a unique temp file in the target directory, then atomically
renames over the target (``os.replace``).

Every writer uses its own temp file (PID + nanosecond + monotonic sequence)
so concurrent writers to the same target never share a ``.tmp`` path.
"""

from __future__ import annotations

import json
import os
import time
from itertools import count
from pathlib import Path
from typing import Any

_UNIQUE_SEQ = count()


def _unique_tmp_path(target: Path) -> Path:
    """Return a temp path unique to this process and instant.

    The file is placed in the same directory as *target* for a same-filesystem
    rename.  The path includes PID + nanosecond timestamp + a monotonic
    sequence counter, guaranteeing uniqueness even under extreme concurrency.
    """
    pid = os.getpid()
    ns = time.time_ns()
    seq = next(_UNIQUE_SEQ)
    return target.with_name(f"{target.name}.{pid}.{ns}.{seq}.tmp")


def _atomic_replace(src: str | Path, dst: str | Path, max_retries: int = 5) -> None:
    """Replace *dst* with *src* using ``os.replace``.

    On Windows, the underlying ``MoveFileEx`` with ``MOVEFILE_REPLACE_EXISTING``
    can fail transiently with ``PermissionError`` / ``OSError`` when the target
    is momentarily locked by another thread, the filesystem, or antivirus.
    We retry with exponential back-off to cover this.

    Raises ``OSError`` if all retries are exhausted.
    """
    last_err: OSError | None = None
    for attempt in range(max_retries):
        try:
            os.replace(str(src), str(dst))
            return
        except (PermissionError, OSError) as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(0.01 * (2 ** attempt))
    raise OSError(
        f"cannot replace {dst} with {src} after {max_retries} retries"
    ) from last_err


def atomic_write_json(
    data: Any,
    path: str | Path,
    backup: bool = False,
) -> str:
    """Write JSON with atomic rename.

    Args:
        data: JSON-serializable data.
        path: Target file path.
        backup: If True, preserve existing file as .backup.

    Returns:
        Absolute path of the written file.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Unique temp path per call — eliminates cross-writer collisions.
    tmp = _unique_tmp_path(target)

    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if backup and target.exists():
        backup_path = target.with_suffix(".json.backup")
        import shutil
        shutil.copy2(str(target), str(backup_path))

    _atomic_replace(tmp, target)
    return str(target.resolve())
