"""Extension C: Event Export Contract — stable JSON contract for W1 integration.

Methods:
  export_events(events) -> list[dict]
  export_candidates(candidates) -> list[dict]
  export_result(events, candidates, stats) -> dict

All output is deterministic, no runtime UUIDs, no LLM.
"""
from __future__ import annotations
from typing import Any
from .models import IntelligenceEvent, SignalCandidate
from .relationship import RelationshipGraph


def export_event(event: IntelligenceEvent) -> dict:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "canonical_title": event.canonical_title,
        "summary": event.summary[:200],
        "started_at": event.started_at,
        "latest_at": event.latest_at,
        "status": event.status.value,
        "assets": [{"symbol": a.symbol, "name": a.full_name} for a in event.assets],
        "entities": [{"name": e.name, "type": e.entity_type} for e in event.entities],
        "topics": [t.topic for t in event.topics],
        "source_count": event.source_count,
        "source_diversity": event.source_diversity,
        "evidence_count": event.evidence_count,
        "conflicting_claims": event.conflicting_claims,
        "source_independence": {
            "raw_count": event.source_independence.raw_source_count,
            "independent_count": event.source_independence.independent_source_count,
            "mirrored_count": event.source_independence.mirrored_count,
        },
        "item_ids": [i.feed_id for i in event.items],
        "timeline": [{"ts": e.timestamp, "type": e.event_type, "src": e.source_label}
                     for e in event.timeline],
        "provenance": event.provenance,
    }


def export_candidate(candidate: SignalCandidate) -> dict:
    bd = candidate.breakdown
    return {
        "event_id": candidate.event_id,
        "level": candidate.level.value,
        "score": candidate.score,
        "score_components": {
            "freshness": round(bd.freshness, 1),
            "novelty": round(bd.novelty, 1),
            "source_independence": round(bd.source_independence, 1),
            "asset_relevance": round(bd.asset_relevance, 1),
            "event_severity": round(bd.event_severity, 1),
            "evidence_completeness": round(bd.evidence_completeness, 1),
            "conflict_penalty": round(bd.conflict_penalty, 1),
            "duplication_penalty": round(bd.duplication_penalty, 1),
            "stale_penalty": round(bd.stale_penalty, 1),
            "data_quality_penalty": round(bd.data_quality_penalty, 1),
        },
        "top_assets": candidate.top_assets,
        "top_topics": candidate.top_topics,
        "canonical_title": candidate.canonical_title,
        "source_count": candidate.source_count,
        "independent_count": candidate.independent_count,
    }


def export_graph(graph: RelationshipGraph) -> list[dict]:
    return [
        {"source_id": r.source_id, "target_id": r.target_id,
         "relationship": r.relationship, "confidence": r.confidence,
         "inferred": r.inferred, "evidence": r.evidence}
        for r in graph.relationships
    ]


def export_result(
    events: list[IntelligenceEvent],
    candidates: list[SignalCandidate],
    input_count: int = 0,
    removed_as_duplicate: int = 0,
    processing_ms: float = 0.0,
    pipeline_status: str = "ok",
) -> dict:
    return {
        "pipeline_status": pipeline_status,
        "input_count": input_count,
        "removed_as_duplicate": removed_as_duplicate,
        "event_count": len(events),
        "events": [export_event(e) for e in events],
        "candidates": [export_candidate(c) for c in candidates],
        "processing_ms": processing_ms,
    }
