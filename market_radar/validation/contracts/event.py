"""
Event contract — validated event representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import ValidationEventIdentity


@dataclass(frozen=True)
class ValidationEvent:
    """A real-world event in the validation system with Point-in-Time guarantees."""

    event_id: str
    identity: ValidationEventIdentity
    event_type: str
    published_at: datetime
    effective_at: datetime
    first_seen_at: Optional[datetime] = None
    assets: list[str] = field(default_factory=list)

    # Source tracking
    source_id: str = ""
    content_hash: str = ""
    independence_group: str = ""

    def as_of(self, point_in_time: datetime) -> bool:
        """Check if this event was known as of a given time."""
        known_time = self.first_seen_at or self.published_at
        if known_time is None:
            return False
        return known_time <= point_in_time


@dataclass(frozen=True)
class EventCluster:
    """A cluster of related events (same real-world event from multiple sources)."""

    event_cluster_id: str
    primary_event_id: str
    member_event_ids: list[str] = field(default_factory=list)
    source_dependence_group: str = ""
    duplicate_reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DuplicateReason:
    code: str  # e.g. "SAME_SOURCE_RETRANSMISSION", "CROSS_MEDIA_SAME_EVENT"
    description: str
