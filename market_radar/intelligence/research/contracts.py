"""
Typed Contracts — Research Intelligence Layer (Lane E)

These are the canonical typed data structures for the research cognition layer.
Every schema class provides deterministic ID generation and validation.
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional


def _deterministic_id(prefix: str, content: str) -> str:
    """Generate a deterministic ID from content."""
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16].upper()
    return f"{prefix}-{h}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# === Valid Status Values ===

VALID_CLAIM_STATUSES = [
    "observed", "supported", "contested", "contradicted",
    "insufficient_evidence", "stale", "superseded", "rejected",
]

VALID_EVIDENCE_ROLES = [
    "supporting", "opposing", "qualifying", "invalidating", "missing",
]

VALID_CONFLICT_TYPES = [
    "direction_conflict", "horizon_conflict", "regime_conflict",
    "transmission_conflict", "source_conflict", "revision_conflict",
    "validation_conflict", "calibration_conflict",
]

VALID_CANDIDATE_STATUSES = [
    "proposed", "evidence_compiled", "validation_pending",
    "historically_mixed", "historically_supported",
    "holdout_failed", "rejected", "archived",
]

VALID_QUESTION_STATUSES = [
    "open", "partially_answered", "blocked_by_data",
    "blocked_by_validation", "answered_with_limits", "archived",
]

FORBIDDEN_STATUSES = ["proven", "guaranteed", "certain", "profitable"]


@dataclass
class ResearchClaimV1:
    subject: str
    predicate: str
    object: str
    claim_type: str
    claim_status: str
    claim_scope: str = "historical_only"
    maturity: int = 0

    asset: Optional[str] = None
    sector: Optional[str] = None
    event_family: Optional[str] = None
    strategy_id: Optional[str] = None
    time_horizon: Optional[str] = None
    regime: Optional[str] = None

    valid_from_utc: Optional[str] = None
    valid_to_utc: Optional[str] = None
    information_cutoff_utc: Optional[str] = None

    supporting_evidence_edge_ids: list = field(default_factory=list)
    opposing_evidence_edge_ids: list = field(default_factory=list)
    conflict_set_ids: list = field(default_factory=list)
    source_lane_refs: list = field(default_factory=list)

    point_in_time_quality: str = "unknown"
    validation_status: str = "unvalidated"
    calibration_status: str = "unavailable"

    limitations: list = field(default_factory=list)
    supersedes_claim_id: Optional[str] = None
    claim_id: Optional[str] = None
    claim_key: Optional[str] = None
    generated_at_utc: Optional[str] = None

    def __post_init__(self):
        if self.claim_status in FORBIDDEN_STATUSES:
            raise ValueError(f"Forbidden claim status: {self.claim_status}")
        if self.claim_status not in VALID_CLAIM_STATUSES:
            raise ValueError(f"Invalid claim status: {self.claim_status}")
        if self.claim_id is None:
            self.claim_key = self._build_key()
            self.claim_id = _deterministic_id("RC", self.claim_key)
        if self.generated_at_utc is None:
            self.generated_at_utc = _utc_now()

    def _build_key(self) -> str:
        parts = [
            self.subject,
            self.predicate,
            self.object,
            self.asset or "",
            self.event_family or "",
            self.time_horizon or "",
            self.regime or "",
            self.claim_scope,
        ]
        return "::".join(parts)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class EvidenceEdgeV1:
    claim_id: str
    evidence_role: str
    source_lane: str
    source_artifact_path: str
    source_record_id: str
    observed_at_utc: str
    available_at_utc: str

    source_sha256: Optional[str] = None
    producer_sha: Optional[str] = None
    evidence_type: Optional[str] = None
    independence_group: Optional[str] = None
    origin_group: Optional[str] = None
    information_cutoff_utc: Optional[str] = None

    point_in_time_quality: str = "unknown"
    data_quality: str = "verified"
    validation_status: str = "unvalidated"

    supports: bool = False
    contradicts: bool = False
    qualifies: bool = False
    limits: bool = False

    notes: Optional[str] = None
    evidence_edge_id: Optional[str] = None

    def __post_init__(self):
        if self.evidence_role not in VALID_EVIDENCE_ROLES:
            raise ValueError(f"Invalid evidence role: {self.evidence_role}")
        if self.evidence_edge_id is None:
            content = f"{self.claim_id}::{self.source_lane}::{self.source_record_id}::{self.evidence_role}"
            self.evidence_edge_id = _deterministic_id("EE", content)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class ConflictSetV1:
    conflict_key: str
    conflict_type: str
    claim_ids: list
    conflict_status: str = "open"

    evidence_edge_ids: list = field(default_factory=list)
    asset: Optional[str] = None
    event_family: Optional[str] = None
    time_horizon: Optional[str] = None
    regime: Optional[str] = None
    valid_time_range: Optional[dict] = None

    resolution_status: str = "unresolved"
    resolution_rule: Optional[str] = None
    required_new_evidence: list = field(default_factory=list)

    created_at_utc: Optional[str] = None
    updated_at_utc: Optional[str] = None
    conflict_set_id: Optional[str] = None

    def __post_init__(self):
        if self.conflict_type not in VALID_CONFLICT_TYPES:
            raise ValueError(f"Invalid conflict type: {self.conflict_type}")
        if self.conflict_set_id is None:
            content = f"{self.conflict_key}::{self.conflict_type}::{'::'.join(sorted(self.claim_ids))}"
            self.conflict_set_id = _deterministic_id("CS", content)
        if self.created_at_utc is None:
            self.created_at_utc = _utc_now()
        if self.updated_at_utc is None:
            self.updated_at_utc = self.created_at_utc

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResearchQuestionV1:
    question_key: str
    question_text: str
    status: str = "open"

    linked_claim_ids: list = field(default_factory=list)
    linked_conflict_set_ids: list = field(default_factory=list)
    linked_candidate_ids: list = field(default_factory=list)

    missing_evidence: list = field(default_factory=list)
    required_data: list = field(default_factory=list)
    required_validation: list = field(default_factory=list)
    required_time_range: Optional[dict] = None

    priority: int = 3
    owner_module: Optional[str] = None

    created_at_utc: Optional[str] = None
    updated_at_utc: Optional[str] = None
    question_id: Optional[str] = None

    def __post_init__(self):
        if self.status not in VALID_QUESTION_STATUSES:
            raise ValueError(f"Invalid question status: {self.status}")
        if self.question_id is None:
            self.question_id = _deterministic_id("RQ", self.question_key)
        if self.created_at_utc is None:
            self.created_at_utc = _utc_now()
        if self.updated_at_utc is None:
            self.updated_at_utc = self.created_at_utc

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CandidateRecordV1:
    candidate_type: str
    candidate_name: str
    candidate_status: str = "proposed"

    source_claim_ids: list = field(default_factory=list)
    source_conflict_ids: list = field(default_factory=list)
    source_validation_ids: list = field(default_factory=list)
    source_failed_experiment_ids: list = field(default_factory=list)

    strategy_family: Optional[str] = None
    asset_scope: list = field(default_factory=list)
    event_family_scope: list = field(default_factory=list)
    horizon_scope: list = field(default_factory=list)
    regime_scope: list = field(default_factory=list)

    maturity: int = 0
    historical_support: Optional[str] = None
    holdout_status: str = "not_tested"
    calibration_status: str = "unavailable"
    live_shadow_status: str = "not_deployed"

    required_followup: list = field(default_factory=list)
    rejection_reasons: list = field(default_factory=list)
    limitations: list = field(default_factory=list)

    created_at_utc: Optional[str] = None
    updated_at_utc: Optional[str] = None
    candidate_id: Optional[str] = None

    def __post_init__(self):
        if self.candidate_status not in VALID_CANDIDATE_STATUSES:
            raise ValueError(f"Invalid candidate status: {self.candidate_status}")
        if self.candidate_id is None:
            content = f"{self.candidate_type}::{self.candidate_name}::{self.candidate_status}"
            self.candidate_id = _deterministic_id("CD", content)
        if self.created_at_utc is None:
            self.created_at_utc = _utc_now()
        if self.updated_at_utc is None:
            self.updated_at_utc = self.created_at_utc

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DecisionRecordV1:
    decision_type: str
    subject_id: str
    previous_state: str
    new_state: str
    made_by: str = "deterministic_rule"

    evidence_edge_ids: list = field(default_factory=list)
    validation_result_ids: list = field(default_factory=list)
    conflict_set_ids: list = field(default_factory=list)
    failed_experiment_ids: list = field(default_factory=list)

    rule_id: Optional[str] = None
    limitations: list = field(default_factory=list)
    reversible: bool = True

    made_at_utc: Optional[str] = None
    decision_id: Optional[str] = None

    def __post_init__(self):
        if self.decision_id is None:
            content = f"{self.decision_type}::{self.subject_id}::{self.previous_state}->{self.new_state}"
            self.decision_id = _deterministic_id("DC", content)
        if self.made_at_utc is None:
            self.made_at_utc = _utc_now()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ResearchDossierV1:
    subject_type: str
    subject_id: str
    candidate_status: str

    current_claims: list = field(default_factory=list)
    contested_claims: list = field(default_factory=list)
    contradicted_claims: list = field(default_factory=list)
    open_questions: list = field(default_factory=list)
    conflict_sets: list = field(default_factory=list)

    supporting_evidence: list = field(default_factory=list)
    opposing_evidence: list = field(default_factory=list)

    validation_summary: Optional[str] = None
    calibration_summary: Optional[str] = None

    failed_experiments: list = field(default_factory=list)
    limitations: list = field(default_factory=list)
    next_required_evidence: list = field(default_factory=list)
    producer_locks: Optional[dict] = None

    generated_at_utc: Optional[str] = None
    dossier_id: Optional[str] = None

    def __post_init__(self):
        if self.dossier_id is None:
            content = f"{self.subject_type}::{self.subject_id}"
            self.dossier_id = _deterministic_id("RD", content)
        if self.generated_at_utc is None:
            self.generated_at_utc = _utc_now()

    def to_dict(self) -> dict:
        return asdict(self)
