"""WP-02 Historical data-factory contracts.

D03: Canonical data contracts for the finite, checkpointed historical
evidence and point-in-time data factory.

Every record has deterministic ID, schema version, rule/parser version,
created/retrieved time and source provenance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class SourceClass(str, Enum):
    """Classification of a candidate source."""
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    QUALIFYING_EVIDENCE = "QUALIFYING_EVIDENCE"
    MARKET_OUTCOME = "MARKET_OUTCOME"
    REJECTED = "REJECTED"


class QualificationState(str, Enum):
    """Final qualification state for an intake record."""
    QUALIFIED = "QUALIFIED"
    INCOMPLETE = "INCOMPLETE"
    DUPLICATE = "DUPLICATE"
    LEAKED = "LEAKED"
    UNAUTHORIZED_SOURCE = "UNAUTHORIZED_SOURCE"
    IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
    OUTCOME_UNAVAILABLE = "OUTCOME_UNAVAILABLE"
    QUARANTINED = "QUARANTINED"


class AcquisitionStatus(str, Enum):
    """Status of an acquisition run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"


class CorrectionType(str, Enum):
    """Type of relationship between two cases."""
    CORRECTION = "correction"
    RETRACTION = "retraction"
    CONTRADICTION = "contradiction"
    SUPERSESSION = "supersession"


class DuplicateType(str, Enum):
    """Type of duplication."""
    EXACT_DUPLICATE = "exact_duplicate"
    SAME_EVENT_IDENTITY = "same_event_identity"
    RELATED_DISTINCT = "related_distinct"


class SplitLabel(str, Enum):
    """Frozen split label."""
    BUILD = "BUILD"
    DEVELOPMENT = "DEVELOPMENT"
    BLIND = "BLIND"


# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stable_hash(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def _new_id() -> str:
    return _stable_hash({"t": _utc_now().isoformat()})


SCHEMA_VERSION = "1.0"


# ──────────────────────────────────────────────────────────────────────────────
# Source registry
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SourceRegistryEntry:
    """A single entry in the versioned source registry."""
    source_id: str
    name: str
    source_class: SourceClass
    authority: str
    fact_permission: str
    access_method: str
    base_url: str
    historical_coverage_start: Optional[datetime] = None
    historical_coverage_end: Optional[datetime] = None
    parser_version: str = "1.0"
    rate_limit_per_second: float = 1.0
    retry_limit: int = 3
    terms_note: str = ""
    short_excerpts_allowed: bool = True
    fallback_source_id: Optional[str] = None
    health_status: str = "unknown"
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)

    @property
    def id(self) -> str:
        return _stable_hash({"source_id": self.source_id, "v": self.schema_version})


# ──────────────────────────────────────────────────────────────────────────────
# Acquisition
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class AcquisitionRun:
    """A finite acquisition run configuration and result."""
    run_id: str
    source_id: str
    start_time: datetime
    end_time: datetime
    record_limit: int
    page_size: int = 50
    request_timeout_seconds: int = 30
    retry_limit: int = 3
    backoff_seconds: float = 1.0
    checkpoint_path: Optional[str] = None
    output_path: Optional[str] = None
    status: AcquisitionStatus = AcquisitionStatus.PENDING
    total_records: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    max_record_budget: int = 2000
    max_request_budget: int = 100
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    schema_version: str = SCHEMA_VERSION

    @property
    def deterministic_id(self) -> str:
        return _stable_hash({
            "source_id": self.source_id,
            "start": self.start_time.isoformat(),
            "end": self.end_time.isoformat(),
            "limit": self.record_limit,
            "v": self.schema_version,
        })

    def request_fingerprint(self) -> str:
        """Fingerprint for checkpoint resume validation."""
        return _stable_hash({
            "source_id": self.source_id,
            "start": self.start_time.isoformat(),
            "end": self.end_time.isoformat(),
            "limit": self.record_limit,
            "page_size": self.page_size,
            "v": self.schema_version,
        })


