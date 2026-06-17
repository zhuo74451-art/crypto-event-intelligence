"""Alert candidate index metadata persistence.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from market_radar.operations.sqlite_schema import get_connection


def insert_alert_candidate(
    db_path: str | Path,
    candidate_id: str,
    source_name: str,
    alert_type: str,
    summary: Optional[str] = None,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    """Record an alert candidate."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO alert_candidates
               (candidate_id, source_name, alert_type, detected_at, summary, detail_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (candidate_id, source_name, alert_type, now, summary,
             json.dumps(detail) if detail else None),
        )
        conn.commit()
    finally:
        conn.close()


def list_alerts(
    db_path: str | Path,
    limit: int = 20,
    unacknowledged_only: bool = False,
) -> list[dict[str, Any]]:
    """List alert candidates."""
    conn = get_connection(db_path)
    try:
        if unacknowledged_only:
            rows = conn.execute(
                "SELECT * FROM alert_candidates WHERE acknowledged=0 ORDER BY detected_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM alert_candidates ORDER BY detected_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
