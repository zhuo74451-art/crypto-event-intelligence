from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MacroEnum(Enum):
    """Base enum for all macro domain enums."""

    @classmethod
    def members(cls) -> list[str]:
        return [m.name for m in cls]

    @classmethod
    def values(cls) -> list:
        return [m.value for m in cls]

    def describe(self) -> str:
        return f"{self.__class__.__name__}.{self.name}"


class DataQuality(MacroEnum):
    """Quality of the underlying data source."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


class SeasonalAdjustment(MacroEnum):
    """Indicates whether a data series has been seasonally adjusted."""
    SEASONALLY_ADJUSTED = "seasonally_adjusted"
    NOT_SEASONALLY_ADJUSTED = "not_seasonally_adjusted"
    UNKNOWN = "unknown"


class UnitType(MacroEnum):
    """Unit of measurement for a macro-economic data point."""
    PERCENT = "percent"
    BASIS_POINTS = "basis_points"
    INDEX_LEVEL = "index_level"
    THOUSANDS = "thousands"
    RATIO = "ratio"
    CHANGE_MOM = "change_mom"
    CHANGE_YOY = "change_yoy"
    CHANGE_ANNUALIZED = "change_annualized"


@dataclass(frozen=True)
class ObservationPeriod:
    """The time period to which a macro observation belongs.

    Attributes:
        period_start: Inclusive start of the observation window.
        period_end: Inclusive end of the observation window.
        period_label: Human-readable label (e.g. '2024-Q1', 'Jan 2024').
    """
    period_start: datetime
    period_end: datetime
    period_label: str

    def __post_init__(self) -> None:
        if self.period_end < self.period_start:
            raise ValueError(
                f"period_end ({self.period_end}) must not be before "
                f"period_start ({self.period_start})"
            )

    def duration_days(self) -> float:
        """Return the length of the observation window in days."""
        return (self.period_end - self.period_start).total_seconds() / 86400.0


@dataclass(frozen=True)
class SourceRef:
    """A reference to the origin of a data point.

    Attributes:
        source_id: Identifies the provider or feed (e.g. 'bloomberg_tick').
        source_type: Category of the source (e.g. 'vendor_feed', 'manual').
        retrieval_time: When this data point was retrieved / recorded.
    """
    source_id: str
    source_type: str
    retrieval_time: datetime
