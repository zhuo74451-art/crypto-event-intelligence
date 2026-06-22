"""Tests for regime state contracts."""

import pytest
from market_radar.intelligence.contracts.regime import (
    RegimeDimension, RegimeSnapshot, RegimeTransition,
    RegimeDimensionType, normalize_distribution,
)


class TestRegimeDimension:
    def test_normal_distribution(self):
        dim = RegimeDimension(
            dimension=RegimeDimensionType.VOLATILITY,
            probabilities={"low": 0.3, "medium": 0.5, "high": 0.2},
        )
        errors = dim.validate()
        assert len(errors) == 0

    def test_probability_out_of_range(self):
        dim = RegimeDimension(
            dimension=RegimeDimensionType.LEVERAGE,
            probabilities={"low": 1.5, "high": 0.5},
        )
        errors = dim.validate()
        assert any("out of range" in e for e in errors)

    def test_sum_not_one(self):
        dim = RegimeDimension(
            dimension=RegimeDimensionType.RISK_APPETITE,
            probabilities={"low": 0.8, "medium": 0.5, "high": 0.2},
        )
        errors = dim.validate()
        assert any("sum to" in e for e in errors)

    def test_normalize_distribution(self):
        probs = {"a": 0.2, "b": 0.3, "c": 0.5}
        normalized = normalize_distribution(probs)
        total = sum(normalized.values())
        assert abs(total - 1.0) < 0.01

    def test_normalize_zero_total(self):
        result = normalize_distribution({})
        assert result == {}

    def test_dominant_state(self):
        dim = RegimeDimension(
            dimension=RegimeDimensionType.TREND,
            probabilities={"uptrend": 0.7, "downtrend": 0.2, "sideways": 0.1},
        )
        assert dim.dominant_state == "uptrend"

    def test_dominant_state_empty(self):
        dim = RegimeDimension(
            dimension=RegimeDimensionType.TREND,
            probabilities={},
        )
        assert dim.dominant_state is None


class TestRegimeSnapshot:
    def test_create_snapshot(self):
        dim = RegimeDimension(
            dimension=RegimeDimensionType.VOLATILITY,
            probabilities={"low": 0.3, "medium": 0.5, "high": 0.2},
        )
        snap = RegimeSnapshot(
            regime_id="reg_001",
            as_of_time="2024-01-01T00:00:00Z",
            dimensions={"volatility": dim},
        )
        assert snap.regime_id == "reg_001"
        assert "volatility" in snap.dimensions

    def test_missing_dimensions_reported(self):
        snap = RegimeSnapshot(
            regime_id="reg_001",
            as_of_time="2024-01-01T00:00:00Z",
            dimensions={},
        )
        missing = snap.missing_dimensions
        assert len(missing) > 0
        assert "volatility" in missing

    def test_dict_conversion(self):
        dim = RegimeDimension(
            dimension=RegimeDimensionType.VOLATILITY,
            probabilities={"low": 0.5, "high": 0.5},
        )
        snap = RegimeSnapshot(
            regime_id="reg_001",
            as_of_time="2024-01-01T00:00:00Z",
            dimensions={"volatility": dim},
        )
        # Dict init should work
        snap2 = RegimeSnapshot(**snap.to_dict())
        assert snap2.regime_id == snap.regime_id


class TestNormalize:
    def test_normalize_preserves_ratios(self):
        orig = {"a": 2.0, "b": 3.0, "c": 5.0}
        result = normalize_distribution(orig)
        assert abs(result["a"] - 0.2) < 0.01
        assert abs(result["b"] - 0.3) < 0.01
        assert abs(result["c"] - 0.5) < 0.01

    def test_normalize_rounds_to_4_decimals(self):
        result = normalize_distribution({"a": 1, "b": 1, "c": 1})
        for v in result.values():
            assert len(str(v).split(".")[1]) <= 4
