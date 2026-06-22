"""Expectation Gap Engine V1 — compute gaps between actual and expected values."""

from __future__ import annotations

from typing import Optional, Union
from decimal import Decimal

from ..contracts.expectation import (
    ExpectationType, GapStatus,
    NumericExpectation, NumericGap,
    NumericRangeExpectation, CategoricalExpectation,
    BinaryProbabilityExpectation, NoReliableExpectation,
    ExpectationGapResult,
)
from ..errors.codes import IntelligenceError, ErrorCode


class ExpectationGapEngineV1:
    """Compute expectation gaps from structured expectations and actual outcomes."""

    @staticmethod
    def compute_numeric_gap(expectation: NumericExpectation,
                            actual: float) -> ExpectationGapResult:
        """Compute numeric expectation gap.

        raw_gap = actual - expected
        relative_gap = raw_gap / expected (if expected != 0)
        standardized_gap = raw_gap / std_dev (if std_dev available and > 0)
        """
        expected = expectation.expected_value
        raw_gap = actual - expected

        relative_gap = None
        if expected != 0:
            relative_gap = raw_gap / expected

        standardized_gap = None
        if expectation.std_dev is not None and expectation.std_dev > 0:
            standardized_gap = raw_gap / expectation.std_dev

        numeric_gap = NumericGap(
            raw_gap=round(raw_gap, 6),
            relative_gap=round(relative_gap, 6) if relative_gap is not None else None,
            standardized_gap=round(standardized_gap, 6) if standardized_gap is not None else None,
        )

        return ExpectationGapResult(
            expectation_type=ExpectationType.NUMERIC_CONSENSUS,
            gap_status=GapStatus.AVAILABLE,
            numeric_gap=numeric_gap,
            expectation_quality="available",
            notes=f"Numeric expectation {expected}, actual {actual}, gap {raw_gap:.4f}",
        )

    @staticmethod
    def compute_range_gap(expectation: NumericRangeExpectation,
                          actual: float) -> ExpectationGapResult:
        """Classify actual value relative to an expected range."""
        classification = expectation.classify(actual)
        distance = expectation.distance_to_boundary(actual)

        return ExpectationGapResult(
            expectation_type=ExpectationType.NUMERIC_RANGE,
            gap_status=GapStatus.AVAILABLE,
            range_classification=classification,
            expectation_quality="available",
            notes=f"Range [{expectation.lower}, {expectation.upper}], "
                  f"actual {actual}: {classification} (distance {distance:.4f})",
        )

    @staticmethod
    def compute_categorical_gap(expectation: CategoricalExpectation,
                                actual_category: str) -> ExpectationGapResult:
        """Classify actual category relative to expected."""
        classification = expectation.classify(actual_category)

        return ExpectationGapResult(
            expectation_type=ExpectationType.CATEGORICAL,
            gap_status=GapStatus.AVAILABLE,
            categorical_classification=classification,
            expectation_quality="available" if classification == "as_expected" else "surprise",
            notes=f"Expected {expectation.expected_category}, actual {actual_category}: {classification}",
        )

    @staticmethod
    def compute_probability_gap(expectation: BinaryProbabilityExpectation,
                                outcome: bool) -> ExpectationGapResult:
        """Compute surprise from a binary probability expectation."""
        updated = BinaryProbabilityExpectation(
            prior_probability=expectation.prior_probability,
            outcome=outcome,
            source=expectation.source,
        )

        return ExpectationGapResult(
            expectation_type=ExpectationType.BINARY_PROBABILITY,
            gap_status=GapStatus.AVAILABLE,
            probability_surprise=updated.surprise_information,
            expectation_quality="available",
            notes=f"Prior {expectation.prior_probability}, outcome {outcome}, "
                  f"surprise {updated.surprise_information:.4f}",
        )

    @staticmethod
    def handle_no_expectation(reason: str = "") -> ExpectationGapResult:
        """Return a gap result for when no reliable expectation exists."""
        return ExpectationGapResult(
            expectation_type=ExpectationType.NO_RELIABLE_EXPECTATION,
            gap_status=GapStatus.UNAVAILABLE,
            expectation_quality="insufficient",
            notes=reason or "No reliable pre-event expectation available",
        )
