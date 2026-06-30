"""Versioned Event State store using SQLite.

Provides explicit transactions, context-manager lifecycle, idempotent replay
(identical state does NOT increment revision), as-of reconstruction, and
foreign-key integrity.
"""

from __future__ import annotations
import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from market_radar.cognition.contracts import (
    EventState,
    EventRevision,
    SourceConflict,
    utc_now,
)


class EventStore:
    """SQLite-backed versioned event store."""

    def __init__(self, db_path: str):
        self._lock = threading.Lock()
        self._db_path = str(db_path)
        self.conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()
        self._depth = 0

    def __enter__(self) -> "EventStore":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            try:
                self.conn.rollback()
            except Exception:
                pass
        self.close()

    def transaction(self):
        return _TransactionContext(self)

    def _begin(self) -> None:
        self._depth += 1
        if self._depth == 1:
            self.conn.execute("BEGIN")

    def _commit(self) -> None:
        if self._depth == 1:
            self.conn.commit()
        self._depth -= 1

    def _rollback(self) -> None:
        if self._depth >= 1:
            self.conn.rollback()
            self._depth = 0

    def _init_schema(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS event_states (
            event_id TEXT PRIMARY KEY,
            revision INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL,
            state_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS event_revisions (
            revision_id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            revision INTEGER NOT NULL,
            previous_status TEXT,
            new_status TEXT,
            reason TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES event_states(event_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS source_conflicts (
            conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            observation_id_a TEXT,
            observation_id_b TEXT,
            source_a TEXT,
            source_b TEXT,
            conflicting_field TEXT,
            value_a TEXT,
            value_b TEXT,
            resolved INTEGER DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES event_states(event_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS observation_membership (
            observation_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            PRIMARY KEY (observation_id, event_id),
            FOREIGN KEY (event_id) REFERENCES event_states(event_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_revisions_event ON event_revisions(event_id);
        CREATE INDEX IF NOT EXISTS idx_conflicts_event ON source_conflicts(event_id);
        CREATE INDEX IF NOT EXISTS idx_membership_event ON observation_membership(event_id);
        """)
        self.conn.commit()

    def upsert_event(self, state: EventState) -> bool:
        """Insert or update *state*. Returns True if state changed."""
        with self._lock:
            existing = self.conn.execute(
                "SELECT state_json, revision FROM event_states WHERE event_id=?",
                (state.event_id,),
            ).fetchone()
            if existing:
                prev_json = existing["state_json"]
                new_dict = _strip_runtime(state.to_dict())
                prev_dict = _strip_runtime(json.loads(prev_json))
                if _canonical_json(new_dict) == _canonical_json(prev_dict):
                    return False
                new_rev = existing["revision"] + 1
                state.revision = new_rev
                state.state_updated_at = utc_now()
                self.conn.execute(
                    "UPDATE event_states SET revision=?, status=?, state_json=?, updated_at=? WHERE event_id=?",
                    (new_rev, state.status, json.dumps(state.to_dict()), state.state_updated_at, state.event_id),
                )
            else:
                state.revision = 1
                state.state_updated_at = utc_now()
                self.conn.execute(
                    "INSERT INTO event_states VALUES (?,?,?,?,?)",
                    (state.event_id, 1, state.status, json.dumps(state.to_dict()), state.state_updated_at),
                )
            return True

    def get_event(self, event_id: str) -> Optional[EventState]:
        row = self.conn.execute(
            "SELECT state_json FROM event_states WHERE event_id=?", (event_id,)
        ).fetchone()
        if row:
            return EventState.from_dict(json.loads(row[0]))
        return None

    def get_all_events(self) -> List[EventState]:
        rows = self.conn.execute(
            "SELECT state_json FROM event_states ORDER BY event_id"
        ).fetchall()
        return [EventState.from_dict(json.loads(r[0])) for r in rows]

    def get_event_as_of(self, event_id: str, as_of_timestamp: str) -> Optional[EventState]:
        """Return the EventState as it appeared at *as_of_timestamp*."""
        rows = self.conn.execute(
            "SELECT revision, state_json FROM event_states WHERE event_id=?", (event_id,)
        ).fetchall()
        if not rows:
            return None
        current = EventState.from_dict(json.loads(rows[0]["state_json"]))
        revs = self.conn.execute(
            "SELECT revision, new_status, timestamp FROM event_revisions WHERE event_id=? ORDER BY revision DESC",
            (event_id,),
        ).fetchall()
        target_status = current.status
        for r in revs:
            if r["timestamp"] and r["timestamp"] <= as_of_timestamp:
                break
            if r["new_status"]:
                target_status = r["new_status"]
        state = EventState.from_dict(current.to_dict())
        state.status = target_status
        return state

    def add_revision(self, rev: EventRevision) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO event_revisions VALUES (?,?,?,?,?,?,?)",
                (rev.revision_id, rev.event_id, rev.revision, rev.previous_status, rev.new_status, rev.reason, rev.timestamp or utc_now()),
            )

    def get_revisions(self, event_id: str) -> List[EventRevision]:
        rows = self.conn.execute(
            "SELECT * FROM event_revisions WHERE event_id=? ORDER BY revision", (event_id,)
        ).fetchall()
        return [
            EventRevision(
                revision_id=r["revision_id"], event_id=r["event_id"], revision=r["revision"],
                previous_status=r["previous_status"], new_status=r["new_status"],
                reason=r["reason"], timestamp=r["timestamp"],
            )
            for r in rows
        ]

    def add_observation_membership(self, observation_id: str, event_id: str) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO observation_membership VALUES (?,?)",
                (observation_id, event_id),
            )

    def get_observation_event_ids(self, observation_id: str) -> List[str]:
        rows = self.conn.execute(
            "SELECT event_id FROM observation_membership WHERE observation_id=?", (observation_id,)
        ).fetchall()
        return [r[0] for r in rows]

    def add_conflict(self, conflict: SourceConflict) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO source_conflicts (event_id, observation_id_a, observation_id_b, source_a, source_b, conflicting_field, value_a, value_b) VALUES (?,?,?,?,?,?,?,?)",
                (conflict.event_id, conflict.observation_id_a, conflict.observation_id_b, conflict.source_a, conflict.source_b, conflict.conflicting_field, conflict.value_a, conflict.value_b),
            )

    def get_conflicts(self, event_id: str) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM source_conflicts WHERE event_id=?", (event_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    def rollback(self):
        try:
            self.conn.rollback()
        except Exception:
            pass


class _TransactionContext:
    def __init__(self, store: EventStore):
        self._store = store

    def __enter__(self):
        self._store._begin()
        return self._store

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._store._rollback()
        else:
            self._store._commit()


def _strip_runtime(d: dict) -> dict:
    ignore = {"state_updated_at", "revision"}
    return {k: v for k, v in d.items() if k not in ignore}


def _canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, default=str)
