from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class YieldObservation:
    """A single yield observation for a specific tenor.

    Attributes:
        tenor: The maturity tenor label (e.g. '2Y', '10Y', '30Y').
        yield_value: The yield in basis points or percent.
        change_bps: Change from previous close in basis points.
        real_yield: Real yield (nominal minus breakeven), if available.
    """
    tenor: str
    yield_value: Optional[float] = None
    change_bps: Optional[float] = None
    real_yield: Optional[float] = None


@dataclass(frozen=True)
class EquityObservation:
    """A single equity index observation.

    Attributes:
        index_name: Name of the equity index (e.g. 'S&P 500', 'NASDAQ').
        price_level: Current index level.
        change_pct: Percentage change from previous close.
        volume_relative: Volume relative to recent average.
    """
    index_name: str
    price_level: Optional[float] = None
    change_pct: Optional[float] = None
    volume_relative: Optional[float] = None


@dataclass(frozen=True)
class CrossAssetSnapshot:
    """A snapshot of key cross-asset market conditions at a point in time.

    Attributes:
        yields: Mapping of yield curve observations keyed by market code.
        dollar: DXY or equivalent dollar index level / change.
        equities: List of equity index observations.
        gold: Gold spot price observation (value, change).
        timestamp: When this cross-asset snapshot was taken.
    """
    yields: dict[str, YieldObservation] = field(default_factory=dict)
    dollar: Optional[float] = None
    equities: list[EquityObservation] = field(default_factory=list)
    gold: Optional[float] = None
    timestamp: Optional[datetime] = None

    @property
    def has_data(self) -> bool:
        """True if at least one asset class has data."""
        return bool(self.yields) or self.dollar is not None or bool(self.equities) or self.gold is not None
