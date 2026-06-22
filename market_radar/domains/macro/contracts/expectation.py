from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from .common import MacroEnum, SeasonalAdjustment, UnitType


class ExpectationQuality(MacroEnum):
    """Confidence / reliability of a collected expectation."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"
    RECONSTRUCTED = "reconstructed"
    CONFLICTING = "conflicting"


class ExpectationType(MacroEnum):
    """The structural form of the expectation."""
    NUMERIC_POINT = "numeric_point"
    NUMERIC_RANGE = "numeric_range"
    DISTRIBUTION_SUMMARY = "distribution_summary"
    BINARY_PROBABILITY = "binary_probability"
    CATEGORICAL = "categorical"
    NO_RELIABLE_EXPECTATION = "no_reliable_expectation"


class ExpectationSource(MacroEnum):
    """Known providers of consensus or individual expectation data."""
    BLOOMBERG = "bloomberg"
    REUTERS = "reuters"
    INVESTING_DOT_COM = "investing_dot_com"
    FOREX_FACTORY = "forex_factory"
    FED_SURVEY = "fed_survey"
    CLEVELAND_FED = "cleveland_fed"
    CME_FEDWATCH = "cme_fedwatch"
    MANUAL = "manual"
    RECONSTRUCTED = "reconstructed"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ExpectationSnapshot:
    """A single captured expectation for a macro release component.

    Attributes:
        expectation_snapshot_id: Unique ID for this captured expectation.
        release_event_id: The release calendar event this belongs to.
        component_id: Which sub-component of the release (e.g. 'headline_cpi').
        captured_at: Timestamp when this expectation was captured / polled.
        valid_for_release_time: The release time this expectation is for.
        expected_value: Primary point-estimate value.
        expected_low: Lower bound (for range / interval expectations).
        expected_high: Upper bound (for range / interval expectations).
        median: Median value (when distribution summaries are available).
        mean: Mean value (when distribution summaries are available).
        dispersion: Standard deviation / interquartile range indicator.
        respondent_count: Number of economists / contributors polled.
        unit: Unit of measurement for the expected values.
        seasonal_adjustment: Whether the expectation is seasonally adjusted.
        annualization: Annualization method, if any.
        source_id: Identifies the source feed.
        source_type: Category of source (vendor_feed, manual, etc.).
        source_first_seen_at: When this expectation first appeared.
        quality: Assessed quality of this expectation snapshot.
        limitations: Free-text notes on caveats / known issues.
    """
    expectation_snapshot_id: str
    release_event_id: str
    component_id: str
    captured_at: datetime
    valid_for_release_time: datetime
    expected_value: Optional[float] = None
    expected_low: Optional[float] = None
    expected_high: Optional[float] = None
    median: Optional[float] = None
    mean: Optional[float] = None
    dispersion: Optional[float] = None
    respondent_count: Optional[int] = None
    unit: UnitType = UnitType.INDEX_LEVEL
    seasonal_adjustment: SeasonalAdjustment = SeasonalAdjustment.UNKNOWN
    annualization: Optional[str] = None
    source_id: str = ""
    source_type: str = ""
    source_first_seen_at: Optional[datetime] = None
    quality: ExpectationQuality = ExpectationQuality.INSUFFICIENT
    limitations: list[str] = field(default_factory=list)

    @property
    def has_range(self) -> bool:
        """True if both low and high bounds are present."""
        return self.expected_low is not None and self.expected_high is not None

    @property
    def has_distribution(self) -> bool:
        """True if median/mean and dispersion are present."""
        return (
            (self.median is not None or self.mean is not None)
            and self.dispersion is not None
        )
