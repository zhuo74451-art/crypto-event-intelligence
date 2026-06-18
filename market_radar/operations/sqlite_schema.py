"""SQLite schema and migrations v2.

Managed tables:
  - run_history          (v1 → v2: added parent_run_id, run_ordinal, run_kind)
  - source_health
  - snapshot_metadata
  - alert_candidates
  - schema_version

Version history
---------------
v1 — Original schema (five tables, run_history with minimal columns).
v2 — Added parent_run_id, run_ordinal, run_kind to run_history for
     bounded-shadow parent-child audit linking.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA_VERSION = 2

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS run_history (
    run_id          TEXT PRIMARY KEY,
    runner_label    TEXT NOT NULL,
    status          TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    summary_json    TEXT,
    error           TEXT
);

CREATE TABLE IF NOT EXISTS source_health (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name     TEXT NOT NULL,
    health_status   TEXT NOT NULL,
    checked_at      TEXT NOT NULL,
    response_ms     INTEGER,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS snapshot_metadata (
    snapshot_id     TEXT PRIMARY KEY,
    source_name     TEXT NOT NULL,
    captured_at     TEXT NOT NULL,
    record_count    INTEGER,
    size_bytes      INTEGER,
    checksum_sha256 TEXT,
    metadata_json   TEXT
);

CREATE TABLE IF NOT EXISTS alert_candidates (
    candidate_id    TEXT PRIMARY KEY,
    source_name     TEXT NOT NULL,
    alert_type      TEXT NOT NULL,
    detected_at     TEXT NOT NULL,
    summary         TEXT,
    detail_json     TEXT,
    acknowledged    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_run_history_status ON run_history(status);
CREATE INDEX IF NOT EXISTS idx_run_history_started ON run_history(started_at);
CREATE INDEX IF NOT EXISTS idx_source_health_name ON source_health(source_name);
CREATE INDEX IF NOT EXISTS idx_alert_candidates_type ON alert_candidates(alert_type);
"""

# v2 additions — add columns if missing, then create indexes.
V2_MIGRATION_SQL = """
ALTER TABLE run_history ADD COLUMN parent_run_id TEXT;
ALTER TABLE run_history ADD COLUMN run_ordinal INTEGER;
ALTER TABLE run_history ADD COLUMN run_kind TEXT DEFAULT 'standalone';
"""

V2_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_run_history_parent ON run_history(parent_run_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_run_history_parent_ordinal
    ON run_history(parent_run_id, run_ordinal)
    WHERE parent_run_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_run_history_kind ON run_history(run_kind);
"""


def initialize_sqlite(db_path: str | Path) -> list[str]:
    """Initialize or migrate the ops SQLite database.

    Handles v1 → v2 migration: adds ``parent_run_id``, ``run_ordinal``,
    and ``run_kind`` columns to ``run_history`` without data loss.

    Returns:
        List of migration messages (empty if already current).
    """
    messages: list[str] = []
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("PRAGMA user_version")
        current_version = cur.fetchone()[0]

        if current_version == 0:
            # Fresh install — create full v2 schema
            conn.executescript(SCHEMA_SQL)
            conn.executescript(V2_MIGRATION_SQL)
            conn.executescript(V2_INDEX_SQL)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.commit()
            messages.append(f"schema created at v{SCHEMA_VERSION}")
        elif current_version < SCHEMA_VERSION:
            # Incremental migration: current_version → SCHEMA_VERSION
            if current_version == 1:
                conn.executescript(V2_MIGRATION_SQL)
                conn.executescript(V2_INDEX_SQL)
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                conn.commit()
                messages.append("schema migrated from v1 to v2 (added parent_run_id, run_ordinal, run_kind)")
            else:
                messages.append(f"schema at unknown v{current_version}, upgrading to v{SCHEMA_VERSION}")
                conn.executescript(V2_MIGRATION_SQL)
                conn.executescript(V2_INDEX_SQL)
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                conn.commit()
        else:
            messages.append(f"schema already at v{SCHEMA_VERSION}")

        # Verify tables exist (v2 tables)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = {row[0] for row in tables}
        expected = {"schema_version", "run_history", "source_health",
                     "snapshot_metadata", "alert_candidates"}
        missing = expected - table_names
        if missing:
            messages.append(f"missing tables (re-applying schema): {missing}")
            conn.executescript(SCHEMA_SQL)
            conn.commit()

        # Verify v2 columns exist (idempotent ALTER — ignore if already exist)
        _ensure_v2_columns(conn)

        messages.append(f"schema at v{SCHEMA_VERSION}")
    finally:
        conn.close()

    return messages


def _ensure_v2_columns(conn: sqlite3.Connection) -> None:
    """Add v2 columns if missing (idempotent — safe to call repeatedly)."""
    cursor = conn.execute("PRAGMA table_info(run_history)")
    existing = {row[1] for row in cursor.fetchall()}
    v2_columns = {
        "parent_run_id": "TEXT",
        "run_ordinal": "INTEGER",
        "run_kind": "TEXT DEFAULT 'standalone'",
    }
    for col_name, col_type in v2_columns.items():
        if col_name not in existing:
            conn.execute(f"ALTER TABLE run_history ADD COLUMN {col_name} {col_type}")

    # Re-create indexes (IF NOT EXISTS is safe)
    conn.executescript(V2_INDEX_SQL)
    conn.commit()


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
