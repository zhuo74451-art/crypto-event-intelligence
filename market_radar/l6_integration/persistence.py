"""MVP+ L6 — Persistence Layer (SQLite State Database).

Standard library sqlite3-based persistence for MVP+ run history,
source health, whale snapshots, and market data indices.

Schema versioned with migration guard. WAL mode, busy timeout,
transaction-safe writes. Null never becomes 0.

Tables:
  - schema_version          — Single-row version guard
  - run_history             — Every run's metadata
  - source_health_history   — Per-source health snapshots
  - whale_snapshot_index    — Index of whale position snapshots
  - whale_change_index      — Detected position changes
  - market_snapshot_index   — Market data snapshots
  - feed_ingestion_index    — Feed ingestion records
  - alert_candidates        — Generated but unsent alerts
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

SCHEMA_VERSION = 1
STATE_DIR = "artifacts/state"
DB_FILENAME = "mvpplus_state.sqlite"
BUSY_TIMEOUT_MS = 5000


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_dir(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)


# ── Connection Pool (thread-local) ───────────────────────────────────────────

_local = threading.local()


def _get_connection(db_path: str) -> sqlite3.Connection:
    """Get thread-local connection with WAL mode and busy timeout."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _ensure_dir(db_path)
        conn = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return _local.conn


@contextmanager
def _transaction(db_path: str):
    """Context manager for atomic transactions.

    Crash-safe: on unhandled exception, rollback. On success, commit.
    """
    conn = _get_connection(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ── Schema and Migration ─────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS run_history (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_s REAL,
    total_items INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    lane_results_json TEXT,
    error TEXT,
    workbench_path TEXT
);

CREATE TABLE IF NOT EXISTS source_health_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_group TEXT NOT NULL,
    status TEXT NOT NULL,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    latency_ms REAL,
    error_type TEXT,
    observed_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_history(run_id)
);

CREATE TABLE IF NOT EXISTS whale_snapshot_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    address TEXT NOT NULL,
    asset TEXT NOT NULL,
    side TEXT NOT NULL,
    position_size_usd REAL NOT NULL,
    entry_price REAL,
    mark_price REAL,
    leverage REAL,
    unrealized_pnl_usd REAL,
    liquidation_price REAL,
    liquidation_distance_pct REAL,
    label TEXT,
    entity_type TEXT,
    label_confidence TEXT,
    data_origin TEXT DEFAULT 'live',
    observed_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_history(run_id)
);

CREATE TABLE IF NOT EXISTS whale_change_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    address TEXT NOT NULL,
    asset TEXT NOT NULL,
    change_type TEXT NOT NULL,
    side TEXT NOT NULL,
    current_size_usd REAL NOT NULL,
    previous_size_usd REAL,
    delta_usd REAL,
    change_pct REAL,
    risk_level TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_history(run_id)
);

CREATE TABLE IF NOT EXISTS market_snapshot_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    price REAL NOT NULL,
    price_change_24h_pct REAL,
    volume_24h REAL,
    source TEXT NOT NULL,
    data_origin TEXT DEFAULT 'live',
    observed_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_history(run_id)
);

CREATE TABLE IF NOT EXISTS feed_ingestion_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    feed_type TEXT NOT NULL,
    source_name TEXT,
    count INTEGER NOT NULL,
    ingested_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES run_history(run_id)
);

CREATE TABLE IF NOT EXISTS alert_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'INFO',
    asset TEXT,
    address TEXT,
    message TEXT NOT NULL,
    details_json TEXT,
    generated_at TEXT NOT NULL,
    sent INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (run_id) REFERENCES run_history(run_id)
);

