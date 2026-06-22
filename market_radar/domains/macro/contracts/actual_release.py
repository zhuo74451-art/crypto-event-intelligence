from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from .common import MacroEnum, SeasonalAdjustment, UnitType, ObservationPeriod


class RevisionStatus(MacroEnum):
    """Indicates the revision stage of a published data point."""
    INITIAL = "initial"
    PRELIMINARY = "preliminary"
    REVISED = "revised"
    FINAL = "final"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OfficialReleaseRecord:
    """The officially published value for a macro release component.

    Attributes:
        release_event_id: The calendar event this actual belongs to.
        component_id: Which sub-component of the release.
        actual_value: The officially released numeric value.
        prior_value: The previously reported value for the same period.
        revised_prior_value: The prior value after any concurrent revision.
        unit: Unit of measurement.
        seasonal_adjustment: Seasonal adjustment status of this figure.
        annualization: Annualization method applied, if any.
        observation_period: The data period this release covers.
        published_at: The official publication timestamp.
        first_seen_at: When our system first observed this value.
        retrieved_at: When our system retrieved / scraped this record.
        source_id: Identifies the source feed.
        source_document_ref: Reference to the original source document / URL.
        revision_status: Revision stage of this figure.
    """
    release_event_id: str
    component_id: str
    actual_value: Optional[float] = None
    prior_value: Optional[float] = None
    revised_prior_value: Optional[float] = None
    unit: UnitType = UnitType.INDEX_LEVEL
    seasonal_adjustment: SeasonalAdjustment = SeasonalAdjustment.UNKNOWN
    annualization: Optional[str] = None
    observation_period: Optional[ObservationPeriod] = None
    published_at: Optional[datetime] = None
    first_seen_at: Optional[datetime] = None
    retrieved_at: Optional[datetime] = None
    source_id: str = ""
    source_document_ref: str = ""
    revision_status: RevisionStatus = RevisionStatus.INITIAL

    @property
    def has_value(self) -> bool:
        """True if an actual numeric value has been recorded."""
        return self.actual_value is not None

    @property
    def prior_was_revised(self) -> bool:
        """True if the prior value was revised concurrently."""
        return self.revised_prior_value is not None
