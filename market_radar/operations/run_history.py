"""Run history persistence.

Records and queries run execution history.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from market_radar.operations.sqlite_schema import get_connection


def insert_run(
    db_path: str | Path,
    run_id: str,
    runner_label: str,
    status: str,
    error: Optional[str] = None,
    summary: Optional[dict[str, Any]] = None,
) -> None:
    """Insert a run record."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO run_history (run_id, runner_label, status, started_at, finished_at, summary_json, error)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (run_id, runner_label, status, now, now,
             json.dumps(summary) if summary else None,
             error),
        )
        conn.commit()
    finally:
        conn.close()


def update_run_finish(
    db_path: str | Path,
    run_id: str,
    status: str,
    error: Optional[str] = None,
    summary: Optional[dict[str, Any]] = None,
) -> bool:
    """Update a run record on completion.

    Returns True if found and updated.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """UPDATE run_history SET status=?, finished_at=?, summary_json=?, error=?
               WHERE run_id=?""",
            (status, now, json.dumps(summary) if summary else None, error, run_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_run(db_path: str | Path, run_id: str) -> Optional[dict[str, Any]]:
    """Get a single run record."""
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT * FROM run_history WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("summary_json"):
            d["summary"] = json.loads(d["summary_json"])
        return d
    finally:
        conn.close()


def list_runs(
    db_path: str | Path,
    limit: int = 20,
    status_filter: Optional[str] = None,
) -> list[dict[str, Any]]:
    """List recent run records."""
    conn = get_connection(db_path)
    try:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM run_history WHERE status=? ORDER BY started_at DESC LIMIT ?",
                (status_filter, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM run_history ORDER BY started_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
