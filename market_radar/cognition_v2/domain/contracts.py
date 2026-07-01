"""Cognition v2 domain contracts — validated Pydantic models.

Dependency direction: domain imports nothing from application, persistence,
or operator packages. Only Pydantic and standard library.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════════

class ClaimClass(str, Enum):
    FACT = "fact"
    EVENT_STATE = "event_state"
    MECHANISM = "mechanism"
    EXPOSURE = "exposure"
    DIRECTION = "direction"
    PRICED_IN = "priced_in"
    ATTENTION_ACTION = "attention_action"


class EvidenceStatus(str, Enum):
    BLOCKED = "blocked"
    INSUFFICIENT = "insufficient"
    TENTATIVE = "tentative"
    SUPPORTED = "supported"
    STRONG = "strong"


class Horizon(str, Enum):
    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class ThesisState(str, Enum):
    DISCOVERED = "DISCOVERED"
    QUALIFYING = "QUALIFYING"
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    DORMANT = "DORMANT"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"
    ARCHIVED = "ARCHIVED"
    REOPEN_REVIEW = "REOPEN_REVIEW"
    REJECTED = "REJECTED"
    ISOLATED = "ISOLATED"


class ActionType(str, Enum):
    LOG = "log"
    FLAG = "flag"
    REVIEW = "review"
    ESCALATE = "escalate"
    SILENCE = "silence"


class RevisionOutcome(str, Enum):
    UNCHANGED = "unchanged"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    CONTESTED = "contested"
    INVALIDATED_REVISION = "invalidated"
    EXPIRED_REVISION = "expired"
    ARCHIVED_REVISION = "archived"
    REOPENED = "reopened"


class SourceAuthority(str, Enum):
    OFFICIAL = "official"
    OFFICIAL_DELEGATED = "official_delegated"
    VERIFIED_THIRD_PARTY = "verified_third_party"
    UNVERIFIED = "unverified"
    UNKNOWN = "unknown"


class FactPermission(str, Enum):
    SELF = "self"
    OFFICIAL_ACTION = "official_action"
    OWN_INTERNAL = "own_internal"
    DIRECT_OBSERVATION = "direct_observation"
    PUBLIC_DECLARATION = "public_declaration"
    CITED_THIRD_PARTY = "cited_third_party"
    NONE = "none"


class SourceHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class SplitLabel(str, Enum):
    BUILD = "BUILD"
    DEVELOPMENT = "DEVELOPMENT"
    BLIND = "BLIND"


class EventFamily(str, Enum):
    REGULATORY = "regulatory"
    CORPORATE = "corporate"
    MACRO = "macro"
    TECHNOLOGY = "technology"
    MARKET = "market"
    SECURITY = "security"


class MarketRegime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"


class CorrectionType(str, Enum):
    CORRECTION = "correction"
    RETRACTION = "retraction"
    CONTRADICTION = "contradiction"
    UPDATE = "update"


# ═══════════════════════════════════════════════════════════════════════════════
# Helper validators
# ═══════════════════════════════════════════════════════════════════════════════

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid4())


# ═══════════════════════════════════════════════════════════════════════════════
# Source Identity
# ═══════════════════════════════════════════════════════════════════════════════

class SourceIdentity(BaseModel):
    """Identity of an information source with permission and authority."""
    id: str = Field(default_factory=_new_id, description="Unique source ID")
    name: str = Field(..., min_length=1, description="Source display name")
    source_type: str = Field(..., description="e.g. api, feed, direct, research")
    authority: SourceAuthority = Field(default=SourceAuthority.UNKNOWN)
    fact_permission: FactPermission = Field(default=FactPermission.NONE)
    base_url: Optional[str] = Field(default=None)
    fingerprint_hash: Optional[str] = Field(default=None)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Source name must not be empty or whitespace-only")
        return v.strip()


class SourcePermission(BaseModel):
    """What a source is permitted to establish as fact."""
    source_id: str = Field(..., min_length=1)
    claim_classes: Set[ClaimClass] = Field(default_factory=set)
    horizon_limit: Optional[Horizon] = Field(default=None)
    requires_corroboration: bool = Field(default=False)
    max_evidence_age_seconds: Optional[int] = Field(default=None)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


# ═══════════════════════════════════════════════════════════════════════════════
# Evidence
# ═══════════════════════════════════════════════════════════════════════════════

class EvidenceRef(BaseModel):
    """A single evidence reference — minimal required fields."""
    source: str = Field(..., min_length=1)
    content_hash: str = Field(..., min_length=1)
    retrieved_at: datetime


class EvidenceRecord(BaseModel):
    """A piece of evidence with full provenance."""
    id: str = Field(default_factory=_new_id)
    source_id: str = Field(..., min_length=1)
    source_name: str = Field(..., min_length=1)
    content_hash: str = Field(..., min_length=1)
    body_text: Optional[str] = Field(default=None)
    publication_time: Optional[datetime] = Field(default=None)
    effective_time: Optional[datetime] = Field(default=None)
    first_seen_at: datetime = Field(default_factory=_utc_now)
    retrieval_time: datetime = Field(default_factory=_utc_now)
    assessment_time: Optional[datetime] = Field(default=None)
    fact_permission: FactPermission = Field(default=FactPermission.NONE)
    authority: SourceAuthority = Field(default=SourceAuthority.UNKNOWN)
    version: int = Field(default=1, ge=1)
    is_correction: bool = Field(default=False)
    corrects_evidence_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("content_hash")
    @classmethod
    def hash_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content_hash must not be empty")
        return v


# ═══════════════════════════════════════════════════════════════════════════════
# Event
# ═══════════════════════════════════════════════════════════════════════════════

class EventRecord(BaseModel):
    """A market event resolved from one or more evidence items."""
    id: str = Field(default_factory=_new_id)
    event_family: EventFamily = Field(...)
    title: str = Field(..., min_length=1)
    description: Optional[str] = Field(default=None)
    event_time: Optional[datetime] = Field(default=None)
    first_seen_at: datetime = Field(default_factory=_utc_now)
    source_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    lifecycle_state: ThesisState = Field(default=ThesisState.DISCOVERED)
    is_resolved: bool = Field(default=False)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Event title must not be empty")
        return v.strip()


class EventRevision(BaseModel):
    """Immutable event revision."""
    id: str = Field(default_factory=_new_id)
    event_id: str = Field(..., min_length=1)
    version: int = Field(..., ge=1)
    previous_version: Optional[int] = Field(default=None)
    revision_body: str = Field(..., min_length=1)
    revision_outcome: RevisionOutcome = Field(...)
    reason: str = Field(..., min_length=1)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def check_version_sequence(self) -> "EventRevision":
        if self.previous_version is not None and self.previous_version >= self.version:
            raise ValueError(f"previous_version {self.previous_version} must be < version {self.version}")
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Claims, Theses
# ═══════════════════════════════════════════════════════════════════════════════

class ClaimRecord(BaseModel):
    """A typed claim with bounded scope and evidence status."""
    id: str = Field(default_factory=_new_id)
    claim_class: ClaimClass = Field(...)
    summary: str = Field(..., min_length=1)
    evidence_status: EvidenceStatus = Field(...)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    counter_evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    horizon: Optional[Horizon] = Field(default=None)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utc_now)

    # No numeric confidence field
    # No trade/wallet/publish field

    @model_validator(mode="after")
    def check_evidence_refs(self) -> "ClaimRecord":
        if self.evidence_status in (EvidenceStatus.SUPPORTED, EvidenceStatus.STRONG):
            if not self.evidence_refs:
                raise ValueError(f"{self.evidence_status.value} claims require evidence references")
        if self.evidence_status == EvidenceStatus.BLOCKED:
            if not self.evidence_refs:
                pass  # BLOCKED may have empty refs with reason
        return self

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Claim summary must not be empty")
        return v.strip()


class ThesisRecord(BaseModel):
    """A thesis — the core cognitive unit."""
    id: str = Field(default_factory=_new_id)
    claim_class: ClaimClass = Field(...)
    summary: str = Field(..., min_length=1)
    lifecycle_state: ThesisState = Field(default=ThesisState.DISCOVERED)
    version: int = Field(default=1, ge=1)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    horizon: Optional[Horizon] = Field(default=None)
    event_ids: List[str] = Field(default_factory=list)
    portfolio_class: Optional[str] = Field(default=None)  # thesis | risk_observation | mechanism_candidate
    review_by: Optional[datetime] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Thesis summary must not be empty")
        return v.strip()


class ThesisRevision(BaseModel):
    """Immutable thesis revision."""
    id: str = Field(default_factory=_new_id)
    thesis_id: str = Field(..., min_length=1)
    version: int = Field(..., ge=1)
    previous_version: Optional[int] = Field(default=None)
    revision_body: str = Field(..., min_length=1)
    revision_outcome: RevisionOutcome = Field(...)
    lifecycle_state: ThesisState = Field(...)
    reason: str = Field(..., min_length=1)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    claim_refs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utc_now)

    @model_validator(mode="after")
    def check_version_sequence(self) -> "ThesisRevision":
        if self.previous_version is not None and self.previous_version >= self.version:
            raise ValueError(f"previous_version {self.previous_version} must be < version {self.version}")
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# Exposure and CounterEvidence
# ═══════════════════════════════════════════════════════════════════════════════

class ExposureLink(BaseModel):
    """Links a thesis to an asset, sector, or structure."""
    id: str = Field(default_factory=_new_id)
    thesis_id: str = Field(..., min_length=1)
    asset_identifier: str = Field(..., min_length=1)
    asset_type: str = Field(default="crypto_asset")  # crypto_asset | sector | structure
    direction: Optional[str] = Field(default=None)  # positive | negative | mixed | unclear
    strength: Optional[str] = Field(default=None)  # primary | secondary | speculative
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utc_now)


class CounterEvidence(BaseModel):
    """Evidence that challenges a thesis claim."""
    id: str = Field(default_factory=_new_id)
    thesis_id: str = Field(..., min_length=1)
    claim_class: ClaimClass = Field(...)
    evidence_refs: List[EvidenceRef] = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    alternative_explanation: Optional[str] = Field(default=None)
    source_id: str = Field(..., min_length=1)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utc_now)


# ═══════════════════════════════════════════════════════════════════════════════
# Review and Attention
# ═══════════════════════════════════════════════════════════════════════════════

class ReviewIntent(BaseModel):
    """A scheduled or triggered review of a thesis."""
    id: str = Field(default_factory=_new_id)
    thesis_id: str = Field(..., min_length=1)
    idempotency_key: str = Field(..., min_length=1)
    due_at: datetime = Field(...)
    status: str = Field(default="PENDING")  # PENDING | CLAIMED | RUNNING | CANCELLED | FAILED
    checkpoint_step: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    last_error: Optional[str] = Field(default=None)
    trigger_reason: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)


class AttentionAllocation(BaseModel):
    """Records bounded machine attention allocation."""
    id: str = Field(default_factory=_new_id)
    thesis_id: str = Field(..., min_length=1)
    allocated_at: datetime = Field(default_factory=_utc_now)
    priority: int = Field(default=0)
    reason: str = Field(..., min_length=1)
    expires_at: Optional[datetime] = Field(default=None)
    source: str = Field(default="scheduler")


class NotificationDecision(BaseModel):
    """A decision to notify or remain silent."""
    id: str = Field(default_factory=_new_id)
    thesis_id: str = Field(..., min_length=1)
    action_type: ActionType = Field(...)
    reason: str = Field(..., min_length=1)
    notification_body: Optional[str] = Field(default=None)
    is_material: bool = Field(default=False)
    decided_at: datetime = Field(default_factory=_utc_now)
    version: int = Field(default=1, ge=1)

    # No trade/wallet/publish fields


# ═══════════════════════════════════════════════════════════════════════════════
# Provenance
# ═══════════════════════════════════════════════════════════════════════════════

class ProvenanceEdge(BaseModel):
    """Directed relationship with time and reason."""
    id: str = Field(default_factory=_new_id)
    source_id: str = Field(..., min_length=1)
    target_id: str = Field(..., min_length=1)
    relationship_type: str = Field(..., description="e.g. derived_from, corrects, contradicts, supports")
    reason: str = Field(default="")
    created_at: datetime = Field(default_factory=_utc_now)
    version: int = Field(default=1, ge=1)


# ═══════════════════════════════════════════════════════════════════════════════
# Historical replay
# ═══════════════════════════════════════════════════════════════════════════════

class OutcomeWindow(BaseModel):
    """Market outcome at a specific window from event time."""
    window_label: str = Field(..., pattern=r"^\d+[mhd]$")  # e.g. 1h, 6h, 24h, 3d, 7d
    event_id: str = Field(..., min_length=1)
    open_time: datetime = Field(...)
    close_time: datetime = Field(...)
    open_price: Optional[float] = Field(default=None)
    close_price: Optional[float] = Field(default=None)
    high_price: Optional[float] = Field(default=None)
    low_price: Optional[float] = Field(default=None)
    volume: Optional[float] = Field(default=None)
    return_pct: Optional[float] = Field(default=None)
    direction: Optional[str] = Field(default=None)  # up | down | flat | unknown
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utc_now)


class HistoricalCaseManifest(BaseModel):
    """Deterministic record of a historical replay case."""
    id: str = Field(default_factory=_new_id)
    case_id: str = Field(..., min_length=1)
    event_family: EventFamily = Field(...)
    market_regime: MarketRegime = Field(default=MarketRegime.UNKNOWN)
    split_label: SplitLabel = Field(...)
    title: str = Field(..., min_length=1)
    description: Optional[str] = Field(default=None)
    event_time: Optional[datetime] = Field(default=None)
    evidence_manifest_hash: str = Field(..., min_length=1)
    outcome_windows: List[OutcomeWindow] = Field(default_factory=list)
    correction_relations: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("case_id")
    @classmethod
    def case_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("case_id must not be empty")
        return v

    def deterministic_hash(self) -> str:
        """Produce deterministic hash from stable fields."""
        content = json.dumps({
            "case_id": self.case_id,
            "event_family": self.event_family.value,
            "market_regime": self.market_regime.value,
            "split_label": self.split_label.value,
            "title": self.title,
            "event_time": self.event_time.isoformat() if self.event_time else None,
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# Version and configuration records
# ═══════════════════════════════════════════════════════════════════════════════

class RunRecord(BaseModel):
    """Record of a cognition run."""
    id: str = Field(default_factory=_new_id)
    run_type: str = Field(default="inference")
    started_at: datetime = Field(default_factory=_utc_now)
    completed_at: Optional[datetime] = Field(default=None)
    configuration_version: str = Field(default="1.0")
    schema_version: str = Field(default="1.0")
    model_version: Optional[str] = Field(default=None)
    rule_version: Optional[str] = Field(default=None)
    status: str = Field(default="running")
    error: Optional[str] = Field(default=None)


class ConfigurationVersion(BaseModel):
    """Tracks schema, model, rule, and prompt versions."""
    id: str = Field(default_factory=_new_id)
    component: str = Field(..., description="schema|model|rule|prompt")
    version: str = Field(..., min_length=1)
    content_hash: Optional[str] = Field(default=None)
    previous_version: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=_utc_now)


# ═══════════════════════════════════════════════════════════════════════════════
# Abstention reasons
# ═══════════════════════════════════════════════════════════════════════════════

class AbstentionReason(BaseModel):
    """Structured reason for abstaining from a claim."""
    claim_class: ClaimClass = Field(...)
    reason_type: str = Field(...)  # e.g. missing_evidence, unresolved_identity, etc.
    description: str = Field(..., min_length=1)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Future-evidence leakage blocker
# ═══════════════════════════════════════════════════════════════════════════════

class FutureEvidenceBlocker(BaseModel):
    """Validates that no evidence from after a cutoff leaks into a time window."""
    cutoff_time: datetime = Field(...)
    max_allowed_time: datetime = Field(...)

    def is_leaked(self, evidence_time: datetime) -> bool:
        return evidence_time > self.max_allowed_time

    def filter_evidence(self, evidence_times: List[datetime]) -> List[datetime]:
        return [t for t in evidence_times if t <= self.max_allowed_time]


# ═══════════════════════════════════════════════════════════════════════════════
# Lifecycle transition request
# ═══════════════════════════════════════════════════════════════════════════════

class LifecycleTransitionRequest(BaseModel):
    """Request to transition a thesis to a new state."""
    thesis_id: str = Field(..., min_length=1)
    from_state: ThesisState = Field(...)
    to_state: ThesisState = Field(...)
    expected_version: int = Field(..., ge=1)
    reason: str = Field(..., min_length=1)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    rule_refs: List[str] = Field(default_factory=list)
    idempotency_key: str = Field(..., min_length=1)


# ═══════════════════════════════════════════════════════════════════════════════
# Canonical edges — lifecycle graph
# ═══════════════════════════════════════════════════════════════════════════════

CANONICAL_STATES: List[ThesisState] = [
    ThesisState.DISCOVERED, ThesisState.QUALIFYING, ThesisState.CANDIDATE,
    ThesisState.ACTIVE, ThesisState.DORMANT, ThesisState.INVALIDATED,
    ThesisState.EXPIRED, ThesisState.ARCHIVED, ThesisState.REOPEN_REVIEW,
    ThesisState.REJECTED, ThesisState.ISOLATED,
]

CANONICAL_EDGES: Dict[ThesisState, Set[ThesisState]] = {
    ThesisState.DISCOVERED: {ThesisState.QUALIFYING, ThesisState.REJECTED, ThesisState.ISOLATED},
    ThesisState.QUALIFYING: {ThesisState.CANDIDATE, ThesisState.REJECTED, ThesisState.ISOLATED, ThesisState.EXPIRED},
    ThesisState.CANDIDATE: {ThesisState.ACTIVE, ThesisState.DORMANT, ThesisState.REJECTED, ThesisState.EXPIRED, ThesisState.ISOLATED},
    ThesisState.ACTIVE: {ThesisState.ACTIVE, ThesisState.DORMANT, ThesisState.INVALIDATED, ThesisState.EXPIRED, ThesisState.ARCHIVED},
    ThesisState.DORMANT: {ThesisState.ACTIVE, ThesisState.INVALIDATED, ThesisState.EXPIRED, ThesisState.ARCHIVED},
    ThesisState.INVALIDATED: {ThesisState.ARCHIVED, ThesisState.REOPEN_REVIEW},
    ThesisState.EXPIRED: {ThesisState.ARCHIVED, ThesisState.REOPEN_REVIEW},
    ThesisState.ARCHIVED: {ThesisState.REOPEN_REVIEW},
    ThesisState.REOPEN_REVIEW: {ThesisState.ACTIVE, ThesisState.CANDIDATE, ThesisState.ARCHIVED, ThesisState.REJECTED, ThesisState.ISOLATED},
    ThesisState.REJECTED: {ThesisState.REOPEN_REVIEW},
    ThesisState.ISOLATED: {ThesisState.QUALIFYING, ThesisState.REJECTED},
}
