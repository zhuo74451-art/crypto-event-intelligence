"""Extension A: Event Relationship Graph — local non-persistent relationships.

Relationships:
  - precedes: event A happened before event B
  - updates: event B is a newer version of event A
  - contradicts: events have conflicting claims
  - same_entity: events share key entities
  - same_asset: events share key assets
  - possible_consequence: event B may be a consequence of event A (marked as inferred)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from .models import IntelligenceEvent


class RelationshipType(str):
    PRECEDES = "precedes"
    UPDATES = "updates"
    CONTRADICTS = "contradicts"
    SAME_ENTITY = "same_entity"
    SAME_ASSET = "same_asset"
    POSSIBLE_CONSEQUENCE = "possible_consequence"


@dataclass
class EventRelationship:
    source_id: str
    target_id: str
    relationship: str
    confidence: float = 1.0
    inferred: bool = False
    evidence: str = ""


@dataclass
class RelationshipGraph:
    relationships: list[EventRelationship] = field(default_factory=list)

    def get_related(self, event_id: str) -> list[EventRelationship]:
        return [r for r in self.relationships if r.source_id == event_id or r.target_id == event_id]


def build_relationship_graph(events: list[IntelligenceEvent]) -> RelationshipGraph:
    """Build relationship graph from events deterministically."""
    graph = RelationshipGraph()
    event_map = {e.event_id: e for e in events}

    for i, a in enumerate(events):
        for b in events[i + 1:]:
            # Same asset
            a_assets = {asst.symbol for asst in a.assets}
            b_assets = {asst.symbol for asst in b.assets}
            shared_assets = a_assets & b_assets

            if shared_assets:
                graph.relationships.append(EventRelationship(
                    source_id=a.event_id, target_id=b.event_id,
                    relationship=RelationshipType.SAME_ASSET,
                    confidence=0.8, inferred=False,
                    evidence=f"Shared assets: {', '.join(shared_assets)}",
                ))

            # Same entity
            a_entities = {e.name.lower() for e in a.entities}
            b_entities = {e.name.lower() for e in b.entities}
            shared_entities = a_entities & b_entities
            if shared_entities:
                graph.relationships.append(EventRelationship(
                    source_id=a.event_id, target_id=b.event_id,
                    relationship=RelationshipType.SAME_ENTITY,
                    confidence=0.7, inferred=False,
                    evidence=f"Shared entities: {', '.join(shared_entities)}",
                ))

            # Contradicts
            if a.conflicting_claims or b.conflicting_claims:
                graph.relationships.append(EventRelationship(
                    source_id=a.event_id, target_id=b.event_id,
                    relationship=RelationshipType.CONTRADICTS,
                    confidence=0.5, inferred=True,
                    evidence="Events contain conflicting claims",
                ))

            # Possible consequence (must mark as inferred)
            if shared_assets and a.latest_at and b.started_at:
                if b.started_at > a.latest_at:
                    graph.relationships.append(EventRelationship(
                        source_id=a.event_id, target_id=b.event_id,
                        relationship=RelationshipType.POSSIBLE_CONSEQUENCE,
                        confidence=0.3, inferred=True,
                        evidence="Temporal: B started after A's latest; shared assets",
                    ))

    return graph
