"""Cognition v2 SQLAlchemy models.

Dependency: domain contracts only. No operator, application, or CLI imports.
"""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Generator, Optional
from uuid import uuid4

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint, create_engine, event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys and WAL mode on SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


Base = declarative_base()


def _new_uuid() -> str:
    return str(uuid4())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════════════
# Sources
# ═══════════════════════════════════════════════════════════════════════════════

class SourceModel(Base):
    __tablename__ = "sources"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    name = Column(String(255), nullable=False, unique=True)
    source_type = Column(String(64), nullable=False)
    authority = Column(String(32), nullable=False, default="unknown")
    fact_permission = Column(String(32), nullable=False, default="none")
    base_url = Column(String(512), nullable=True)
    fingerprint_hash = Column(String(64), nullable=True)
    health = Column(String(32), nullable=False, default="unknown")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=_utc_now)
    updated_at = Column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


class SourceHealthModel(Base):
    __tablename__ = "source_health"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    health_status = Column(String(32), nullable=False, default="unknown")
    last_ok_at = Column(DateTime(timezone=True), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime(timezone=True), default=_utc_now)


# ═══════════════════════════════════════════════════════════════════════════════
# Evidence
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceModel(Base):
    __tablename__ = "evidence"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    source_name = Column(String(255), nullable=False)
    content_hash = Column(String(64), nullable=False, unique=True)
    body_text = Column(Text, nullable=True)
    publication_time = Column(DateTime(timezone=True), nullable=True)
    effective_time = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    retrieval_time = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    assessment_time = Column(DateTime(timezone=True), nullable=True)
    fact_permission = Column(String(32), nullable=False, default="none")
    authority = Column(String(32), nullable=False, default="unknown")
    version = Column(Integer, nullable=False, default=1)
    is_correction = Column(Integer, nullable=False, default=0)
    corrects_evidence_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now)


# ═══════════════════════════════════════════════════════════════════════════════
# Events
# ═══════════════════════════════════════════════════════════════════════════════

class EventModel(Base):
    __tablename__ = "events"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    event_family = Column(String(64), nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    event_time = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    version = Column(Integer, nullable=False, default=1)
    event_state = Column(String(32), nullable=False, default="DISCOVERED")
    is_resolved = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=_utc_now)


class EventRevisionModel(Base):
    __tablename__ = "event_revisions"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    event_id = Column(String(36), ForeignKey("events.id"), nullable=False)
    version = Column(Integer, nullable=False)
    previous_version = Column(Integer, nullable=True)
    revision_body = Column(Text, nullable=False)
    revision_outcome = Column(String(32), nullable=False)
    reason = Column(Text, nullable=False)
    idempotency_key = Column(String(255), nullable=True, unique=True)
    rule_refs_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now)
    __table_args__ = (UniqueConstraint("event_id", "version", name="uq_event_revision_version"),)


# ═══════════════════════════════════════════════════════════════════════════════
# Theses
# ═══════════════════════════════════════════════════════════════════════════════

class ThesisModel(Base):
    __tablename__ = "theses"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    claim_class = Column(String(32), nullable=False)
    summary = Column(Text, nullable=False)
    lifecycle_state = Column(String(32), nullable=False, default="DISCOVERED")
    version = Column(Integer, nullable=False, default=1)
    horizon = Column(String(32), nullable=True)
    portfolio_class = Column(String(64), nullable=True)
    review_by = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now)
    updated_at = Column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now)


class ThesisRevisionModel(Base):
    __tablename__ = "thesis_revisions"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    thesis_id = Column(String(36), ForeignKey("theses.id"), nullable=False)
    version = Column(Integer, nullable=False)
    previous_version = Column(Integer, nullable=True)
    revision_body = Column(Text, nullable=False)
    revision_outcome = Column(String(32), nullable=False)
    lifecycle_state = Column(String(32), nullable=False)
    previous_state = Column(String(32), nullable=True)
    reason = Column(Text, nullable=False)
    idempotency_key = Column(String(255), nullable=True, unique=True)
    request_fingerprint = Column(String(64), nullable=True)
    evidence_refs_json = Column(Text, nullable=True)
    rule_refs_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now)
    __table_args__ = (UniqueConstraint("thesis_id", "version", name="uq_thesis_revision_version"),)


