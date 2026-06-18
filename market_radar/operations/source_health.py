"""Source health history persistence.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from market_radar.operations.sqlite_schema import get_connection


def record_health(
    db_path: str | Path,
    source_name: str,
    health_status: str,
    response_ms: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    """Record a source health check result."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO source_health (source_name, health_status, checked_at, response_ms, error_message)
               VALUES (?, ?, ?, ?, ?)""",
            (source_name, health_status, now, response_ms, error_message),
        )
        conn.commit()
    finally:
        conn.close()


def get_source_health(
    db_path: str | Path,
    source_name: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Get health history for a source."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT * FROM source_health WHERE source_name=? ORDER BY checked_at DESC LIMIT ?""",
            (source_name, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
