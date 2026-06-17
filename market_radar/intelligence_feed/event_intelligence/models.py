"""Event intelligence models — dedup, event, entity, scoring, timeline."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from market_radar.intelligence_feed.models import FeedItem


# ── Dedup ──────────────────────────────────────────────────────────────────────

class DuplicateType(str, Enum):
    EXACT = "exact"
    MIRRORED = "mirrored"
    UPDATED = "updated"
    RELATED = "related"
    UNKNOWN = "unknown"


@dataclass
class DuplicateInfo:
    duplicate_of: str                # feed_id of canonical item
    duplicate_reason: DuplicateType
    duplicate_confidence: float      # 0.0-1.0
    canonical_item_id: str          # matching field value
    source_copies: list[str] = field(default_factory=list)


@dataclass
class DuplicateResult:
    canonical_items: list[FeedItem] = field(default_factory=list)
    removed_count: int = 0
    duplicate_map: dict[str, DuplicateInfo] = field(default_factory=dict)


# ── Event ──────────────────────────────────────────────────────────────────────

class EventStatus(str, Enum):
    NEW = "new"
    DEVELOPING = "developing"
    CONFIRMED = "confirmed"
    UPDATED = "updated"
    CONFLICTING = "conflicting"
    STALE = "stale"
    SUPERSEDED = "superseded"


@dataclass
class Entity:
    name: str
    entity_type: str   # exchange/protocol/foundation/company/regulator/country/person
    confidence: float = 1.0


@dataclass
class Asset:
    symbol: str
    full_name: str
    confidence: float = 1.0


@dataclass
class Topic:
    topic: str         # listing/delisting/exploit/security/regulation/macro/...
    confidence: float = 1.0


@dataclass
class ExtractionResult:
    assets: list[Asset] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)


@dataclass
class TimelineEntry:
    timestamp: str               # UTC ISO
    item_id: str                 # feed_id
    source_label: str
    event_type: str              # first_report / update / conflict / resolution
    summary: str = ""
    previous_status: Optional[str] = None
    new_status: Optional[str] = None


@dataclass
class SourceIndependence:
    raw_source_count: int = 0
    independent_source_count: int = 0
    source_groups: list[SourceGroup] = field(default_factory=list)
    primary_source_candidates: list[str] = field(default_factory=list)
    mirrored_count: int = 0
    unknown_source_count: int = 0


@dataclass
class SourceGroup:
    group_label: str               # e.g. "coindesk_via_tg", "official"
    sources: list[str] = field(default_factory=list)
    is_independent: bool = True


@dataclass
class ScoreBreakdown:
    freshness: float = 0.0
    novelty: float = 0.0
    source_independence: float = 0.0
    asset_relevance: float = 0.0
    event_severity: float = 0.0
    evidence_completeness: float = 0.0
    conflict_penalty: float = 0.0
    duplication_penalty: float = 0.0
    stale_penalty: float = 0.0
    data_quality_penalty: float = 0.0

    @property
    def total(self) -> float:
        return max(0.0, min(100.0, sum([
            self.freshness, self.novelty, self.source_independence,
            self.asset_relevance, self.event_severity, self.evidence_completeness,
        ]) - self.conflict_penalty - self.duplication_penalty -
        self.stale_penalty - self.data_quality_penalty))


class CandidateLevel(str, Enum):
    WATCH = "watch"
    REVIEW = "review"
    HIGH_ATTENTION = "high_attention"


@dataclass
class SignalCandidate:
    event_id: str
    level: CandidateLevel
    score: float
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    top_assets: list[str] = field(default_factory=list)
    top_topics: list[str] = field(default_factory=list)
    canonical_title: str = ""
    summary: str = ""
    source_count: int = 0
    independent_count: int = 0


@dataclass
class IntelligenceEvent:
    event_id: str
    event_type: str
    canonical_title: str
    summary: str = ""
    started_at: Optional[str] = None
    latest_at: Optional[str] = None
    status: EventStatus = EventStatus.NEW
    entities: list[Entity] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)
    items: list[FeedItem] = field(default_factory=list)
    source_count: int = 0
    source_diversity: int = 0
    evidence_count: int = 0
    conflicting_claims: list[str] = field(default_factory=list)
    novelty: float = 0.0
    freshness: float = 0.0
    relevance: float = 0.0
    confidence: float = 0.0
    data_quality: float = 1.0
    provenance: str = "deterministic_rules"
    timeline: list[TimelineEntry] = field(default_factory=list)
    source_independence: SourceIndependence = field(default_factory=SourceIndependence)
    candidate: Optional[SignalCandidate] = None


@dataclass
class EventClusterConfig:
    # Time window for same-event clustering (hours)
    time_window_hours: float = 72.0
    # Min token overlap for title-based clustering
    min_title_overlap: float = 0.3
    # Max hours for re-emerged event detection
    re_emergence_hours: float = 168.0
    # Score weights
    freshness_weight: float = 20.0
    novelty_weight: float = 15.0
    source_independence_weight: float = 25.0
    asset_relevance_weight: float = 15.0
    event_severity_weight: float = 15.0
    evidence_weight: float = 10.0
    # Thresholds
    stale_hours: float = 48.0
    future_tolerance_seconds: float = 3600.0
    max_title_tokens: int = 20
