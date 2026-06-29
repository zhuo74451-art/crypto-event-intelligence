"""Versioned Event State store using SQLite."""
from __future__ import annotations
import json, sqlite3, threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from market_radar.cognition.contracts import EventState, EventRevision, SourceConflict, utc_now


class EventStore:
    def __init__(self, db_path: str):
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

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
            FOREIGN KEY (event_id) REFERENCES event_states(event_id)
        );
        CREATE TABLE IF NOT EXISTS source_conflicts (
            conflict_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            observation_id_a TEXT,
            observation_id_b TEXT,
            source_a TEXT,
            source_b TEXT,
            conflicting_field TEXT,
            resolved INTEGER DEFAULT 0,
            FOREIGN KEY (event_id) REFERENCES event_states(event_id)
        );
        CREATE INDEX IF NOT EXISTS idx_revisions_event ON event_revisions(event_id);
        CREATE INDEX IF NOT EXISTS idx_conflicts_event ON source_conflicts(event_id);
        """)
        self.conn.commit()

    def upsert_event(self, state: EventState) -> None:
        with self._lock:
            existing = self.conn.execute("SELECT state_json, revision FROM event_states WHERE event_id=?", (state.event_id,)).fetchone()
            if existing:
                prev = json.loads(existing["state_json"])
                new_rev = existing["revision"] + 1
                state.revision = new_rev
                state.state_updated_at = utc_now()
                self.conn.execute("UPDATE event_states SET revision=?, status=?, state_json=?, updated_at=? WHERE event_id=?", (new_rev, state.status, json.dumps(state.to_dict()), state.state_updated_at, state.event_id))
            else:
                state.revision = 1
                state.state_updated_at = utc_now()
                self.conn.execute("INSERT INTO event_states VALUES (?,?,?,?,?)", (state.event_id, 1, state.status, json.dumps(state.to_dict()), state.state_updated_at))
            self.conn.commit()

    def get_event(self, event_id: str) -> Optional[EventState]:
        row = self.conn.execute("SELECT state_json FROM event_states WHERE event_id=?", (event_id,)).fetchone()
        if row:
            return EventState.from_dict(json.loads(row[0]))
        return None

    def get_all_events(self) -> List[EventState]:
        rows = self.conn.execute("SELECT state_json FROM event_states ORDER BY event_id").fetchall()
        return [EventState.from_dict(json.loads(r[0])) for r in rows]

    def add_revision(self, rev: EventRevision) -> None:
        with self._lock:
            self.conn.execute("INSERT OR IGNORE INTO event_revisions VALUES (?,?,?,?,?,?,?)", (rev.revision_id, rev.event_id, rev.revision, rev.previous_status, rev.new_status, rev.reason, rev.timestamp or utc_now()))
            self.conn.commit()

    def get_revisions(self, event_id: str) -> List[EventRevision]:
        rows = self.conn.execute("SELECT * FROM event_revisions WHERE event_id=? ORDER BY revision", (event_id,)).fetchall()
        return [EventRevision(revision_id=r["revision_id"], event_id=r["event_id"], revision=r["revision"], previous_status=r["previous_status"], new_status=r["new_status"], reason=r["reason"], timestamp=r["timestamp"]) for r in rows]

    def add_conflict(self, conflict: SourceConflict) -> None:
        with self._lock:
            self.conn.execute("INSERT INTO source_conflicts (event_id, observation_id_a, observation_id_b, source_a, source_b, conflicting_field) VALUES (?,?,?,?,?,?)", (conflict.event_id, conflict.observation_id_a, conflict.observation_id_b, conflict.source_a, conflict.source_b, conflict.conflicting_field))
            self.conn.commit()

    def get_conflicts(self, event_id: str) -> List[Dict]:
        rows = self.conn.execute("SELECT * FROM source_conflicts WHERE event_id=?", (event_id,)).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()

    def rollback(self):
        self.conn.rollback()
