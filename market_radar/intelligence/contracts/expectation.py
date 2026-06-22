"""Expectation gap contracts — numeric, range, categorical, binary probability expectations."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from .common import ContractBase


class ExpectationType(str, Enum):
    NUMERIC_CONSENSUS = "numeric_consensus"
    NUMERIC_RANGE = "numeric_range"
    CATEGORICAL = "categorical"
    BINARY_PROBABILITY = "binary_probability"
    NO_RELIABLE_EXPECTATION = "no_reliable_expectation"


class GapStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    INSUFFICIENT = "insufficient"


@dataclass
class NumericExpectation(ContractBase):
    """A numeric consensus expectation with standard deviation."""
    contract_name: str = "NumericExpectation"
    schema_version: str = "1.0.0"

    expected_value: float = 0.0
    std_dev: Optional[float] = None
    sample_count: Optional[int] = None
    source: str = ""


@dataclass
class NumericGap(ContractBase):
    """The gap between actual and expected values."""
    contract_name: str = "NumericGap"
    schema_version: str = "1.0.0"

    raw_gap: float = 0.0
    relative_gap: Optional[float] = None
    standardized_gap: Optional[float] = None
    direction: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.raw_gap is not None:
            self.direction = "above" if self.raw_gap > 0 else "below" if self.raw_gap < 0 else "inline"


@dataclass
class NumericRangeExpectation(ContractBase):
    """A range expectation with lower and upper bounds."""
    contract_name: str = "NumericRangeExpectation"
    schema_version: str = "1.0.0"

    lower: float = 0.0
    upper: float = 0.0
    source: str = ""

    def classify(self, actual: float) -> str:
        if actual < self.lower:
            return "below_range"
        elif actual > self.upper:
            return "above_range"
        return "within_range"

    def distance_to_boundary(self, actual: float) -> float:
        if actual < self.lower:
            return self.lower - actual
        elif actual > self.upper:
            return actual - self.upper
        return 0.0


@dataclass
class CategoricalExpectation(ContractBase):
    """A categorical expectation with expected and alternative categories."""
    contract_name: str = "CategoricalExpectation"
    schema_version: str = "1.0.0"

    expected_category: str = ""
    alternative_categories: list[str] = field(default_factory=list)
    source: str = ""

    def classify(self, actual_category: str) -> str:
        if actual_category == self.expected_category:
            return "as_expected"
        if actual_category in self.alternative_categories:
            return "unexpected_category"
        return "majority_unclear"


@dataclass
class BinaryProbabilityExpectation(ContractBase):
    """A binary probability expectation (e.g., 70% chance of approval)."""
    contract_name: str = "BinaryProbabilityExpectation"
    schema_version: str = "1.0.0"

    prior_probability: float = 0.5
    outcome: Optional[bool] = None
    surprise_information: Optional[float] = None
    source: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.outcome is not None and self.surprise_information is None:
            self.surprise_information = abs(self.prior_probability - (1.0 if self.outcome else 0.0))


@dataclass
class NoReliableExpectation(ContractBase):
    """Marker for when no reliable pre-event expectation exists."""
    contract_name: str = "NoReliableExpectation"
    schema_version: str = "1.0.0"

    reason: str = ""


@dataclass
class ExpectationGapResult(ContractBase):
    """The computed expectation gap result."""
    contract_name: str = "ExpectationGapResult"
    schema_version: str = "1.0.0"

    expectation_type: ExpectationType = ExpectationType.NO_RELIABLE_EXPECTATION
    gap_status: GapStatus = GapStatus.UNAVAILABLE
    numeric_gap: Optional[NumericGap] = None
    range_classification: Optional[str] = None
    categorical_classification: Optional[str] = None
    probability_surprise: Optional[float] = None
    expectation_quality: str = "insufficient"
    notes: str = ""

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.expectation_type, str):
            self.expectation_type = ExpectationType(self.expectation_type)
        if isinstance(self.gap_status, str):
            self.gap_status = GapStatus(self.gap_status)
