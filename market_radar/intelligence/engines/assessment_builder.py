"""Assessment Builder V1 — constructs final market assessments."""

from __future__ import annotations

from typing import Any, Optional

from ..contracts.assessment import (
    MarketAssessment, HorizonDirectionAssessment,
    Direction, OverallStatus, ActionGuidance,
)
from ..contracts.calibration import ConfidenceStatement, ConfidenceType
from ..errors.codes import IntelligenceError, ErrorCode


class AssessmentBuilderV1:
    """Constructs final MarketAssessment from intelligence layers.

    Rules:
    - insufficient_evidence must not include strong directional advice
    - Directional assessments must have alternative explanations
    - Directional assessments must have invalidation conditions
    - Uncalibrated confidence cannot be called calibrated
    - Multi-time-scale can have different directions
    - Missing market confirmation must be explicit
    """

    def __init__(self):
        pass

    def build(self, assessment_id: str,
              event: dict,
              evidence_state: dict,
              event_state: dict,
              regime_state: dict,
              expectation_gap: dict,
              transmission_summary: dict,
              horizon_assessments: list[HorizonDirectionAssessment],
              limitations: Optional[list[str]] = None) -> MarketAssessment:
        """Build a complete MarketAssessment from all intelligence layers.

        Validates all hard constraints before returning.
        """
        assessment = MarketAssessment(
            assessment_id=assessment_id,
            event=event,
            evidence_state=evidence_state,
            event_state=event_state,
            regime_state=regime_state,
            expectation_gap=expectation_gap,
            transmission_summary=transmission_summary,
            horizon_assessments=horizon_assessments,
            limitations=limitations or [],
        )

        # Validate each horizon
        all_insufficient = True
        for h in horizon_assessments:
            h_errors = h.validate()
            if h_errors:
                assessment.limitations.extend(h_errors)
            if h.direction not in (Direction.INSUFFICIENT_EVIDENCE, Direction.INVALIDATED):
                all_insufficient = False

        # Determine overall status
        assessment.overall_status = self._determine_overall_status(
            horizon_assessments, all_insufficient,
        )

        # Determine action guidance
        assessment.action_guidance = self._determine_action_guidance(
            assessment.overall_status, horizon_assessments,
        )

        # If insufficient evidence, ensure no strong direction
        if assessment.overall_status == OverallStatus.INSUFFICIENT:
            for h in assessment.horizon_assessments:
                if h.direction not in (
                    Direction.INSUFFICIENT_EVIDENCE, Direction.NEUTRAL,
                    Direction.INVALIDATED,
                ):
                    h.direction = Direction.INSUFFICIENT_EVIDENCE

        return assessment

    def _determine_overall_status(
        self,
        horizon_assessments: list[HorizonDirectionAssessment],
        all_insufficient: bool,
    ) -> OverallStatus:
        if all_insufficient:
            return OverallStatus.INSUFFICIENT
        for h in horizon_assessments:
            if h.direction in (
                Direction.BULLISH, Direction.BEARISH,
                Direction.VOLATILITY_UP, Direction.VOLATILITY_DOWN,
            ):
                return OverallStatus.ACTIONABLE
        return OverallStatus.WATCHING

    def _determine_action_guidance(
        self,
        status: OverallStatus,
        horizon_assessments: list[HorizonDirectionAssessment],
    ) -> ActionGuidance:
        if status == OverallStatus.INSUFFICIENT:
            return ActionGuidance.INSUFFICIENT_EVIDENCE

        for h in horizon_assessments:
            if h.direction in (Direction.BULLISH,):
                return ActionGuidance.RISK_BIAS_UP
            if h.direction in (Direction.BEARISH,):
                return ActionGuidance.RISK_BIAS_DOWN
            if h.direction == Direction.WAIT_FOR_CONFIRMATION:
                return ActionGuidance.WAIT_FOR_CONFIRMATION

        return ActionGuidance.OBSERVE

    @staticmethod
    def make_horizon(
        horizon: str,
        direction: Direction,
        state: str = "",
        eligible_strategies: Optional[list[str]] = None,
        supporting_evidence: Optional[list[str]] = None,
        opposing_evidence: Optional[list[str]] = None,
        alternative_explanations: Optional[list[str]] = None,
        invalidation_conditions: Optional[list[str]] = None,
        confidence_statement: Optional[ConfidenceStatement] = None,
    ) -> HorizonDirectionAssessment:
        """Factory method for HorizonDirectionAssessment."""
        return HorizonDirectionAssessment(
            horizon=horizon,
            direction=direction,
            state=state,
            eligible_strategies=eligible_strategies or [],
            supporting_evidence=supporting_evidence or [],
            opposing_evidence=opposing_evidence or [],
            alternative_explanations=alternative_explanations or [],
            invalidation_conditions=invalidation_conditions or [],
            confidence_statement=confidence_statement,
        )
