"""P02-P06: Multi-lane intake contracts for cognition spine V1.

Defines versioned typed contracts for six input lanes:
1. QuickFlashEventEnvelope  -- broad-recall cleaned event stream
2. DirectEvidenceBundle     -- purpose-built official evidence/fallback
3. MarketStateInput         -- price, volume, OI, funding, etc.
4. ExpectationBaselineInput -- consensus, prior, schedules, implied
5. ResearchClaimInput       -- papers, reports, public methods
6. HistoricalOutcomeInput   -- point-in-time outcome labels

Each contract preserves schema_version, stable ID, timestamps,
origin/source identity, authority class, fact permission,
refs/hashes, entities/assets, quality/confidence, and
live/replay/fixture/degraded designation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "intake-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LaneOrigin(str, Enum):
    LIVE = "live"
    REPLAY = "replay"
    FIXTURE = "fixture"
    DEGRADED = "degraded"


class AuthorityClass(str, Enum):
    PRIMARY_OFFICIAL = "primary_official"
    SECONDARY_OFFICIAL = "secondary_official"
    INDUSTRY_REPORT = "industry_report"
    ACADEMIC = "academic"
    NEWS_MEDIA = "news_media"
    SOCIAL_SENSOR = "social_sensor"
    DERIVED = "derived"
    UNKNOWN = "unknown"


class FactPermission(str, Enum):
    CONFIRMED = "confirmed"
    CORROBORATED = "corroborated"
    SINGLE_SOURCE = "single_source"
    ALLEGED = "alleged"
    UNCLEAR = "unclear"



@dataclass
class QuickFlashEventEnvelope:
    """Cleaned event from QuickFlash broad-recall system."""
    schema_version: str = SCHEMA_VERSION
    envelope_id: str = ''
    upstream_item_id: str = ''
    upstream_event_id: str = ''
    source_item_ids: List[str] = field(default_factory=list)
    source_identity: str = ''
    authority_class: str = AuthorityClass.UNKNOWN.value
    fact_permission: str = FactPermission.UNCLEAR.value
    published_at: str = ''
    first_seen_at: str = ''
    updated_at: str = ''
    cleaned_title: str = ''
    cleaned_summary: str = ''
    event_type: str = ''
    entities: List[str] = field(default_factory=list)
    assets: List[str] = field(default_factory=list)
    jurisdictions: List[str] = field(default_factory=list)
    original_url: str = ''
    evidence_refs: List[str] = field(default_factory=list)
    evidence_hashes: List[str] = field(default_factory=list)
    importance: float = 0.0
    urgency: float = 0.0
    novelty: float = 0.0
    duplicate_cluster_id: str = ''
    upstream_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    upstream_quality: str = 'unknown'
    upstream_confidence: float = 0.0
    filtering_metadata: Dict[str, Any] = field(default_factory=dict)
    rejection_reason: str = ''
    origin: str = LaneOrigin.FIXTURE.value
    retrieved_at: str = ''

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> QuickFlashEventEnvelope:
        return cls(**data)


@dataclass
class DirectEvidenceBundle:
    """Purpose-built official evidence bundle."""
    schema_version: str = SCHEMA_VERSION
    bundle_id: str = ''
    source_id: str = ''
    source_display_name: str = ''
    authority_class: str = AuthorityClass.PRIMARY_OFFICIAL.value
    fact_permission: str = FactPermission.CONFIRMED.value
    retrieved_at: str = ''
    published_at: str = ''
    effective_at: str = ''
    first_seen_at: str = ''
    title: str = ''
    description: str = ''
    raw_artifact_path: str = ''
    raw_artifact_sha256: str = ''
    content_type: str = ''
    body_text: str = ''
    verification_request_id: str = ''
    correction_detected: bool = False
    previous_version_id: str = ''
    fallback_used: bool = False
    fallback_source: str = ''
    origin: str = LaneOrigin.FIXTURE.value
    http_status: int = 0
    latency_ms: int = 0
    error_code: str = ''
    health_status: str = 'unknown'

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DirectEvidenceBundle:
        return cls(**data)


@dataclass
class MarketStateInput:
    """Point-in-time market data for an asset."""
    schema_version: str = SCHEMA_VERSION
    record_id: str = ''
    asset: str = ''
    as_of: str = ''
    provider: str = ''
    price: Optional[float] = None
    return_1h: Optional[float] = None
    return_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    relative_performance_btc: Optional[float] = None
    open_interest: Optional[float] = None
    funding_rate: Optional[float] = None
    basis: Optional[float] = None
    liquidation_pressure: Optional[float] = None
    order_book_depth: Optional[float] = None
    spread: Optional[float] = None
    whale_position_change: Optional[float] = None
    stablecoin_liquidity: Optional[float] = None
    exchange_netflow: Optional[float] = None
    defi_tvl: Optional[float] = None
    protocol_health: str = ''
    missing_metrics: List[str] = field(default_factory=list)
    rate_limited: bool = False
    evidence_path: str = ''
    evidence_sha256: str = ''
    origin: str = LaneOrigin.FIXTURE.value
    retrieved_at: str = ''

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MarketStateInput:
        return cls(**data)


@dataclass
class ExpectationBaselineInput:
    """Typed expectation record."""
    schema_version: str = SCHEMA_VERSION
    record_id: str = ''
    event_dedup_key: str = ''
    asset: str = ''
    expectation_type: str = 'unavailable'
    expected_value: Optional[float] = None
    expected_range_low: Optional[float] = None
    expected_range_high: Optional[float] = None
    expected_category: str = ''
    actual_value: Optional[float] = None
    actual_category: str = ''
    signed_surprise: Optional[float] = None
    absolute_surprise: Optional[float] = None
    surprise_pct: Optional[float] = None
    baseline_source: str = ''
    baseline_timestamp: str = ''
    revision: int = 1
    confidence: str = 'low'
    stale: bool = False
    implied_probability: Optional[float] = None
    prediction_market_price: Optional[float] = None
    unlock_amount: Optional[float] = None
    unlock_date: str = ''
    limitations: List[str] = field(default_factory=list)
    origin: str = LaneOrigin.FIXTURE.value
    retrieved_at: str = ''

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExpectationBaselineInput:
        return cls(**data)


@dataclass
class ResearchClaimInput:
    """Controlled research claim path."""
    schema_version: str = SCHEMA_VERSION
    claim_id: str = ''
    source_title: str = ''
    source_url: str = ''
    source_date: str = ''
    claim_type: str = 'fact'
    domain: str = ''
    variables: List[str] = field(default_factory=list)
    applicable_regime: str = ''
    claim_text: str = ''
    expected_direction: str = ''
    time_horizon: str = ''
    falsification_condition: str = ''
    knowledge_half_life_days: int = 365
    review_date: str = ''
    status: str = 'seed'
    evidence_refs: List[str] = field(default_factory=list)
    conflicting_claim_ids: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    validation_result: str = ''
    origin: str = LaneOrigin.FIXTURE.value
    retrieved_at: str = ''

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ResearchClaimInput:
        return cls(**data)


@dataclass
class HistoricalOutcomeInput:
    """Point-in-time outcome label for validation."""
    schema_version: str = SCHEMA_VERSION
    outcome_id: str = ''
    event_dedup_key: str = ''
    case_name: str = ''
    outcome_category: str = ''
    price_impact_pct: Optional[float] = None
    direction_accuracy: str = ''
    max_favorable_pct: Optional[float] = None
    max_adverse_pct: Optional[float] = None
    event_time: str = ''
    outcome_window_hours: int = 168
    evaluation_time: str = ''
    expected_abstention: bool = False
    expected_contradiction: bool = False
    expected_invalidation: bool = False
    expected_lifecycle: str = ''
    asset: str = ''
    strategy_id: str = ''
    notes: str = ''
    origin: str = LaneOrigin.FIXTURE.value

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HistoricalOutcomeInput:
        return cls(**data)