@dataclass
class AcquisitionCheckpoint:
    """Durable checkpoint for resumable acquisition."""
    run_id: str
    request_fingerprint: str
    completed_pages: List[int] = field(default_factory=list)
    last_page_token: Optional[str] = None
    total_records_so_far: int = 0
    total_requests_so_far: int = 0
    failed_requests_so_far: int = 0
    checkpointed_at: datetime = field(default_factory=_utc_now)
    schema_version: str = SCHEMA_VERSION

    def is_compatible(self, request: AcquisitionRun) -> bool:
        """Check if a new request can resume from this checkpoint."""
        return self.request_fingerprint == request.request_fingerprint()


@dataclass
class RawIntakeRecord:
    """Raw record from an acquisition adapter before normalization."""
    intake_id: str
    source_id: str
    source_url: str
    raw_body: str
    retrieved_at: datetime
    intake_status: str = "raw"
    parser_version: str = "1.0"
    error_message: Optional[str] = None
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)


# ──────────────────────────────────────────────────────────────────────────────
# Normalization and provenance
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class NormalizedEvidenceRecord:
    """Normalized evidence record with explicit point-in-time fields."""
    evidence_id: str
    source_id: str
    source_url: str
    authority: str
    fact_permission: str
    publication_time: Optional[datetime] = None
    effective_time: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    retrieval_time: Optional[datetime] = None
    assessment_time: Optional[datetime] = None
    normalized_fact: str = ""
    short_excerpt: str = ""
    content_hash: str = ""
    parser_version: str = "1.0"
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)

    @property
    def availability_time(self) -> Optional[datetime]:
        """Point-in-time rule: availability = max(first_seen_at, retrieval_time)."""
        if self.first_seen_at is not None and self.retrieval_time is not None:
            return max(self.first_seen_at, self.retrieval_time)
        return self.first_seen_at or self.retrieval_time

    def compute_content_hash(self) -> str:
        """Deterministic hash of stable content fields — excludes timestamps."""
        return _stable_hash({
            "source_id": self.source_id,
            "source_url": self.source_url,
            "normalized_fact": self.normalized_fact,
            "short_excerpt": self.short_excerpt,
            "parser_version": self.parser_version,
            "schema_version": self.schema_version,
        })


# ──────────────────────────────────────────────────────────────────────────────
# Event identity and correction chains
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EventIdentityAssignment:
    """Assignment of a case to a stable event identity."""
    case_id: str
    event_identity_id: str
    duplicate_type: Optional[DuplicateType] = None
    rule_version: str = "1.0"
    evidence_refs: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class CorrectionChainAssignment:
    """Assignment of a case to a correction/retraction/contradiction chain."""
    case_id: str
    correction_chain_id: str
    chain_root_case_id: Optional[str] = None
    correction_type: Optional[CorrectionType] = None
    target_case_id: Optional[str] = None
    rule_version: str = "1.0"
    evidence_refs: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)


# ──────────────────────────────────────────────────────────────────────────────
# Asset mapping and market regime
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class AssetMapping:
    """Mapping of a case to affected assets."""
    case_id: str
    primary_asset: str
    additional_assets: List[str] = field(default_factory=list)
    benchmark_asset: Optional[str] = None
    instrument_identifier: str = ""
    mapping_rule_version: str = "1.0"
    evidence_refs: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class MarketRegimeAssignment:
    """Assignment of a market regime label to a case."""
    case_id: str
    regime_label: str
    rule_version: str = "1.0"
    observation_refs: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)


