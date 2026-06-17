"""Run history persistence.

Records and queries run execution history.
Supports v2 parent-child linking.
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
    *,
    parent_run_id: Optional[str] = None,
    run_ordinal: Optional[int] = None,
    run_kind: str = "standalone",
) -> None:
    """Insert a run record.

    Args:
        db_path: Path to the SQLite database.
        run_id: Unique run identifier.
        runner_label: Label identifying the runner component.
        status: Current status string.
        error: Optional error description.
        summary: Optional structured summary dict.
        parent_run_id: Parent shadow run ID (for child linking, v2).
        run_ordinal: Ordinal within the parent run (v2).
        run_kind: Kind of run — ``standalone`` | ``shadow_parent`` | ``shadow_child`` | ``shadow_wrapper``.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection(db_path)
    try:
        conn.execute(
            """INSERT INTO run_history
               (run_id, runner_label, status, started_at, finished_at,
                summary_json, error, parent_run_id, run_ordinal, run_kind)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, runner_label, status, now, now,
             json.dumps(summary) if summary else None,
             error,
             parent_run_id, run_ordinal, run_kind),
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


# ---------------------------------------------------------------------------
# v2 Parent-child linking
# ---------------------------------------------------------------------------


def link_existing_run_to_parent(
    db_path: str | Path,
    run_id: str,
    parent_run_id: str,
    run_ordinal: int,
    run_kind: str = "shadow_child",
) -> bool:
    """Link an existing run record to a parent shadow run.

    Rules:
    1. *run_id* must already exist in the database.
    2. *parent_run_id* must already exist.
    3. *run_ordinal* must be a positive integer.
    4. Will not overwrite an existing *parent_run_id* that differs.
    5. Will not overwrite an existing *run_ordinal* that differs.
    6. Repeated calls with the same relationship are idempotent.
    7. Different children may not share the same ``(parent_run_id, run_ordinal)``.
    8. Does NOT modify child status, started_at, finished_at, summary, or error.

    Returns:
        ``True`` on success.  Raises ``ValueError`` on rule violation.
    """
    if not run_id:
        raise ValueError("run_id must be non-empty")
    if not parent_run_id:
        raise ValueError("parent_run_id must be non-empty")
    if not isinstance(run_ordinal, int) or run_ordinal < 1:
        raise ValueError(f"run_ordinal must be a positive integer, got {run_ordinal}")

    conn = get_connection(db_path)
    try:
        # Rule 1: child must exist
        child = conn.execute(
            "SELECT run_id, parent_run_id, run_ordinal FROM run_history WHERE run_id=?",
            (run_id,),
        ).fetchone()
        if child is None:
            raise ValueError(f"child run_id '{run_id}' does not exist")

        # Rule 2: parent must exist
        parent = conn.execute(
            "SELECT run_id FROM run_history WHERE run_id=?",
            (parent_run_id,),
        ).fetchone()
        if parent is None:
            raise ValueError(f"parent_run_id '{parent_run_id}' does not exist")

        # Rule 4: must not overwrite different parent_run_id
        existing_parent = child["parent_run_id"]
        if existing_parent is not None and existing_parent != parent_run_id:
            raise ValueError(
                f"run_id '{run_id}' already linked to parent "
                f"'{existing_parent}', cannot relink to '{parent_run_id}'"
            )

        # Rule 5: must not overwrite different run_ordinal
        existing_ordinal = child["run_ordinal"]
        if existing_ordinal is not None and existing_ordinal != run_ordinal:
            raise ValueError(
                f"run_id '{run_id}' already has ordinal {existing_ordinal}, "
                f"cannot change to {run_ordinal}"
            )

        # Rule 7: unique (parent_run_id, run_ordinal) — enforced by unique index
        # We check manually for a clearer error message
        conflict = conn.execute(
            """SELECT run_id FROM run_history
               WHERE parent_run_id=? AND run_ordinal=? AND run_id!=?""",
            (parent_run_id, run_ordinal, run_id),
        ).fetchone()
        if conflict is not None:
            raise ValueError(
                f"parent '{parent_run_id}' ordinal {run_ordinal} already "
                f"assigned to run_id '{conflict['run_id']}'"
            )

        # Apply the link
        conn.execute(
            """UPDATE run_history
               SET parent_run_id=?, run_ordinal=?, run_kind=?
               WHERE run_id=?""",
            (parent_run_id, run_ordinal, run_kind, run_id),
        )
        conn.commit()
        return True

    except ValueError:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        raise ValueError(f"link_existing_run_to_parent failed: {e}") from e
    else:
        conn.close()


def list_child_runs(
    db_path: str | Path,
    parent_run_id: str,
) -> list[dict[str, Any]]:
    """List child runs linked to a parent, ordered by run_ordinal.

    Returns:
        List of run records (as dicts) sorted by ``run_ordinal`` ASC.
    """
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            """SELECT * FROM run_history
               WHERE parent_run_id=?
               ORDER BY run_ordinal ASC""",
            (parent_run_id,),
        ).fetchall()
        results: list[dict[str, Any]] = []
        for row in rows:
            d = dict(row)
            if d.get("summary_json"):
                d["summary"] = json.loads(d["summary_json"])
            results.append(d)
        return results
    finally:
        conn.close()
