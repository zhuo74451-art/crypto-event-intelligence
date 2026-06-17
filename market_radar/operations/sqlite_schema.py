"""SQLite schema and migrations v1.

Managed tables:
  - run_history
  - source_health
  - snapshot_metadata
  - alert_candidates
  - schema_version
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA_VERSION = 1

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


def initialize_sqlite(db_path: str | Path) -> list[str]:
    """Initialize or migrate the ops SQLite database.

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

        if current_version < SCHEMA_VERSION:
            conn.executescript(SCHEMA_SQL)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            conn.commit()
            messages.append(f"schema migrated from v{current_version} to v{SCHEMA_VERSION}")
        else:
            messages.append(f"schema already at v{SCHEMA_VERSION}")

        # Verify tables exist
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

        messages.append(f"schema at v{SCHEMA_VERSION}")
    finally:
        conn.close()

    return messages


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