# ──────────────────────────────────────────────────────────────────────────────
# Outcome observations
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class OutcomeObservation:
    """Separate outcome observation for one instrument and window."""
    outcome_id: str
    case_id: str
    provider: str
    instrument: str
    interval: str  # 1h, 6h, 24h, 3d, 7d
    open_time: datetime
    close_time: datetime
    retrieval_time: datetime
    open_price: Optional[float] = None
    close_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    volume: Optional[float] = None
    return_pct: Optional[float] = None
    direction: Optional[str] = None
    content_hash: str = ""
    missing_data_reason: Optional[str] = None
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)

    def compute_content_hash(self) -> str:
        """Deterministic hash of outcome data — excludes timestamps."""
        return _stable_hash({
            "provider": self.provider,
            "instrument": self.instrument,
            "interval": self.interval,
            "open_time": self.open_time.isoformat(),
            "close_time": self.close_time.isoformat(),
            "open_price": self.open_price,
            "close_price": self.close_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "volume": self.volume,
            "return_pct": self.return_pct,
            "direction": self.direction,
        })


# ──────────────────────────────────────────────────────────────────────────────
# Case qualification
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class CaseQualificationDecision:
    """Decision on whether an intake record becomes a qualified case."""
    case_id: str
    intake_id: str
    qualification: QualificationState
    event_family: str
    title: str
    event_time: Optional[datetime] = None
    split_label: Optional[SplitLabel] = None
    evidence_refs: List[str] = field(default_factory=list)
    identity_refs: List[str] = field(default_factory=list)
    correction_chain_refs: List[str] = field(default_factory=list)
    asset_refs: List[str] = field(default_factory=list)
    regime_refs: List[str] = field(default_factory=list)
    outcome_refs: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    rule_version: str = "1.0"
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)


# ──────────────────────────────────────────────────────────────────────────────
# Split allocation
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class FrozenSplitAssignment:
    """Assignment of a case to a frozen split."""
    case_id: str
    split_label: SplitLabel
    split_boundary_version: str
    allocation_rule_version: str = "1.0"
    chain_root_time: Optional[datetime] = None
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)


# ──────────────────────────────────────────────────────────────────────────────
# Corpus build manifest and quality
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class CorpusBuildManifest:
    """Build manifest for one corpus construction run."""
    build_id: str
    corpus_version: str = "1.0"
    build_date: datetime = field(default_factory=_utc_now)
    total_accepted_cases: int = 0
    total_intake_records: int = 0
    rejected_records: int = 0
    family_distribution: Dict[str, int] = field(default_factory=dict)
    regime_distribution: Dict[str, int] = field(default_factory=dict)
    split_distribution: Dict[str, int] = field(default_factory=dict)
    artifact_hashes: Dict[str, str] = field(default_factory=dict)
    root_hash: str = ""
    schema_version: str = SCHEMA_VERSION

    def compute_root_hash(self) -> str:
        """Deterministic root hash from all artifact hashes."""
        return _stable_hash({
            "corpus_version": self.corpus_version,
            "artifact_hashes": self.artifact_hashes,
            "schema_version": self.schema_version,
        })


@dataclass
class CorpusQualityReport:
    """Quality report for a corpus build."""
    build_id: str
    acceptable_cases_ge_1500: bool = False
    family_coverage_all_six: bool = False
    family_minimum_150: bool = False
    family_max_35_percent: bool = False
    regime_coverage_multiple: bool = False
    unknown_regime_max_10_percent: bool = False
    critical_time_completeness_100: bool = False
    authority_permission_completeness_100: bool = False
    future_leakage_violations: int = 0
    duplicate_accepted_case_ids: int = 0
    cross_split_event_identities: int = 0
    cross_split_correction_chains: int = 0
    blind_tuning_contamination: int = 0
    outcome_structural_violations: int = 0
    outcome_24h_coverage: float = 0.0
    deterministic_rebuild_match: bool = False
    audit_path_coverage: float = 0.0
    all_gates_pass: bool = False
    errors: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION


@dataclass
class RejectedRecord:
    """Record of a rejected intake record with reason."""
    intake_id: str
    case_id: Optional[str] = None
    rejection_reason: str = ""
    qualification: Optional[QualificationState] = None
    source_id: str = ""
    retrieved_at: Optional[datetime] = None
    schema_version: str = SCHEMA_VERSION
    created_at: datetime = field(default_factory=_utc_now)
