"""Signal Candidate scoring engine — deterministic explainable scores.

Score components (each 0-100):
  - freshness: 20% weight
  - novelty: 15% weight
  - source independence: 25% weight
  - asset relevance: 15% weight
  - event severity: 15% weight
  - evidence completeness: 10% weight

Total = weighted_average(components) - penalties, clamped to [0, 100].

Calibration rules:
  - Single-source NEW items must NOT default to HIGH_ATTENTION
  - Multiple independent sources required for HIGH_ATTENTION
  - CONFLICTING raises attention but adds penalty
  - All components explainable and independently verifiable
"""
from __future__ import annotations
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


# Weights (sum to 100)
_W_FRESHNESS = 20
_W_NOVELTY = 15
_W_INDEPENDENCE = 25
_W_ASSET = 15
_W_SEVERITY = 15
_W_EVIDENCE = 10


class ScoringEngine:
    """Deterministic scoring for IntelligenceEvents.

    Total = weighted_average(freshness, novelty, independence, asset, severity, evidence)
            - penalties
    Clamped to [0, 100].

    Args:
        config: EventClusterConfig with weights and thresholds.
        reference_time: Injection point for deterministic testing.
    """

    def __init__(self, config: Optional[EventClusterConfig] = None,
                 reference_time: Optional[datetime] = None):
        self._config = config or EventClusterConfig()
        self._ref_time = reference_time or datetime.now(timezone.utc)

    def compute(self, event: IntelligenceEvent) -> SignalCandidate:
        bd = ScoreBreakdown()

        # Freshness (0-100)
        bd.freshness = self._score_freshness(event)

        # Novelty (0-100)
        bd.novelty = self._score_novelty(event)

        # Source independence (0-100)
        si = event.source_independence
        indep = si.independent_source_count
        raw = si.raw_source_count
        # Scale: 0→0, 1→15, 2→40, 3→65, 4→80, 5+→100
        if indep >= 5:
            bd.source_independence = 100.0
        elif indep == 4:
            bd.source_independence = 80.0
        elif indep == 3:
            bd.source_independence = 65.0
        elif indep == 2:
            bd.source_independence = 40.0
        elif indep == 1:
            bd.source_independence = 15.0
        else:
            bd.source_independence = 0.0

        # Asset relevance (0-100)
        bd.asset_relevance = self._score_asset_relevance(event)

        # Event severity (0-100)
        bd.event_severity = self._score_severity(event)

        # Evidence completeness (0-100)
        bd.evidence_completeness = self._score_evidence(event)

        # ── Penalties ───────────────────────────────────────────────────────
        # Conflicting claims reduce confidence but not attention-level score
        if event.status == EventStatus.CONFLICTING:
            bd.conflict_penalty = 15.0

        # Single-item events get a duplication penalty (no cross-verification)
        if len(event.items) <= 1:
            bd.duplication_penalty = 15.0
        elif len(event.items) == 2 and raw <= 2:
            bd.duplication_penalty = 5.0

        # Stale / superseded
        if event.status in (EventStatus.STALE, EventStatus.SUPERSEDED):
            bd.stale_penalty = 50.0

        # Data quality penalty — no body = less reliable
        if event.items and all(not i.body for i in event.items):
            bd.data_quality_penalty = 20.0
        elif event.items and sum(1 for i in event.items if i.body) < len(event.items) / 2:
            bd.data_quality_penalty = 10.0

        total = bd.total

        # Determine level
        if total >= 70:
            level = CandidateLevel.HIGH_ATTENTION
        elif total >= 35:
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

    # ── Component scorers ───────────────────────────────────────────────────

    def _score_freshness(self, event: IntelligenceEvent) -> float:
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
        """Novelty based on event status AND source confirmation.

        A single-source NEW item is less novel than a multi-source NEW item.
        """
        indep = event.source_independence.independent_source_count
        is_single = len(event.items) <= 1 or indep <= 1

        if event.status == EventStatus.NEW:
            if is_single:
                return 20.0  # Single source, unconfirmed — low novelty
            return 40.0  # Multiple sources — medium novelty
        if event.status == EventStatus.DEVELOPING:
            return 50.0
        if event.status == EventStatus.CONFIRMED:
            return 60.0
        if event.status == EventStatus.CONFLICTING:
            return 55.0
        if event.status == EventStatus.UPDATED:
            return 35.0
        return 5.0  # STALE / SUPERSEDED

    def _score_asset_relevance(self, event: IntelligenceEvent) -> float:
        symbols = {a.symbol for a in event.assets}
        majors = symbols & {"BTC", "ETH", "SOL", "HYPE"}
        if not symbols:
            return 0.0
        score = min(100.0, len(symbols) * 15.0 + len(majors) * 15.0)
        return score

    def _score_severity(self, event: IntelligenceEvent) -> float:
        from .extraction import TOPIC_SEVERITY
        if not event.topics:
            return 15.0  # Default mild severity
        max_sev = max(TOPIC_SEVERITY.get(t.topic, 15.0) for t in event.topics)
        return max_sev

    def _score_evidence(self, event: IntelligenceEvent) -> float:
        if not event.items:
            return 0.0
        with_body = sum(1 for i in event.items if i.body)
        total = len(event.items)
        body_ratio = with_body / total if total > 0 else 0
        # Evidence: more items with bodies = higher score
        # 0 items → 0, 1 item → 15, 2 items → 30, 3+ → up to 60 based on body quality
        count_score = min(60.0, total * 10.0)
        # Body quality bonus
        body_bonus = body_ratio * 40.0
        return count_score + body_bonus
