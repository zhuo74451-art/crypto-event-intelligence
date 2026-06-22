"""Tests for calibration and confidence guards."""

import pytest
from market_radar.intelligence.contracts.calibration import (
    ConfidenceStatement, ConfidenceType, CalibrationArtifactRef,
    CalibratorProtocol, NoCalibrationAvailable,
)


class TestCalibratedProbability:
    def test_valid_calibrated(self):
        cal = CalibrationArtifactRef(
            calibration_artifact_id="cal_001",
            calibration_method="isotonic",
            validation_period="2024-2025",
            sample_size=200,
            out_of_sample=True,
            metric_summary="Brier=0.12",
        )
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.CALIBRATED_PROBABILITY,
            value="0.75",
            probability_value=0.75,
            calibration_artifact=cal,
        )
        assert cs.validate() == []

    def test_calibrated_without_artifact_returns_errors(self):
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.CALIBRATED_PROBABILITY,
            value="0.75",
            probability_value=0.75,
        )
        errors = cs.validate()
        assert len(errors) > 0
        assert any("artifact" in e.lower() for e in errors)

    def test_calibrated_without_artifact_id(self):
        cal = CalibrationArtifactRef(
            calibration_artifact_id="",
            calibration_method="test",
            validation_period="2024",
            sample_size=100,
            out_of_sample=True,
            metric_summary="",
        )
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.CALIBRATED_PROBABILITY,
            value="0.75",
            probability_value=0.75,
            calibration_artifact=cal,
        )
        errors = cs.validate()
        assert any("artifact ID" in e for e in errors)

    def test_calibrated_zero_sample_size(self):
        cal = CalibrationArtifactRef(
            calibration_artifact_id="cal_001",
            calibration_method="test",
            validation_period="2024",
            sample_size=0,
            out_of_sample=True,
            metric_summary="",
        )
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.CALIBRATED_PROBABILITY,
            value="0.75",
            probability_value=0.75,
            calibration_artifact=cal,
        )
        errors = cs.validate()
        assert any("sample_size" in e for e in errors)

    def test_calibrated_not_out_of_sample(self):
        cal = CalibrationArtifactRef(
            calibration_artifact_id="cal_001",
            calibration_method="test",
            validation_period="2024",
            sample_size=100,
            out_of_sample=False,
            metric_summary="",
        )
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.CALIBRATED_PROBABILITY,
            value="0.75",
            probability_value=0.75,
            calibration_artifact=cal,
        )
        errors = cs.validate()
        assert any("out_of_sample" in e for e in errors)


class TestUncalibratedScore:
    def test_uncalibrated_with_production_false(self):
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
            value="0.75",
            probability_value=0.75,
            production_probability=False,
        )
        assert cs.validate() == []

    def test_uncalibrated_missing_production_flag(self):
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
            value="0.75",
            probability_value=0.75,
        )
        errors = cs.validate()
        assert any("production_probability" in e for e in errors)

    def test_uncalibrated_cannot_be_production(self):
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
            value="0.75",
            probability_value=0.75,
            production_probability=True,
        )
        errors = cs.validate()
        assert any("production_probability=True" in e for e in errors)


class TestQualitative:
    def test_qualitative_with_basis(self):
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.QUALITATIVE,
            value="high",
            basis="Two independent primary sources confirm",
        )
        assert cs.validate() == []

    def test_qualitative_without_basis(self):
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.QUALITATIVE,
            value="medium",
        )
        errors = cs.validate()
        assert any("basis" in e for e in errors)


class TestNoCalibration:
    def test_no_calibration_available(self):
        nca = NoCalibrationAvailable()
        assert "No calibration artifact" in nca.reason