# ═══════════════════════════════════════════════════════════════════════════════
# Claims and exposures
# ═══════════════════════════════════════════════════════════════════════════════

class ClaimModel(Base):
    __tablename__ = "claims"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    thesis_id = Column(String(36), ForeignKey("theses.id"), nullable=True)
    claim_class = Column(String(32), nullable=False)
    summary = Column(Text, nullable=False)
    evidence_status = Column(String(32), nullable=False)
    horizon = Column(String(32), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=_utc_now)


class ExposureLinkModel(Base):
    __tablename__ = "exposure_links"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    thesis_id = Column(String(36), ForeignKey("theses.id"), nullable=False)
    asset_identifier = Column(String(255), nullable=False)
    asset_type = Column(String(64), nullable=False, default="crypto_asset")
    direction = Column(String(32), nullable=True)
    strength = Column(String(32), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=_utc_now)


class CounterEvidenceModel(Base):
    __tablename__ = "counter_evidence"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    thesis_id = Column(String(36), ForeignKey("theses.id"), nullable=False)
    claim_class = Column(String(32), nullable=False)
    description = Column(Text, nullable=False)
    alternative_explanation = Column(Text, nullable=True)
    source_id = Column(String(36), ForeignKey("sources.id"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=_utc_now)


# ═══════════════════════════════════════════════════════════════════════════════
# Review intents
# ═══════════════════════════════════════════════════════════════════════════════

class ReviewIntentModel(Base):
    __tablename__ = "review_intents"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    thesis_id = Column(String(36), ForeignKey("theses.id"), nullable=False)
    idempotency_key = Column(String(255), nullable=False, unique=True)
    due_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False, default="PENDING")
    checkpoint_step = Column(Integer, nullable=False, default=0)
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    trigger_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now)


# ═══════════════════════════════════════════════════════════════════════════════
# Attention and notifications
# ═══════════════════════════════════════════════════════════════════════════════

class AttentionModel(Base):
    __tablename__ = "attention_allocations"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    thesis_id = Column(String(36), ForeignKey("theses.id"), nullable=False)
    allocated_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    priority = Column(Integer, nullable=False, default=0)
    reason = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    source = Column(String(64), nullable=False, default="scheduler")


class NotificationModel(Base):
    __tablename__ = "notification_decisions"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    thesis_id = Column(String(36), ForeignKey("theses.id"), nullable=False)
    action_type = Column(String(32), nullable=False)
    reason = Column(Text, nullable=False)
    notification_body = Column(Text, nullable=True)
    is_material = Column(Integer, nullable=False, default=0)
    decided_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    version = Column(Integer, nullable=False, default=1)


# ═══════════════════════════════════════════════════════════════════════════════
# Provenance
# ═══════════════════════════════════════════════════════════════════════════════

class ProvenanceEdgeModel(Base):
    __tablename__ = "provenance_edges"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    source_id = Column(String(36), nullable=False)
    target_id = Column(String(36), nullable=False)
    relationship_type = Column(String(64), nullable=False)
    reason = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=_utc_now)
    version = Column(Integer, nullable=False, default=1)


# ═══════════════════════════════════════════════════════════════════════════════
# Historical replay
# ═══════════════════════════════════════════════════════════════════════════════

class HistoricalCaseModel(Base):
    __tablename__ = "historical_cases"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    case_id = Column(String(128), nullable=False, unique=True)
    event_family = Column(String(64), nullable=False)
    market_regime = Column(String(32), nullable=False, default="unknown")
    split_label = Column(String(32), nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    event_time = Column(DateTime(timezone=True), nullable=True)
    evidence_manifest_hash = Column(String(64), nullable=False)
    # R21 — Durable event and correction-chain identity
    event_identity_id = Column(String(128), nullable=True)
    correction_chain_id = Column(String(128), nullable=True)
    chain_root_case_id = Column(String(128), nullable=True)
    correction_type = Column(String(32), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=_utc_now)


class OutcomeWindowModel(Base):
    __tablename__ = "outcome_windows"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    case_id = Column(String(36), ForeignKey("historical_cases.id"), nullable=False)
    window_label = Column(String(16), nullable=False)
    event_id = Column(String(36), nullable=False)
    open_time = Column(DateTime(timezone=True), nullable=False)
    close_time = Column(DateTime(timezone=True), nullable=False)
    open_price = Column(Float, nullable=True)
    close_price = Column(Float, nullable=True)
    high_price = Column(Float, nullable=True)
    low_price = Column(Float, nullable=True)
    volume = Column(Float, nullable=True)
    return_pct = Column(Float, nullable=True)
    direction = Column(String(16), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=_utc_now)


# ═══════════════════════════════════════════════════════════════════════════════
# Version records
# ═══════════════════════════════════════════════════════════════════════════════

class RunRecordModel(Base):
    __tablename__ = "run_records"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    run_type = Column(String(64), nullable=False, default="inference")
    started_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    configuration_version = Column(String(64), nullable=False, default="1.0")
    schema_version = Column(String(64), nullable=False, default="1.0")
    model_version = Column(String(64), nullable=True)
    rule_version = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="running")
    error = Column(Text, nullable=True)


