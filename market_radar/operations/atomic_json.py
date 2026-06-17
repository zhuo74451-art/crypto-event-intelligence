"""Atomic JSON artifact helper.

Writes JSON to a temp file, then atomically renames over the target.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


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
    tmp = target.with_suffix(".tmp")

    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if backup and target.exists():
        backup_path = target.with_suffix(".json.backup")
        shutil.copy2(str(target), str(backup_path))

    os.replace(str(tmp), str(target))
    return str(target.resolve())
