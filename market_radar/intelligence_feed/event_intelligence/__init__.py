"""Event Intelligence — cross-source deterministic event clustering and Signal Candidates.

FeedItem → dedup → event clustering → source independence → timeline → Signal Candidate.

All deterministic — no LLM, no vectors, no paid APIs.
"""
from .models import (
    DuplicateInfo, DuplicateType, DuplicateResult,
    IntelligenceEvent, EventStatus, EventClusterConfig,
    Entity, Asset, Topic, ExtractionResult,
    SourceIndependence, SourceGroup,
    SignalCandidate, CandidateLevel, ScoreBreakdown,
    TimelineEntry,
)
from .dedup import DedupEngine
from .extraction import ExtractionEngine, ASSET_MAP
from .clustering import ClusteringEngine
from .scoring import ScoringEngine
from .timeline import TimelineBuilder
from .orchestrator import EventIntelligenceOrchestrator, EventIntelligenceResult

__all__ = [
    "DuplicateInfo", "DuplicateType", "DuplicateResult",
    "IntelligenceEvent", "EventStatus", "EventClusterConfig",
    "Entity", "Asset", "Topic", "ExtractionResult",
    "SourceIndependence", "SourceGroup",
    "SignalCandidate", "CandidateLevel", "ScoreBreakdown",
    "TimelineEntry",
    "DedupEngine",
    "ExtractionEngine", "ASSET_MAP",
    "ClusteringEngine",
    "ScoringEngine",
    "TimelineBuilder",
    "EventIntelligenceOrchestrator", "EventIntelligenceResult",
]
