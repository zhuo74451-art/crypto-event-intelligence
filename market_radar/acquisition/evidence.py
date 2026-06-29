"""Evidence manifest — creates verifiable evidence entries for each observation.

Each entry captures what was observed, when, from which source, and the
raw evidence path + hash so an independent verifier can cross-check.
"""

from __future__ import annotations

from typing import Any, Dict, List

from market_radar.acquisition.contracts import ObservationStub


def build_evidence_entries(
    source_id: str,
    observations: List[ObservationStub],
    artifact_path: str,
    content_sha256: str,
) -> List[Dict[str, Any]]:
    """Build evidence manifest entries for a set of observations.

    Uses the per-observation ``raw_provenance`` for artifact path and SHA-256
    when available, falling back to the top-level *artifact_path*/*content_sha256*.
    This ensures multi-file sources (e.g. Congress per-feed XML) point to the
    correct individual artifact rather than a summary file.
    """
    entries: List[Dict[str, Any]] = []
    for obs in observations:
        rp = obs.raw_provenance
        entry = {
            "observation_id": obs.observation_id,
            "source_id": source_id,
            "title": obs.title,
            "event_time": obs.event_time,
            "observed_at": obs.observed_at,
            "raw_artifact_path": rp.get("raw_artifact_path", artifact_path),
            "raw_artifact_sha256": rp.get("content_sha256", content_sha256),
            "record_key": rp.get("record_key", ""),
            "feed_id": rp.get("feed_id", ""),
            "repo": rp.get("repo", ""),
            "series_id": rp.get("series_id", ""),
        }
        entries.append(entry)
    return entries
