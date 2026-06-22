from __future__ import annotations
from typing import List, Optional
from market_radar.strategies.macro_scheduled.contracts.strategy_output import (
    HorizonAssessment, AssessmentDirection, StrategyLifecycleState,
)
from market_radar.strategies.macro_scheduled.contracts.surprise import (
    CompositeSurpriseContext, DirectionalInterpretation,
)
from market_radar.strategies.macro_scheduled.contracts.regime_context import RegimeContext
from market_radar.strategies.macro_scheduled.contracts.transmission import TransmissionPath, TransmissionStatus
from market_radar.strategies.macro_scheduled.contracts.confirmation import MarketConfirmationSnapshot, ConfirmationStatus
from market_radar.strategies.macro_scheduled.contracts.pricing import PricedInEstimate, PricedInStatus


class HypothesisBuilder:
    HORIZONS = ["intraday_0_4h", "short_term_1_3d", "swing_3_14d", "medium_term_1_3m"]

    @staticmethod
    def build_horizon_assessments(surprise: Optional[CompositeSurpriseContext] = None,
                                    regime: Optional[RegimeContext] = None,
                                    transmission: Optional[List[TransmissionPath]] = None,
                                    confirmation: Optional[MarketConfirmationSnapshot] = None,
                                    priced_in: Optional[PricedInEstimate] = None) -> List[HorizonAssessment]:
        results: List[HorizonAssessment] = []
        results.append(HypothesisBuilder._assess_intraday(surprise, confirmation))
        results.append(HypothesisBuilder._assess_short_term(transmission, confirmation, priced_in))
        results.append(HypothesisBuilder._assess_swing(regime, transmission, priced_in))
        results.append(HypothesisBuilder._assess_medium_term(regime, transmission))
        return results

    @staticmethod
    def _direction_from_surprise(surprise: Optional[CompositeSurpriseContext]) -> AssessmentDirection:
        if surprise is None or surprise.primary_direction is None:
            return AssessmentDirection.INSUFFICIENT_EVIDENCE
        mapping = {
            DirectionalInterpretation.BULLISH: AssessmentDirection.BULLISH,
            DirectionalInterpretation.BEARISH: AssessmentDirection.BEARISH,
            DirectionalInterpretation.VOLATILITY_UP: AssessmentDirection.VOLATILITY_UP,
            DirectionalInterpretation.VOLATILITY_DOWN: AssessmentDirection.VOLATILITY_DOWN,
            DirectionalInterpretation.NEUTRAL: AssessmentDirection.NEUTRAL,
            DirectionalInterpretation.AMBIGUOUS: AssessmentDirection.WAIT_FOR_CONFIRMATION,
            DirectionalInterpretation.EVENT_SPECIFIC: AssessmentDirection.WAIT_FOR_CONFIRMATION,
        }
        return mapping.get(surprise.primary_direction, AssessmentDirection.INSUFFICIENT_EVIDENCE)

    @staticmethod
    def _assess_intraday(surprise: Optional[CompositeSurpriseContext],
                          confirmation: Optional[MarketConfirmationSnapshot]) -> HorizonAssessment:
        direction = HypothesisBuilder._direction_from_surprise(surprise)
        state = StrategyLifecycleState.SURPRISE_COMPUTED
        supporting: List[str] = []
        contradicting: List[str] = []
        if confirmation:
            if confirmation.has_spot_confirmation:
                state = StrategyLifecycleState.CONFIRMED
                supporting.append("spot_market")
            if confirmation.has_derivatives_only:
                state = StrategyLifecycleState.MIXED
                supporting.append("derivatives_only")
            if confirmation.contradictory_channels:
                contradicting = confirmation.contradictory_channels
        return HorizonAssessment(
            horizon="intraday_0_4h",
            direction=direction,
            state=state,
            supporting_channels=supporting,
            contradicting_channels=contradicting,
            invalidation_conditions=["Rapid reversal within 1 hour", "Conflicting cross-asset signals"],
        )

    @staticmethod
    def _assess_short_term(transmission: Optional[List[TransmissionPath]],
                            confirmation: Optional[MarketConfirmationSnapshot],
                            priced_in: Optional[PricedInEstimate]) -> HorizonAssessment:
        direction = AssessmentDirection.WAIT_FOR_CONFIRMATION
        state = StrategyLifecycleState.AWAITING_MARKET_CONFIRMATION
        supporting: List[str] = []
        contradictions: List[str] = []
        if confirmation and confirmation.overall_status == ConfirmationStatus.CONFIRMING:
            state = StrategyLifecycleState.CONFIRMED
            supporting = [k for k, v in confirmation.channels.items() if v.status == ConfirmationStatus.CONFIRMING]
            contradictions = confirmation.contradictory_channels
        if priced_in and priced_in.status == PricedInStatus.LARGELY_PRICED:
            direction = AssessmentDirection.NEUTRAL
        if not contradictions:
            if confirmation and confirmation.has_spot_confirmation:
                direction = AssessmentDirection.BULLISH
        return HorizonAssessment(
            horizon="short_term_1_3d",
            direction=direction,
            state=state,
            supporting_channels=supporting,
            contradicting_channels=contradictions,
            invalidation_conditions=["Full reversal", "Regime shift"],
        )

    @staticmethod
    def _assess_swing(regime: Optional[RegimeContext],
                       transmission: Optional[List[TransmissionPath]],
                       priced_in: Optional[PricedInEstimate]) -> HorizonAssessment:
        direction = AssessmentDirection.NEUTRAL
        if regime and regime.quality.value in ("strong", "moderate"):
            direction = AssessmentDirection.BULLISH
        return HorizonAssessment(
            horizon="swing_3_14d",
            direction=direction,
            state=StrategyLifecycleState.EXPECTATION_CAPTURED,
            invalidation_conditions=["Regime change", "Unexpected policy shift"],
        )

    @staticmethod
    def _assess_medium_term(regime: Optional[RegimeContext],
                             transmission: Optional[List[TransmissionPath]]) -> HorizonAssessment:
        return HorizonAssessment(
            horizon="medium_term_1_3m",
            direction=AssessmentDirection.NEUTRAL,
            state=StrategyLifecycleState.SCHEDULED,
            invalidation_conditions=["Major regime shift", "Structural change in policy framework"],
        )
