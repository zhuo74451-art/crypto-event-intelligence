"""Minimal local durable-review runtime using SQLAlchemy ReviewIntent tables.

Not JSON-file based. Uses a controlled clock and no sleeping background process.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Optional, Tuple
from uuid import uuid4

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, make_transient, sessionmaker


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key enforcement on SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

Base = declarative_base()


class ReviewIntent(Base):
    __tablename__ = "review_intents"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    thesis_id = Column(String(36), nullable=False)
    idempotency_key = Column(String(255), nullable=False, unique=True)
    due_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False, default="PENDING")
    checkpoint_step = Column(Integer, nullable=False, default=0)
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DurableError(Exception):
    pass


class ReviewNotFoundError(DurableError):
    pass


class ReviewNotClaimableError(DurableError):
    pass


class DuplicateIdempotencyKeyError(DurableError):
    pass


class RetryExhaustedError(DurableError):
    pass


class MinimalDurableRuntime:
    """Foreground-only durable review runtime using SQLAlchemy.

    Controlled clock (pass `now` as datetime), no sleeping background process.
    """

    def __init__(self, db_path: Optional[str] = None, max_retries: int = 3):
        self._db_path = db_path or tempfile.mktemp(suffix=".db")
        self._max_retries = max_retries
        self._engine = create_engine(f"sqlite:///{self._db_path}", echo=False)
        Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(bind=self._engine)

    @property
    def db_path(self) -> str:
        return self._db_path

    def close(self) -> None:
        self._engine.dispose()

    @contextmanager
    def _session(self) -> Generator[Session, None, None]:
        session = self._Session(expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def persist_review(self, thesis_id: str, idempotency_key: str, due_at: datetime) -> str:
        """Persist one due ReviewIntent."""
        with self._session() as s:
            existing = s.query(ReviewIntent).filter(ReviewIntent.idempotency_key == idempotency_key).first()
            if existing:
                raise DuplicateIdempotencyKeyError(f"idempotency_key '{idempotency_key}' already exists")
            r = ReviewIntent(
                thesis_id=thesis_id,
                idempotency_key=idempotency_key,
                due_at=due_at,
            )
            s.add(r)
            s.flush()
            return r.id

    def claim_due(self, now: datetime) -> Optional[ReviewIntent]:
        """Atomically claim one due review within a transaction."""
        with self._session() as s:
            candidate = (
                s.query(ReviewIntent)
                .filter(ReviewIntent.status == "PENDING", ReviewIntent.due_at <= now)
                .order_by(ReviewIntent.due_at.asc())
                .first()
            )
            if candidate is None:
                return None
            candidate.status = "CLAIMED"
            s.flush()
            # Return a fresh copy to avoid detached attribute errors
            review_id = candidate.id
        with self._session() as s:
            return s.query(ReviewIntent).filter(ReviewIntent.id == review_id).first()

    def write_checkpoint(self, review_id: str, step: int, retry_count: int = 0, last_error: Optional[str] = None) -> None:
        """Persist step checkpoint."""
        with self._session() as s:
            r = s.query(ReviewIntent).filter(ReviewIntent.id == review_id).first()
            if r is None:
                raise ReviewNotFoundError(f"Review {review_id} not found")
            if r.status not in ("CLAIMED", "RUNNING"):
                raise ReviewNotClaimableError(f"Review {review_id} status is {r.status}, cannot write checkpoint")
            r.checkpoint_step = step
            r.retry_count = retry_count
            if last_error:
                r.last_error = last_error
            r.status = "RUNNING"

    def resume_checkpoint(self, review_id: str) -> Tuple[int, int, Optional[str]]:
        """Resume from last committed checkpoint."""
        with self._session() as s:
            r = s.query(ReviewIntent).filter(ReviewIntent.id == review_id).first()
            if r is None:
                raise ReviewNotFoundError(f"Review {review_id} not found")
            return r.checkpoint_step, r.retry_count, r.last_error

    def close_and_reopen(self) -> None:
        """Simulate close and reopen of the runtime (same database)."""
        self._engine.dispose()
        self._engine = create_engine(f"sqlite:///{self._db_path}", echo=False)
        Base.metadata.create_all(self._engine)
        self._Session = sessionmaker(bind=self._engine)

    def cancel_review(self, review_id: str) -> None:
        with self._session() as s:
            r = s.query(ReviewIntent).filter(ReviewIntent.id == review_id).first()
            if r is None:
                raise ReviewNotFoundError(f"Review {review_id} not found")
            r.status = "CANCELLED"
            s.flush()

    def resume_review(self, review_id: str) -> None:
        with self._session() as s:
            r = s.query(ReviewIntent).filter(ReviewIntent.id == review_id).first()
            if r is None:
                raise ReviewNotFoundError(f"Review {review_id} not found")
            r.status = "PENDING"
            r.checkpoint_step = 0
            r.retry_count = 0
            s.flush()

    def simulate_failure(self, review_id: str) -> None:
        """Inject a simulated failure — increments retry_count.

        Commits before raising RetryExhaustedError so FAILED state persists.
        """
        with self._session() as s:
            r = s.query(ReviewIntent).filter(ReviewIntent.id == review_id).first()
            if r is None:
                raise ReviewNotFoundError(f"Review {review_id} not found")
            r.retry_count += 1
            r.last_error = "simulated failure"
            if r.retry_count >= self._max_retries:
                r.status = "FAILED"
                s.flush()
                s.commit()
                raise RetryExhaustedError(f"Retry exhausted for {review_id}")

    def has_idempotency_key(self, idempotency_key: str) -> bool:
        with self._session() as s:
            return s.query(ReviewIntent).filter(ReviewIntent.idempotency_key == idempotency_key).first() is not None

    def get_review(self, review_id: str) -> Optional[ReviewIntent]:
        with self._session() as s:
            r = s.query(ReviewIntent).filter(ReviewIntent.id == review_id).first()
            if r is None:
                return None
            _id = r.id
        with self._session() as s:
            return s.query(ReviewIntent).filter(ReviewIntent.id == _id).first()