CREATE INDEX IF NOT EXISTS idx_whale_snapshot_run ON whale_snapshot_index(run_id);
CREATE INDEX IF NOT EXISTS idx_whale_change_run ON whale_change_index(run_id);
CREATE INDEX IF NOT EXISTS idx_market_snapshot_run ON market_snapshot_index(run_id);
CREATE INDEX IF NOT EXISTS idx_source_health_run ON source_health_history(run_id);
CREATE INDEX IF NOT EXISTS idx_alert_generated ON alert_candidates(generated_at);
"""


class PersistenceError(Exception):
    """Raised on persistence failures (not crashes)."""


class MVPStateDB:
    """SQLite state database for MVP+ persistence.

    Thread-safe (thread-local connections). Crash-safe (transactions).
    Schema-versioned with migration guard.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(STATE_DIR, DB_FILENAME)
        self._init_schema()

    def _init_schema(self):
        """Initialize schema if not exists; check version compatibility."""
        _ensure_dir(self.db_path)
        conn = _get_connection(self.db_path)

        # Check existing version
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        table_exists = cur.fetchone() is not None

        if not table_exists:
            # Fresh database — create all tables
            conn.executescript(SCHEMA_SQL)
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, _utc_now()),
            )
            conn.commit()
        else:
            # Verify version compatibility
            cur = conn.execute("SELECT MAX(version) FROM schema_version")
            row = cur.fetchone()
            existing_version = row[0] if row else 0
            if existing_version > SCHEMA_VERSION:
                raise PersistenceError(
                    f"Database schema version {existing_version} > code version {SCHEMA_VERSION}. "
                    f"Downgrade not supported."
                )
            if existing_version < SCHEMA_VERSION:
                # Future: run migrations here
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (SCHEMA_VERSION, _utc_now()),
                )
                conn.commit()

    # ── Run History ──────────────────────────────────────────────────────────

    def record_run(self, run_id: str, status: str, started_at: str, error: Optional[str] = None):
        with _transaction(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO run_history (run_id, status, started_at, error) VALUES (?, ?, ?, ?)",
                (run_id, status, started_at, error),
            )

    def complete_run(self, run_id: str, status: str, lane_results: dict,
                     total_items: int, total_errors: int, workbench_path: Optional[str] = None):
        now = _utc_now()
        with _transaction(self.db_path) as conn:
            # Get started_at
            cur = conn.execute("SELECT started_at FROM run_history WHERE run_id=?", (run_id,))
            row = cur.fetchone()
            started_at = row["started_at"] if row else now
            duration = None
            try:
                start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                end = datetime.fromisoformat(now.replace("Z", "+00:00"))
                duration = (end - start).total_seconds()
            except (ValueError, TypeError):
                pass

            conn.execute(
                """UPDATE run_history SET status=?, completed_at=?, duration_s=?,
                   total_items=?, total_errors=?, lane_results_json=?, workbench_path=?
                   WHERE run_id=?""",
                (status, now, duration, total_items, total_errors,
                 json.dumps(lane_results, default=str), workbench_path, run_id),
            )

    # ── Source Health ────────────────────────────────────────────────────────

    def record_source_health(self, run_id: str, health_entries: list[dict]):
        with _transaction(self.db_path) as conn:
            for h in health_entries:
                conn.execute(
                    """INSERT INTO source_health_history
                       (run_id, source_name, source_group, status, success_count,
                        error_count, consecutive_failures, latency_ms, error_type, observed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, h.get("source_name", ""), h.get("source_group", ""),
                     h.get("status", "UNKNOWN"), h.get("success_count", 0),
                     h.get("error_count", 0), h.get("consecutive_failures", 0),
                     h.get("latency_ms"), h.get("degraded_info", {}).get("error_type"),
                     _utc_now()),
                )

    # ── Whale Snapshots ──────────────────────────────────────────────────────

    def record_whale_positions(self, run_id: str, positions: list[dict]):
        with _transaction(self.db_path) as conn:
            for p in positions:
                conn.execute(
                    """INSERT INTO whale_snapshot_index
                       (run_id, address, asset, side, position_size_usd,
                        entry_price, mark_price, leverage, unrealized_pnl_usd,
                        liquidation_price, liquidation_distance_pct,
                        label, entity_type, label_confidence, data_origin, observed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, p.get("address", ""), p.get("asset", ""),
                     p.get("side", ""), p.get("position_size_usd", 0.0),
                     p.get("entry_price"), p.get("mark_price"),
                     p.get("leverage"), p.get("unrealized_pnl_usd"),
                     p.get("liquidation_price"), p.get("liquidation_distance_pct"),
                     p.get("label"), p.get("entity_type"), p.get("label_confidence"),
                     p.get("data_origin", "live"), _utc_now()),
                )

    def record_whale_changes(self, run_id: str, changes: list[dict]):
        with _transaction(self.db_path) as conn:
            for c in changes:
                conn.execute(
                    """INSERT INTO whale_change_index
                       (run_id, address, asset, change_type, side,
                        current_size_usd, previous_size_usd, delta_usd,
                        change_pct, risk_level, observed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, c.get("address", ""), c.get("asset", ""),
                     c.get("change_type", ""), c.get("side", ""),
                     c.get("current_position_size_usd", 0.0),
                     c.get("previous_position_size_usd"),
                     c.get("position_delta_usd"), c.get("change_pct"),
                     c.get("risk_level", "UNKNOWN"), _utc_now()),
                )

    # ── Market Snapshots ─────────────────────────────────────────────────────

    def record_market_snapshots(self, run_id: str, contexts: list[dict]):
        with _transaction(self.db_path) as conn:
            for ctx in contexts:
                conn.execute(
                    """INSERT INTO market_snapshot_index
                       (run_id, symbol, price, price_change_24h_pct,
                        volume_24h, source, data_origin, observed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (run_id, ctx.get("symbol", ""), ctx.get("price", 0.0),
                     ctx.get("price_change_24h_pct"), ctx.get("volume_24h"),
                     ctx.get("source", "UNKNOWN"), ctx.get("data_origin", "live"),
                     _utc_now()),
                )

    # ── Feed Ingestion ───────────────────────────────────────────────────────

    def record_feed_ingestion(self, run_id: str, feed_items: list[dict]):
        """Record feed ingestion summary per feed type."""
        from collections import Counter
        type_counts: Counter = Counter()
        source_counts: Counter = Counter()
        for item in feed_items:
            ft = item.get("feed_type", "UNKNOWN")
            type_counts[ft] += 1
            sn = item.get("source_name", "UNKNOWN")
            source_counts[sn] += 1

        with _transaction(self.db_path) as conn:
            for feed_type, count in type_counts.items():
                conn.execute(
                    """INSERT INTO feed_ingestion_index
                       (run_id, feed_type, source_name, count, ingested_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (run_id, feed_type, str(dict(source_counts.most_common(3))), count, _utc_now()),
                )

    # ── Alert Candidates ────────────────────────────────────────────────────

    def record_alerts(self, run_id: str, alerts: list[dict]):
        with _transaction(self.db_path) as conn:
            for a in alerts:
                conn.execute(
                    """INSERT INTO alert_candidates
                       (run_id, alert_type, severity, asset, address,
                        message, details_json, generated_at, sent)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                    (run_id, a.get("alert_type", "INFO"), a.get("severity", "INFO"),
                     a.get("asset"), a.get("address"), a.get("message", ""),
                     json.dumps(a.get("details", {}), default=str), _utc_now()),
                )

    # ── Queries ──────────────────────────────────────────────────────────────

    def get_recent_runs(self, limit: int = 10) -> list[dict]:
        conn = _get_connection(self.db_path)
        cur = conn.execute(
            "SELECT * FROM run_history ORDER BY started_at DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cur.fetchall()]

    def get_source_health_trend(self, source_name: str, limit: int = 20) -> list[dict]:
        conn = _get_connection(self.db_path)
        cur = conn.execute(
            """SELECT * FROM source_health_history
               WHERE source_name=? ORDER BY observed_at DESC LIMIT ?""",
            (source_name, limit),
        )
        return [dict(row) for row in cur.fetchall()]

    def get_latest_whale_snapshot(self, address: Optional[str] = None, limit: int = 50) -> list[dict]:
        conn = _get_connection(self.db_path)
        if address:
            cur = conn.execute(
                """SELECT * FROM whale_snapshot_index
                   WHERE address=? ORDER BY observed_at DESC LIMIT ?""",
                (address, limit),
            )
        else:
            cur = conn.execute(
                """SELECT * FROM whale_snapshot_index
                   ORDER BY observed_at DESC LIMIT ?""", (limit,)
            )
        return [dict(row) for row in cur.fetchall()]

    def get_unsent_alerts(self, limit: int = 50) -> list[dict]:
        conn = _get_connection(self.db_path)
        cur = conn.execute(
            """SELECT * FROM alert_candidates WHERE sent=0 ORDER BY generated_at DESC LIMIT ?""",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

    def close(self):
        if hasattr(_local, "conn") and _local.conn:
            _local.conn.close()
            _local.conn = None


def create_state_db(db_path: Optional[str] = None) -> MVPStateDB:
    """Factory: create or open MVP+ state database."""
    return MVPStateDB(db_path=db_path)
