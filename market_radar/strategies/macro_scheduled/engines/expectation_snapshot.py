from __future__ import annotations
from datetime import datetime
from typing import List, Optional, Tuple
from market_radar.domains.macro.contracts.expectation import (
    ExpectationSnapshot, ExpectationQuality, ExpectationSource,
)
from market_radar.domains.macro.contracts.component import CompositionConflict


class ExpectationSnapshotEngine:
    @staticmethod
    def is_post_release_contamination(snapshot: ExpectationSnapshot, release_time: datetime) -> bool:
        """Check if expectation was captured after release (post-hoc contamination)."""
        return snapshot.captured_at > release_time

    @staticmethod
    def detect_conflict(snapshots: List[ExpectationSnapshot]) -> Optional[CompositionConflict]:
        """Detect if multiple expectation sources conflict significantly."""
        if len(snapshots) < 2:
            return None
        values = [s.expected_value for s in snapshots if s.expected_value is not None]
        if len(values) < 2:
            return None
        mean_val = sum(values) / len(values)
        max_dev = max(abs(v - mean_val) for v in values)
        threshold = max(0.1, abs(mean_val) * 0.2) if mean_val != 0 else 0.1
        if max_dev > threshold:
            return CompositionConflict(
                component_a=snapshots[0].component_id,
                component_b=snapshots[1].component_id,
                conflict_type="expectation_divergence",
                description=f"Expectation values diverge: {values}",
            )
        return None

    @staticmethod
    def assess_quality(snapshot: ExpectationSnapshot) -> ExpectationQuality:
        """Assess the overall quality of an expectation snapshot."""
        if snapshot.quality == ExpectationQuality.INSUFFICIENT:
            return ExpectationQuality.INSUFFICIENT
        if snapshot.quality == ExpectationQuality.RECONSTRUCTED:
            return ExpectationQuality.RECONSTRUCTED
        if snapshot.quality == ExpectationQuality.CONFLICTING:
            return ExpectationQuality.CONFLICTING
        if snapshot.source_type == ExpectationSource.RECONSTRUCTED.value:
            return ExpectationQuality.RECONSTRUCTED
        if snapshot.respondent_count is not None and snapshot.respondent_count < 3:
            return ExpectationQuality.WEAK
        return snapshot.quality

    @staticmethod
    def has_independent_sources(snapshots: List[ExpectationSnapshot]) -> bool:
        """Check if multiple snapshots come from independent sources."""
        sources = set(s.source_type for s in snapshots if s.source_type is not None)
        return len(sources) >= 2

    @staticmethod
    def compute_consensus_range(snapshots: List[ExpectationSnapshot]) -> Tuple[Optional[float], Optional[float]]:
        """Compute the low-high range across all snapshots."""
        values = [s.expected_value for s in snapshots if s.expected_value is not None]
        if not values:
            return None, None
        return min(values), max(values)
