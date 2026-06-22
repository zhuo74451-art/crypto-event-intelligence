from __future__ import annotations
from datetime import datetime
from typing import Optional
from ..contracts.replay import ReplayMode, ReplayQuery, ReplayResult
from ..contracts.observation import NormalizedObservation
from ..contracts.timestamps import utc_now


class PointInTimeReplayService:
    """Service for point-in-time replay of observations."""

    def __init__(self, observation_store: dict[str, NormalizedObservation] | None = None):
        self._observation_store = observation_store or {}

    def replay(self, query: ReplayQuery) -> ReplayResult:
        if query.mode == ReplayMode.KNOWLEDGE_AS_KNOWN_THEN:
            return self._replay_as_known(query)
        else:
            return self._replay_best_reconstruction(query)

    def _replay_as_known(self, query: ReplayQuery) -> ReplayResult:
        matched = self._get_filtered_observations(query)
        filtered = self._filter_by_first_seen(matched, query.as_of_time)
        return ReplayResult(
            query=query, observations=tuple(filtered),
            observation_count=len(filtered),
            mode_used=ReplayMode.KNOWLEDGE_AS_KNOWN_THEN,
            is_reconstructed=False,
            generated_at=utc_now().isoformat(),
        )

    def _replay_best_reconstruction(self, query: ReplayQuery) -> ReplayResult:
        matched = self._get_filtered_observations(query)
        return ReplayResult(
            query=query, observations=tuple(matched),
            observation_count=len(matched),
            mode_used=ReplayMode.CURRENT_BEST_RECONSTRUCTION,
            is_reconstructed=True,
            warnings=("May include observations not yet known at as_of_time",),
            generated_at=utc_now().isoformat(),
        )

    def _get_filtered_observations(self, query: ReplayQuery) -> list[NormalizedObservation]:
        results = []
        for obs in self._observation_store.values():
            if query.source_ids and obs.source_id not in query.source_ids:
                continue
            if query.content_types and obs.content_type not in query.content_types:
                continue
            results.append(obs)
        return results

    def _filter_by_first_seen(self, observations: list[NormalizedObservation], as_of: datetime) -> list[NormalizedObservation]:
        as_of_str = as_of.isoformat()
        filtered = []
        for obs in observations:
            first_seen = obs.timestamps.first_seen_at
            if first_seen.is_present() and first_seen.value:
                if first_seen.value.isoformat() <= as_of_str:
                    filtered.append(obs)
            else:
                filtered.append(obs)
        return filtered