class ConfigurationVersionModel(Base):
    __tablename__ = "configuration_versions"
    id = Column(String(36), primary_key=True, default=_new_uuid)
    component = Column(String(64), nullable=False)
    version = Column(String(64), nullable=False)
    content_hash = Column(String(64), nullable=True)
    previous_version = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now)


# ═══════════════════════════════════════════════════════════════════════════════
# Engine helpers
# ═══════════════════════════════════════════════════════════════════════════════

def create_cognition_engine(db_path: str = ":memory:", echo: bool = False) -> Engine:
    """Create SQLAlchemy engine and all tables."""
    engine = create_engine(f"sqlite:///{db_path}", echo=echo)
    Base.metadata.create_all(engine)
    return engine


def make_cognition_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine)


@contextmanager
def cognition_session_scope(factory: sessionmaker) -> Generator[Session, None, None]:
    """Context manager for a session with commit/rollback."""
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Compare-and-swap helpers
# ═══════════════════════════════════════════════════════════════════════════════

class StaleVersionError(Exception):
    """Raised when compare-and-swap finds an unexpected version."""
    pass


class RevisionImmutableError(Exception):
    """Raised when attempting to modify or delete an immutable revision row."""
    pass


def _reject_revision_update(mapper, connection, target):
    """SQLAlchemy before_update listener — rejects any revision row update."""
    raise RevisionImmutableError(
        f"Cannot update {target.__tablename__} row id={getattr(target, 'id', '?')}: "
        "revision rows are immutable"
    )


def _reject_revision_delete(mapper, connection, target):
    """SQLAlchemy before_delete listener — rejects any revision row deletion."""
    raise RevisionImmutableError(
        f"Cannot delete {target.__tablename__} row id={getattr(target, 'id', '?')}: "
        "revision rows are immutable"
    )


# Register immutable revision listeners on both revision models
event.listen(EventRevisionModel, "before_update", _reject_revision_update)
event.listen(EventRevisionModel, "before_delete", _reject_revision_delete)
event.listen(ThesisRevisionModel, "before_update", _reject_revision_update)
event.listen(ThesisRevisionModel, "before_delete", _reject_revision_delete)


def compare_and_swap_thesis(
    factory: sessionmaker,
    thesis_id: str,
    expected_version: int,
    updates: dict,
) -> int:
    """Atomic compare-and-swap for thesis current projection.

    Returns rowcount (1 = success, 0 = stale).
    Raises StaleVersionError when rowcount is 0.
    """
    from sqlalchemy import text
    session: Session = factory()
    try:
        result = session.execute(
            text(
                "UPDATE theses SET version = version + 1, updated_at = :now, "
                "summary = COALESCE(:summary, summary), "
                "lifecycle_state = COALESCE(:lifecycle_state, lifecycle_state), "
                "horizon = COALESCE(:horizon, horizon), "
                "portfolio_class = COALESCE(:portfolio_class, portfolio_class) "
                "WHERE id = :id AND version = :expected_version"
            ),
            {
                "id": thesis_id,
                "expected_version": expected_version,
                "now": _utc_now(),
                "summary": updates.get("summary"),
                "lifecycle_state": updates.get("lifecycle_state"),
                "horizon": updates.get("horizon"),
                "portfolio_class": updates.get("portfolio_class"),
            },
        )
        session.commit()
        if result.rowcount == 0:
            raise StaleVersionError(
                f"Thesis {thesis_id} version mismatch: expected {expected_version}"
            )
        return result.rowcount
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

