"""
Observation contract — a single point-in-time data observation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .common import RevisionRef


@dataclass(frozen=True)
class DataAvailabilityRecord:
    """Record of when a specific piece of data was available to the model."""

    record_id: str
    entity_id: str
    field_name: str
    value_ref: str

    event_time: datetime
    published_at: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    retrieved_at: Optional[datetime] = None
    available_to_model_at: Optional[datetime] = None

    revision_id: Optional[str] = None
    source_id: Optional[str] = None
    availability_quality: Optional[str] = None


@dataclass(frozen=True)
class Observation:
    """A single validated observation at a point in time."""

    observation_id: str
    entity_id: str
    timestamp: datetime
    fields: dict[str, Any] = field(default_factory=dict)
    revision_ref: Optional[RevisionRef] = None
    availability: Optional[DataAvailabilityRecord] = None

    def is_available_as_of(self, as_of_time: datetime) -> bool:
        if self.availability and self.availability.available_to_model_at:
            return self.availability.available_to_model_at <= as_of_time
        # If no availability record, assume the observation timestamp is the limit
        return self.timestamp <= as_of_time
