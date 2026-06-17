"""Signal Candidate scoring engine — deterministic explainable scores.

Score components (each 0-100, weighted):
  - freshness: 20%
  - novelty: 15%
  - source independence: 25%
  - asset relevance: 15%
  - event severity: 15%
  - evidence completeness: 10%

Penalties subtract from total.
"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from .models import (
    IntelligenceEvent, EventClusterConfig, ScoreBreakdown,
    SignalCandidate, CandidateLevel,
    EventStatus,
)

_NONWORD = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


class ScoringEngine:
    """Deterministic scoring for IntelligenceEvents.

    Args:
        config: EventClusterConfig with weights and thresholds.
        reference_time: Injection point for deterministic testing.
    """

    def __init__(self, config: Optional[EventClusterConfig] = None,
                 reference_time: Optional[datetime] = None):
        self._config = config or EventClusterConfig()
        self._ref_time = reference_time or datetime.now(timezone.utc)

    def compute(self, event: IntelligenceEvent) -> SignalCandidate:
        """Compute a SignalCandidate from an IntelligenceEvent."""
        bd = ScoreBreakdown()

        # Freshness (0-100)
        bd.freshness = self._score_freshness(event)

        # Novelty (0-100)
        bd.novelty = self._score_novelty(event)

        # Source independence (0-100)
        si = event.source_independence
        bd.source_independence = min(100.0, si.independent_source_count * 25.0)

        # Asset relevance (0-100)
        bd.asset_relevance = self._score_asset_relevance(event)

        # Event severity (0-100)
        bd.event_severity = self._score_severity(event)

        # Evidence completeness (0-100)
        bd.evidence_completeness = self._score_evidence(event)

        # Penalties
        if event.status == EventStatus.CONFLICTING:
            bd.conflict_penalty = 20.0
        if len(event.items) <= 1:
            bd.duplication_penalty = 10.0
        if event.status in (EventStatus.STALE, EventStatus.SUPERSEDED):
            bd.stale_penalty = 40.0

        total = bd.total

        # Determine level
        if total >= 70:
            level = CandidateLevel.HIGH_ATTENTION
        elif total >= 40:
            level = CandidateLevel.REVIEW
        else:
            level = CandidateLevel.WATCH

        return SignalCandidate(
            event_id=event.event_id,
            level=level,
            score=round(total, 1),
            breakdown=bd,
            top_assets=[a.symbol for a in event.assets[:5]],
            top_topics=[t.topic for t in event.topics[:5]],
            canonical_title=event.canonical_title,
            summary=event.summary[:150],
            source_count=event.source_count,
            independent_count=event.source_independence.independent_source_count,
        )

    def _score_freshness(self, event: IntelligenceEvent) -> float:
        """Score based on how recent the event is."""
        latest = _parse_ts(event.latest_at)
        if not latest:
            return 0.0
        hours = (self._ref_time - latest).total_seconds() / 3600
        if hours <= 1:
            return 100.0
        if hours <= 6:
            return 80.0
        if hours <= 24:
            return 50.0
        if hours <= 72:
            return 20.0
        return 0.0

    def _score_novelty(self, event: IntelligenceEvent) -> float:
        """Score based on event status and newness."""
        if event.status in (EventStatus.NEW, EventStatus.DEVELOPING):
            return 80.0
        if event.status == EventStatus.CONFIRMED:
            return 60.0
        if event.status == EventStatus.UPDATED:
            return 40.0
        if event.status == EventStatus.CONFLICTING:
            return 50.0
        return 10.0

    def _score_asset_relevance(self, event: IntelligenceEvent) -> float:
        """Score based on number and type of assets mentioned."""
        symbols = {a.symbol for a in event.assets}
        majors = symbols & {"BTC", "ETH", "SOL", "HYPE"}
        if not symbols:
            return 0.0
        score = min(100.0, len(symbols) * 20.0 + len(majors) * 10.0)
        return score

    def _score_severity(self, event: IntelligenceEvent) -> float:
        """Score based on event type/topic severity."""
        from .extraction import TOPIC_SEVERITY
        if not event.topics:
            return 20.0
        max_sev = max(TOPIC_SEVERITY.get(t.topic, 20.0) for t in event.topics)
        return max_sev

    def _score_evidence(self, event: IntelligenceEvent) -> float:
        """Score based on evidence quality."""
        if not event.items:
            return 0.0
        with_body = sum(1 for i in event.items if i.body)
        ratio = with_body / len(event.items)
        count_score = min(50.0, len(event.items) * 10.0)
        body_score = ratio * 50.0
        return count_score + body_score
