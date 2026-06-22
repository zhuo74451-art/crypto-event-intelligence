"""Tests for expectation gap engine."""

import pytest
from decimal import Decimal
from market_radar.intelligence.contracts.expectation import (
    NumericExpectation, NumericGap, NumericRangeExpectation,
    CategoricalExpectation, BinaryProbabilityExpectation,
    ExpectationGapResult, ExpectationType, GapStatus,
)
from market_radar.intelligence.engines.expectation_gap import ExpectationGapEngineV1


class TestNumericGap:
    def test_raw_gap_positive(self):
        engine = ExpectationGapEngineV1()
        exp = NumericExpectation(expected_value=100.0, std_dev=10.0)
        result = engine.compute_numeric_gap(exp, 105.0)
        assert result.gap_status == GapStatus.AVAILABLE
        assert result.numeric_gap.raw_gap == 5.0

    def test_raw_gap_negative(self):
        engine = ExpectationGapEngineV1()
        exp = NumericExpectation(expected_value=100.0, std_dev=10.0)
        result = engine.compute_numeric_gap(exp, 95.0)
        assert result.numeric_gap.raw_gap == -5.0

    def test_relative_gap(self):
        engine = ExpectationGapEngineV1()
        exp = NumericExpectation(expected_value=100.0, std_dev=10.0)
        result = engine.compute_numeric_gap(exp, 110.0)
        assert result.numeric_gap.relative_gap == 0.1

    def test_standardized_gap(self):
        engine = ExpectationGapEngineV1()
        exp = NumericExpectation(expected_value=100.0, std_dev=10.0)
        result = engine.compute_numeric_gap(exp, 105.0)
        assert abs(result.numeric_gap.standardized_gap - 0.5) < 0.01

    def test_std_dev_none_no_standardized(self):
        engine = ExpectationGapEngineV1()
        exp = NumericExpectation(expected_value=100.0, std_dev=None)
        result = engine.compute_numeric_gap(exp, 105.0)
        assert result.numeric_gap.standardized_gap is None

    def test_zero_std_dev_no_standardized(self):
        engine = ExpectationGapEngineV1()
        exp = NumericExpectation(expected_value=100.0, std_dev=0.0)
        result = engine.compute_numeric_gap(exp, 105.0)
        assert result.numeric_gap.standardized_gap is None

    def test_zero_expected_no_relative(self):
        engine = ExpectationGapEngineV1()
        exp = NumericExpectation(expected_value=0.0, std_dev=5.0)
        result = engine.compute_numeric_gap(exp, 5.0)
        assert result.numeric_gap.relative_gap is None

    def test_gap_direction_above(self):
        gap = NumericGap(raw_gap=5.0)
        assert gap.direction == "above"

    def test_gap_direction_below(self):
        gap = NumericGap(raw_gap=-3.0)
        assert gap.direction == "below"

    def test_gap_direction_inline(self):
        gap = NumericGap(raw_gap=0.0)
        assert gap.direction == "inline"


class TestRangeGap:
    def test_below_range(self):
        engine = ExpectationGapEngineV1()
        exp = NumericRangeExpectation(lower=100.0, upper=110.0)
        result = engine.compute_range_gap(exp, 95.0)
        assert result.range_classification == "below_range"

    def test_within_range(self):
        engine = ExpectationGapEngineV1()
        exp = NumericRangeExpectation(lower=100.0, upper=110.0)
        result = engine.compute_range_gap(exp, 105.0)
        assert result.range_classification == "within_range"

    def test_above_range(self):
        engine = ExpectationGapEngineV1()
        exp = NumericRangeExpectation(lower=100.0, upper=110.0)
        result = engine.compute_range_gap(exp, 115.0)
        assert result.range_classification == "above_range"

    def test_distance_to_boundary(self):
        exp = NumericRangeExpectation(lower=100.0, upper=110.0)
        assert exp.distance_to_boundary(95.0) == 5.0
        assert exp.distance_to_boundary(115.0) == 5.0
        assert exp.distance_to_boundary(105.0) == 0.0


class TestCategoricalGap:
    def test_as_expected(self):
        engine = ExpectationGapEngineV1()
        exp = CategoricalExpectation(expected_category="hold")
        result = engine.compute_categorical_gap(exp, "hold")
        assert result.categorical_classification == "as_expected"

    def test_unexpected_category(self):
        engine = ExpectationGapEngineV1()
        exp = CategoricalExpectation(
            expected_category="hold",
            alternative_categories=["raise", "cut"],
        )
        result = engine.compute_categorical_gap(exp, "raise")
        assert result.categorical_classification == "unexpected_category"

    def test_majority_unclear(self):
        engine = ExpectationGapEngineV1()
        exp = CategoricalExpectation(expected_category="hold")
        result = engine.compute_categorical_gap(exp, "unexpected")
        assert result.categorical_classification == "majority_unclear"


class TestProbabilityGap:
    def test_surprise_on_approval(self):
        engine = ExpectationGapEngineV1()
        exp = BinaryProbabilityExpectation(prior_probability=0.7)
        result = engine.compute_probability_gap(exp, True)
        assert abs(result.probability_surprise - 0.3) < 1e-10

    def test_surprise_on_rejection(self):
        engine = ExpectationGapEngineV1()
        exp = BinaryProbabilityExpectation(prior_probability=0.3)
        result = engine.compute_probability_gap(exp, True)
        assert result.probability_surprise == 0.7

    def test_no_expectation(self):
        engine = ExpectationGapEngineV1()
        result = engine.handle_no_expectation("No pre-event data")
        assert result.gap_status == GapStatus.UNAVAILABLE
        assert result.expectation_quality == "insufficient"
