"""Tests for market assessment builder."""

import pytest
from market_radar.intelligence.contracts.assessment import (
    MarketAssessment, HorizonDirectionAssessment,
    Direction, OverallStatus, ActionGuidance,
)
from market_radar.intelligence.contracts.calibration import (
    ConfidenceStatement, ConfidenceType, CalibrationArtifactRef,
)
from market_radar.intelligence.engines.assessment_builder import AssessmentBuilderV1


class TestAssessmentBuilder:
    def test_build_basic_assessment(self):
        builder = AssessmentBuilderV1()
        ha = builder.make_horizon(
            horizon="short_term",
            direction=Direction.BULLISH,
            alternative_explanations=["Alternative scenario A"],
            invalidation_conditions=["Regime shift"],
        )
        assessment = builder.build(
            assessment_id="asm_001",
            event={},
            evidence_state={},
            event_state={},
            regime_state={},
            expectation_gap={},
            transmission_summary={},
            horizon_assessments=[ha],
        )
        assert assessment.assessment_id == "asm_001"
        assert assessment.overall_status == OverallStatus.ACTIONABLE

    def test_insufficient_evidence_no_strong_direction(self):
        builder = AssessmentBuilderV1()
        ha = builder.make_horizon(
            horizon="short_term",
            direction=Direction.INSUFFICIENT_EVIDENCE,
        )
        assessment = builder.build(
            assessment_id="asm_002",
            event={}, evidence_state={}, event_state={},
            regime_state={}, expectation_gap={}, transmission_summary={},
            horizon_assessments=[ha],
        )
        assert assessment.overall_status == OverallStatus.INSUFFICIENT
        assert assessment.action_guidance == ActionGuidance.INSUFFICIENT_EVIDENCE

    def test_different_horizons_separate_directions(self):
        builder = AssessmentBuilderV1()
        ha1 = builder.make_horizon(
            horizon="short_term", direction=Direction.BULLISH,
            alternative_explanations=["Alt"],
            invalidation_conditions=["Stop"],
        )
        ha2 = builder.make_horizon(
            horizon="long_term", direction=Direction.BEARISH,
            alternative_explanations=["Alt"],
            invalidation_conditions=["Stop"],
        )
        assessment = builder.build(
            assessment_id="asm_003",
            event={}, evidence_state={}, event_state={},
            regime_state={}, expectation_gap={}, transmission_summary={},
            horizon_assessments=[ha1, ha2],
        )
        assert len(assessment.horizon_assessments) == 2
        assert assessment.horizon_assessments[0].direction != assessment.horizon_assessments[1].direction

    def test_directional_must_have_alternative_explanations(self):
        ha = HorizonDirectionAssessment(
            horizon="short_term",
            direction=Direction.BULLISH,
        )
        errors = ha.validate()
        assert any("alternative" in e for e in errors)

    def test_directional_must_have_invalidation_conditions(self):
        ha = HorizonDirectionAssessment(
            horizon="short_term",
            direction=Direction.BULLISH,
            alternative_explanations=["Alt"],
        )
        errors = ha.validate()
        assert any("invalidation" in e for e in errors)

    def test_calibrated_probability_not_allowed_without_artifact(self):
        cs = ConfidenceStatement(
            confidence_type=ConfidenceType.CALIBRATED_PROBABILITY,
            value="0.75",
            probability_value=0.75,
        )
        ha = HorizonDirectionAssessment(
            horizon="short_term",
            direction=Direction.BULLISH,
            alternative_explanations=["Alt"],
            invalidation_conditions=["Stop"],
            confidence_statement=cs,
        )
        errors = ha.validate()
        assert any("artifact" in e.lower() for e in errors)

    def test_action_guidance_no_trading(self):
        builder = AssessmentBuilderV1()
        ha = builder.make_horizon(
            horizon="short_term", direction=Direction.BULLISH,
            alternative_explanations=["Alt"],
            invalidation_conditions=["Stop"],
        )
        assessment = builder.build(
            assessment_id="asm_004",
            event={}, evidence_state={}, event_state={},
            regime_state={}, expectation_gap={}, transmission_summary={},
            horizon_assessments=[ha],
        )
        assert assessment.action_guidance in (
            ActionGuidance.OBSERVE, ActionGuidance.RISK_BIAS_UP,
            ActionGuidance.RISK_BIAS_DOWN,
        )
        assert "buy" not in assessment.action_guidance.value.lower()
        assert "sell" not in assessment.action_guidance.value.lower()

    def test_serialization_round_trip(self):
        builder = AssessmentBuilderV1()
        ha = builder.make_horizon(
            horizon="short_term", direction=Direction.NEUTRAL,
        )
        assessment = builder.build(
            assessment_id="asm_005",
            event={}, evidence_state={}, event_state={},
            regime_state={}, expectation_gap={}, transmission_summary={},
            horizon_assessments=[ha],
        )
        d = assessment.to_dict()
        assert d["assessment_id"] == "asm_005"
        assert d["contract_name"] == "MarketAssessment"

    def test_multiple_time_scales_different_directions(self):
        builder = AssessmentBuilderV1()
        ha1 = builder.make_horizon("intraday", Direction.BULLISH,
                                   alternative_explanations=["A"],
                                   invalidation_conditions=["B"])
        ha2 = builder.make_horizon("long_term", Direction.BEARISH,
                                   alternative_explanations=["C"],
                                   invalidation_conditions=["D"])
        assessment = builder.build(
            assessment_id="asm_006",
            event={}, evidence_state={}, event_state={},
            regime_state={}, expectation_gap={}, transmission_summary={},
            horizon_assessments=[ha1, ha2],
        )
        assert assessment.overall_status == OverallStatus.ACTIONABLE
