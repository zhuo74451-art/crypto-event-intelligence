"""Non-destructive database backup and restore.

Uses SQLite's online backup API.  Source database is NEVER modified.
Restore writes to a NEW path only — never overwrites the original.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Optional

from market_radar.operations.atomic_json import _atomic_replace


def backup_database(
    source: str | Path,
    destination: str | Path,
    verify: bool = True,
) -> dict:
    """Create a non-destructive SQLite backup.

    Args:
        source: Path to the source database (NEVER modified).
        destination: Path for the backup file.
        verify: If True, run integrity_check and row-count comparison.

    Returns:
        Dict with status, paths, and verification results.

    Raises:
        FileNotFoundError: If source does not exist.
        ValueError: If destination already exists (default safety).
    """
    src = Path(source)
    dst = Path(destination)

    if not src.exists():
        raise FileNotFoundError(f"Source database not found: {src}")

    if dst.exists():
        raise ValueError(f"Destination already exists (refusing to overwrite): {dst}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Use a temp file atomically renamed to destination
    tmp = dst.with_name(f"{dst.name}.{uuid.uuid4().hex[:8]}.tmp")

    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(tmp))
    try:
        # Read source schema version before backup
        src_ver = src_conn.execute("PRAGMA user_version").fetchone()[0]
        src_row_count = src_conn.execute("SELECT COUNT(*) FROM run_history").fetchone()[0]

        src_conn.backup(dst_conn, pages=-1)
        dst_conn.commit()
    except Exception as e:
        # Clean up temp on failure
        dst_conn.close()
        src_conn.close()
        if tmp.exists():
            tmp.unlink()
        raise RuntimeError(f"Backup failed: {e}") from e
    finally:
        src_conn.close()
        dst_conn.close()

    # Atomic rename temp -> destination
    _atomic_replace(tmp, dst)

    result: dict = {
        "source": str(src),
        "destination": str(dst),
        "status": "created",
        "source_schema_version": src_ver,
        "source_row_count": src_row_count,
    }

    if verify:
        result["verification"] = _verify_backup(src, dst)

    return result


def restore_database_to_new_path(
    backup: str | Path,
    destination: str | Path,
    verify: bool = True,
) -> dict:
    """Restore a backup to a NEW path.

    Args:
        backup: Path to the backup file.
        destination: Path for the restored database (must NOT exist).
        verify: If True, run integrity_check and comparison.

    Returns:
        Dict with status, paths, and verification.
    """
    bak = Path(backup)
    dst = Path(destination)

    if not bak.exists():
        raise FileNotFoundError(f"Backup not found: {bak}")

    if dst.exists():
        raise ValueError(
            f"Destination already exists (refusing to overwrite): {dst}"
        )

    if bak.resolve() == dst.resolve():
        raise ValueError("Backup and destination are the same file")

    return backup_database(bak, dst, verify=verify)


def _verify_backup(original: Path, backup: Path) -> dict:
    """Verify backup integrity and consistency with the original."""
    result: dict = {}
    bak_conn = sqlite3.connect(str(backup))
    try:
        # Integrity check
        integrity = bak_conn.execute("PRAGMA integrity_check").fetchall()
        errors = [r[0] for r in integrity if r[0] != "ok"]
        result["integrity_check"] = "pass" if not errors else f"fail: {errors}"

        # Schema version
        bak_ver = bak_conn.execute("PRAGMA user_version").fetchone()[0]
        result["schema_version"] = bak_ver

        # Row count
        bak_count = bak_conn.execute("SELECT COUNT(*) FROM run_history").fetchone()[0]

        # Compare with original
        orig_conn = sqlite3.connect(str(original))
        try:
            orig_count = orig_conn.execute(
                "SELECT COUNT(*) FROM run_history"
            ).fetchone()[0]
            result["original_row_count"] = orig_count
            result["backup_row_count"] = bak_count
            result["row_count_match"] = orig_count == bak_count
        finally:
            orig_conn.close()

        # Parent-child consistency
        parent_count = bak_conn.execute(
            "SELECT COUNT(*) FROM run_history WHERE run_kind='shadow_parent'"
        ).fetchone()[0]
        child_count = bak_conn.execute(
            "SELECT COUNT(*) FROM run_history WHERE run_kind='shadow_child'"
        ).fetchone()[0]
        result["parent_count"] = parent_count
        result["child_count"] = child_count

    finally:
        bak_conn.close()

    return result
