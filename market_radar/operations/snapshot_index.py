"""Snapshot metadata index persistence.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from market_radar.operations.sqlite_schema import get_connection


def insert_snapshot(
    db_path: str | Path,
    snapshot_id: str,
    source_name: str,
    record_count: Optional[int] = None,
    size_bytes: Optional[int] = None,
    checksum_sha256: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Record a snapshot metadata entry."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO snapshot_metadata
               (snapshot_id, source_name, captured_at, record_count, size_bytes, checksum_sha256, metadata_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (snapshot_id, source_name, now, record_count, size_bytes, checksum_sha256,
             json.dumps(metadata) if metadata else None),
        )
        conn.commit()
    finally:
        conn.close()


def list_snapshots(db_path: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    """List recent snapshots."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM snapshot_metadata ORDER BY captured_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
