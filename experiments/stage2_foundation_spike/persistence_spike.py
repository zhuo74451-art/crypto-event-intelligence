"""
Experiment B – Persistence and Migration Spike.

Demonstrates:
- Schema migration (table creation) via SQLAlchemy.
- Transaction rollback on failed migration revision.
- Optimistic concurrency control using a version column.
- Re-open and recover (close connection, reopen, query).
- Foreign-key enforcement.
- Unique idempotency-key constraint.

All operations target a single SQLite file so the spike is self-contained.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    inspect,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


# ---------------------------------------------------------------------------
# ORM Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Event(Base):
    """A crypto event with an idempotency key for deduplication."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idempotency_key = Column(String(64), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    signals = relationship("Signal", back_populates="event", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_events_idempotency_key"),
    )


class Signal(Base):
    """A signal derived from an event, with a foreign key to Event."""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    signal_type = Column(String(64), nullable=False)
    value = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", back_populates="signals")


# ---------------------------------------------------------------------------
# Engine / session factory helpers
# ---------------------------------------------------------------------------

# Enable WAL + foreign keys for every new SQLite connection
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_engine_and_tables(db_path: str) -> Engine:
    """Create an engine, run DDL (create all tables), return the engine."""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine)


# ---------------------------------------------------------------------------
# Migration helpers (spike-level, not full Alembic)
# ---------------------------------------------------------------------------

REVISION_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS _alembic_revisions (
    revision_id VARCHAR(32) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def ensure_revision_table(engine: Engine) -> None:
    """Create the lightweight revision-tracking table used by our spike migrations."""
    with engine.connect() as conn:
        conn.execute(import_text(REVISION_TABLE_DDL))
        conn.commit()


def import_text(ddl: str):
    """Return a runnable text() object from a DDL string."""
    from sqlalchemy import text
    return text(ddl)


def get_applied_revisions(engine: Engine) -> set[str]:
    """Return the set of revision IDs already applied."""
    from sqlalchemy import text
    ensure_revision_table(engine)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT revision_id FROM _alembic_revisions")).fetchall()
        return {row[0] for row in rows}


def apply_migration(engine: Engine, revision_id: str, upgrade_ddl: str) -> None:
    """Apply a single migration revision idempotently."""
    from sqlalchemy import text
    ensure_revision_table(engine)
    applied = get_applied_revisions(engine)
    if revision_id in applied:
        return
    with engine.begin() as conn:
        for stmt in upgrade_ddl.split(";"):
            stripped = stmt.strip()
            if stripped:
                conn.execute(text(stripped))
        conn.execute(
            text("INSERT INTO _alembic_revisions (revision_id) VALUES (:rid)"),
            {"rid": revision_id},
        )


def rollback_revision(engine: Engine, revision_id: str, downgrade_ddl: str) -> None:
    """Roll back a single revision (used for testing rollback behaviour)."""
    from sqlalchemy import text
    ensure_revision_table(engine)
    with engine.begin() as conn:
        for stmt in downgrade_ddl.split(";"):
            stripped = stmt.strip()
            if stripped:
                conn.execute(text(stripped))
        conn.execute(
            text("DELETE FROM _alembic_revisions WHERE revision_id = :rid"),
            {"rid": revision_id},
        )


# ---------------------------------------------------------------------------
# Optimistic-lock helpers
# ---------------------------------------------------------------------------

class VersionConflictError(Exception):
    """Raised when an optimistic-lock update hits a stale version."""


def update_event(session: Session, event_id: int, expected_version: int,
                 **updates) -> Event:
    """
    Update an event only if its version matches *expected_version*.
    Increments the version on success.
    """
    event = session.get(Event, event_id)
    if event is None:
        raise ValueError(f"Event {event_id} not found")
    if event.version != expected_version:
        raise VersionConflictError(
            f"Version conflict for event {event_id}: "
            f"expected {expected_version}, got {event.version}"
        )
    for k, v in updates.items():
        setattr(event, k, v)
    event.version += 1
    session.flush()
    return event


def update_signal(session: Session, signal_id: int, expected_version: int,
                  **updates) -> Signal:
    """Update a signal with optimistic-lock semantics (same pattern as update_event)."""
    signal = session.get(Signal, signal_id)
    if signal is None:
        raise ValueError(f"Signal {signal_id} not found")
    if signal.version != expected_version:
        raise VersionConflictError(
            f"Version conflict for signal {signal_id}: "
            f"expected {expected_version}, got {signal.version}"
        )
    for k, v in updates.items():
        setattr(signal, k, v)
    signal.version += 1
    session.flush()
    return signal


# ---------------------------------------------------------------------------
# Context manager for an isolated session
# ---------------------------------------------------------------------------

@contextmanager
def session_scope(session_factory: sessionmaker) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Introspection helpers (used in tests)
# ---------------------------------------------------------------------------

def table_names(engine: Engine) -> list[str]:
    """Return the list of table names known to SQLAlchemy's inspector."""
    return inspect(engine).get_table_names()


def row_count(engine: Engine, table_name: str) -> int:
    """Return the number of rows in *table_name*."""
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        return result.scalar()
