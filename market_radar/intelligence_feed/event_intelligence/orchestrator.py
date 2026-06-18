"""EventIntelligenceOrchestrator — full pipeline entry point.

FeedItem → Dedup → Cluster → Score → Timeline → SignalCandidates
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from market_radar.intelligence_feed.models import FeedItem, FeedDataMode
from .models import (
    DuplicateResult, IntelligenceEvent, EventClusterConfig,
    SignalCandidate, CandidateLevel, ScoreBreakdown,
)
from .dedup import DedupEngine
from .extraction import ExtractionEngine
from .clustering import ClusteringEngine
from .scoring import ScoringEngine
from .timeline import TimelineBuilder


@dataclass
class EventIntelligenceResult:
    pipeline_status: str = "ok"
    input_count: int = 0
    removed_as_duplicate: int = 0
    event_count: int = 0
    events: list[IntelligenceEvent] = field(default_factory=list)
    candidates: list[SignalCandidate] = field(default_factory=list)
    dedup_result: Optional[DuplicateResult] = None
    processing_ms: float = 0.0
    errors: list[str] = field(default_factory=list)


_NOW_MS: Optional[float] = None


def _now_ms() -> float:
    return datetime.now(timezone.utc).timestamp() * 1000


class EventIntelligenceOrchestrator:
    """Full pipeline: dedup → extract → cluster → score → report.

    Args:
        dedup_engine: DedupEngine instance.
        extractor: ExtractionEngine instance.
        clusterer: ClusteringEngine instance.
        scorer: ScoringEngine instance.
        config: EventClusterConfig instance.
    """

    def __init__(
        self,
        dedup_engine: Optional[DedupEngine] = None,
        extractor: Optional[ExtractionEngine] = None,
        clusterer: Optional[ClusteringEngine] = None,
        scorer: Optional[ScoringEngine] = None,
        config: Optional[EventClusterConfig] = None,
    ):
        self._dedup = dedup_engine or DedupEngine()
        self._extractor = extractor or ExtractionEngine()
        self._clusterer = clusterer or ClusteringEngine(
            config=config, extractor=self._extractor,
        )
        self._scorer = scorer or ScoringEngine(config=config)
        self._config = config or EventClusterConfig()

    def run(self, items: list[FeedItem]) -> EventIntelligenceResult:
        """Run the full event intelligence pipeline.

        Args:
            items: Raw FeedItems (including duplicates and fixtures).

        Returns:
            EventIntelligenceResult with dedup events and candidates.
        """
        start = _now_ms()
        errors: list[str] = []

        if not items:
            return EventIntelligenceResult(
                pipeline_status="ok", input_count=0, processing_ms=0,
            )

        # Filter out fixtures and research samples
        live_items = [i for i in items if i.data_mode == FeedDataMode.LIVE]

        # Step 1: Dedup
        dup_result = self._dedup.dedup(live_items)

        if not dup_result.canonical_items:
            return EventIntelligenceResult(
                pipeline_status="ok",
                input_count=len(live_items),
                removed_as_duplicate=dup_result.removed_count,
                event_count=0,
                dedup_result=dup_result,
                processing_ms=_now_ms() - start,
            )

        # Step 2: Cluster
        events = self._clusterer.cluster(
            dup_result.canonical_items, dup_result=dup_result,
        )

        # Step 3: Score
        candidates = []
        for event in events:
            candidate = self._scorer.compute(event)
            event.candidate = candidate
            candidates.append(candidate)

        elapsed = _now_ms() - start
        return EventIntelligenceResult(
            pipeline_status="ok",
            input_count=len(live_items),
            removed_as_duplicate=dup_result.removed_count,
            event_count=len(events),
            events=events,
            candidates=sorted(candidates, key=lambda c: c.score, reverse=True),
            dedup_result=dup_result,
            processing_ms=round(elapsed, 1),
            errors=errors,
        )
