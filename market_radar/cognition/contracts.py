"""Cognition Spine V1 contracts."""

from __future__ import annotations
import hashlib, json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "cognition-v1"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_id(parts: List[str]) -> str:
    return hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()[:16]

class EventStatus(str, Enum):
    CANDIDATE = "candidate"; ACTIVE = "active"; CONFIRMED = "confirmed"
    CONTRADICTED = "contradicted"; INVALIDATED = "invalidated"
    EXPIRED = "expired"; RESOLVED = "resolved"

class ExpectationType(str, Enum):
    CONSENSUS_VALUE = "consensus_value"; PRIOR_OFFICIAL = "prior_official"
    SCHEDULED_EVENT = "scheduled_event"; MARKET_IMPLIED = "market_implied"
    UNAVAILABLE = "unavailable"

class Verdict(str, Enum):
    SUPPORTS = "supports"; CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"; UNAVAILABLE = "unavailable"

class TransmissionChannel(str, Enum):
    DIRECT_ASSET = "direct_asset"; SECTOR_SPILLOVER = "sector_spillover"
    RISK_ON_OFF = "risk_on_off"; REGULATORY_LIQUIDITY = "regulatory_liquidity"
    SECURITY_OPERATIONAL = "security_operational"
    NO_DEFENSIBLE_PATH = "no_defensible_path"

class AbstentionCode(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    EXPECTATION_UNAVAILABLE = "expectation_unavailable"
    MARKET_DATA_UNAVAILABLE = "market_data_unavailable"
    UNRESOLVED_SOURCE_CONFLICT = "unresolved_source_conflict"
    STALE_EVIDENCE = "stale_evidence"; FUTURE_LEAKAGE_RISK = "future_leakage_risk"
    AMBIGUOUS_GROUPING = "ambiguous_grouping"

class EvidenceType(str, Enum):
    LIVE = "live"; REPLAY = "replay"; FIXTURE = "fixture"; STATIC = "static"
class SourceOrigin(str, Enum):
    LIVE = "live"; REPLAY = "replay"; FIXTURE = "fixture"; DEGRADED = "degraded"
class GroupingMethod(str, Enum):
    EXACT_DEDUP_KEY = "exact_dedup_key"; FUZZY_ENTITY_TIME = "fuzzy_entity_time"
    KEPT_SEPARATE = "kept_separate"


@dataclass
class EventState:
    event_id: str = ""
    status: str = EventStatus.CANDIDATE.value
    revision: int = 1
    title: str = ""
    description: str = ""
    event_dedup_key: str = ""
    observation_ids: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    affected_assets: List[str] = field(default_factory=list)
    possible_related_event_ids: List[str] = field(default_factory=list)
    published_at: str = ""
    effective_at: str = ""
    first_source_at: str = ""
    first_observed_at: str = ""
    last_observed_at: str = ""
    state_updated_at: str = ""
    schema_version: str = SCHEMA_VERSION
    def to_dict(self) -> Dict[str, Any]: return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class EventRevision:
    revision_id: str = ""
    event_id: str = ""
    revision: int = 1
    previous_status: str = ""
    new_status: str = ""
    reason: str = ""
    observation_ids_added: List[str] = field(default_factory=list)
    timestamp: str = ""
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class SourceConflict:
    event_id: str = ""; observation_id_a: str = ""; observation_id_b: str = ""
    source_a: str = ""; source_b: str = ""; conflicting_field: str = ""
    value_a: str = ""; value_b: str = ""; resolved: bool = False
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class ExpectationState:
    event_id: str = ""
    expectation_type: str = ExpectationType.UNAVAILABLE.value
    expected_value: Optional[float] = None
    expected_range_low: Optional[float] = None
    expected_range_high: Optional[float] = None
    expected_category: str = ""
    actual_reported_value: Optional[float] = None
    actual_reported_category: str = ""
    signed_surprise: Optional[float] = None
    absolute_surprise: Optional[float] = None
    surprise_pct: Optional[float] = None
    baseline_source: str = ""; baseline_timestamp: str = ""
    stale: bool = False; confidence: str = "low"
    limitations: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class MarketSnapshot:
    snapshot_id: str = ""
    event_id: str = ""
    as_of: str = ""
    provider: str = ""
    asset: str = ""
    price: Optional[float] = None
    return_1h: Optional[float] = None
    return_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    btc_return_1h: Optional[float] = None
    pre_event_ref: Optional[float] = None
    reaction: Optional[float] = None
    follow_through: Optional[float] = None
    missing_metrics: List[str] = field(default_factory=list)
    evidence_path: str = ""
    evidence_sha256: str = ""
    rate_limited: bool = False
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class ConfirmationState:
    event_id: str = ""
    dimension: str = ""
    verdict: str = Verdict.UNAVAILABLE.value
    reason_code: str = ""
    measured_value: Optional[float] = None
    threshold: Optional[float] = None
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class TransmissionPath:
    path_id: str = ""
    event_id: str = ""
    channel: str = TransmissionChannel.NO_DEFENSIBLE_PATH.value
    source_event: str = ""
    affected_assets: List[str] = field(default_factory=list)
    mechanism: str = ""
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    confidence: str = "low"
    expiry: str = ""
    invalidation_conditions: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class Assessment:
    assessment_id: str = ""
    event_id: str = ""
    event_summary: str = ""
    lifecycle_state: str = EventStatus.CANDIDATE.value
    expectation_gap: Optional[float] = None
    market_confirmation: str = Verdict.UNAVAILABLE.value
    transmission_paths: List[str] = field(default_factory=list)
    confidence_components: Dict[str, float] = field(default_factory=dict)
    overall_confidence: float = 0.0
    supporting_evidence_ids: List[str] = field(default_factory=list)
    contradicting_evidence_ids: List[str] = field(default_factory=list)
    known_unknowns: List[str] = field(default_factory=list)
    expiry: str = ""
    invalidation_conditions: List[str] = field(default_factory=list)
    not_trading_instruction: bool = True
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class Abstention:
    event_id: str = ""
    code: str = AbstentionCode.INSUFFICIENT_EVIDENCE.value
    reason: str = ""
    missing_inputs: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class HistoricalCase:
    case_id: str = ""
    case_name: str = ""
    fixture_path: str = ""
    description: str = ""
    expected_outcome: str = ""
    expected_abstention: bool = False
    expected_invalidation: bool = False
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

@dataclass
class EvaluationResult:
    case_id: str = ""
    actual_assessment_id: str = ""
    actual_abstention: bool = False
    actual_lifecycle: str = ""
    actual_confidence: float = 0.0
    passed: bool = False
    errors: List[str] = field(default_factory=list)
    leakage_detected: bool = False
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)


@dataclass
class RunManifest:
    run_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = ""
    mode: str = ""
    stages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)
