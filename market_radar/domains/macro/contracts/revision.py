from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from .common import MacroEnum


class RevisionType(MacroEnum):
    """Classification of the reason for a revision."""
    ANNUAL = "annual"
    BENCHMARK = "benchmark"
    SEASONAL_FACTOR = "seasonal_factor"
    METHODOLOGY_CHANGE = "methodology_change"
    CORRECTION = "correction"
    OTHER = "other"


@dataclass(frozen=True)
class OfficialRevisionRecord:
    """A record of a revision to a previously published macro data point.

    Attributes:
        revision_id: Unique identifier for this revision record.
        release_event_id: The release event this revision belongs to.
        component_id: Which component was revised.
        prior_value: The value before revision.
        revised_value: The value after revision.
        revision_type: Classification of the revision reason.
        revision_reason: Free-text explanation of the revision.
        revision_date: When the revision was published / applied.
        effective_as_of: The data vintage this revision is effective from.
    """
    revision_id: str
    release_event_id: str
    component_id: str
    prior_value: Optional[float] = None
    revised_value: Optional[float] = None
    revision_type: RevisionType = RevisionType.OTHER
    revision_reason: str = ""
    revision_date: Optional[datetime] = None
    effective_as_of: Optional[datetime] = None

    @property
    def absolute_change(self) -> Optional[float]:
        """Absolute change from prior to revised value."""
        if self.prior_value is not None and self.revised_value is not None:
            return self.revised_value - self.prior_value
        return None

    @property
    def pct_change(self) -> Optional[float]:
        """Percentage change from prior to revised value."""
        if (
            self.prior_value is not None
            and self.revised_value is not None
            and self.prior_value != 0.0
        ):
            return ((self.revised_value - self.prior_value) / abs(self.prior_value)) * 100.0
        return None
