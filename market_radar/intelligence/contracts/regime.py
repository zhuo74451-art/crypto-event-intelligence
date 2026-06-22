"""Market regime contracts — regime snapshots, dimensions, transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from .common import ContractBase


class RegimeDimensionType(str, Enum):
    LIQUIDITY = "liquidity"
    RISK_APPETITE = "risk_appetite"
    VOLATILITY = "volatility"
    TREND = "trend"
    LEVERAGE = "leverage"
    MARKET_LEADERSHIP = "market_leadership"
    PARTICIPANT_MIX = "participant_mix"
    STABLECOIN_CONDITION = "stablecoin_condition"


@dataclass
class RegimeDimension(ContractBase):
    """A single market regime dimension expressed as a probability distribution."""
    contract_name: str = "RegimeDimension"
    schema_version: str = "1.0.0"

    dimension: RegimeDimensionType = RegimeDimensionType.VOLATILITY
    probabilities: dict[str, float] = field(default_factory=dict)
    pre_normalization: Optional[dict[str, float]] = None
    is_normalized: bool = True

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.dimension, str):
            self.dimension = RegimeDimensionType(self.dimension)

    def validate(self) -> list[str]:
        errors = []
        for k, v in self.probabilities.items():
            if v < 0.0 or v > 1.0:
                errors.append(f"Probability {k}={v} out of range [0, 1]")
        total = sum(self.probabilities.values())
        if abs(total - 1.0) > 0.01 and self.is_normalized:
            errors.append(f"Probabilities sum to {total}, expected ~1.0")
        return errors

    @property
    def dominant_state(self) -> Optional[str]:
        if not self.probabilities:
            return None
        return max(self.probabilities, key=self.probabilities.get)


@dataclass
class RegimeSnapshot(ContractBase):
    """A point-in-time snapshot of market regime."""
    contract_name: str = "RegimeSnapshot"
    schema_version: str = "1.0.0"

    regime_id: str = ""
    as_of_time: str = ""
    dimensions: dict[str, RegimeDimension] = field(default_factory=dict)
    source_refs: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.as_of_time:
            self.as_of_time = self.as_of_time
        # Convert dict dimensions
        if self.dimensions:
            converted = {}
            for k, v in self.dimensions.items():
                if isinstance(v, dict):
                    converted[k] = RegimeDimension(**v)
                else:
                    converted[k] = v
            self.dimensions = converted

    @property
    def missing_dimensions(self) -> list[str]:
        all_dims = {d.value for d in RegimeDimensionType}
        present = set(self.dimensions.keys())
        return sorted(all_dims - present)


@dataclass
class RegimeTransition(ContractBase):
    """A transition between regime snapshots."""
    contract_name: str = "RegimeTransition"
    schema_version: str = "1.0.0"

    transition_id: str = ""
    from_regime_id: str = ""
    to_regime_id: str = ""
    transition_time: str = ""
    reason: str = ""
    dimension_changes: dict[str, str] = field(default_factory=dict)


@dataclass
class RegimeApplicability(ContractBase):
    """Describes which regimes a strategy or hypothesis is valid in."""
    contract_name: str = "RegimeApplicability"
    schema_version: str = "1.0.0"

    valid_regimes: list[str] = field(default_factory=list)
    invalid_regimes: list[str] = field(default_factory=list)
    regime_adjustments: dict[str, dict[str, Any]] = field(default_factory=dict)

    def is_valid(self, regime_id: str) -> bool:
        if regime_id in self.invalid_regimes:
            return False
        if not self.valid_regimes:
            return True
        return regime_id in self.valid_regimes


def normalize_distribution(probabilities: dict[str, float]) -> dict[str, float]:
    """Normalize a probability distribution to sum to 1.0.

    Returns the normalized distribution. If sum is 0, returns empty dict.
    """
    total = sum(probabilities.values())
    if total == 0:
        return {}
    return {k: round(v / total, 4) for k, v in probabilities.items()}
