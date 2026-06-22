from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from market_radar.strategies.macro_scheduled.contracts.strategy_output import (
    MacroAssessmentProposal, StrategyOutput, StrategyLifecycleState,
    HorizonAssessment, AssessmentDirection,
)
from market_radar.strategies.macro_scheduled.contracts.surprise import MacroSurprise
from market_radar.strategies.macro_scheduled.contracts.regime_context import RegimeContext
from market_radar.strategies.macro_scheduled.contracts.transmission import TransmissionPath
from market_radar.strategies.macro_scheduled.contracts.confirmation import MarketConfirmationSnapshot
from market_radar.strategies.macro_scheduled.contracts.pricing import PricedInEstimate, CrowdingAssessment
from market_radar.strategies.macro_scheduled.contracts.abstention import AbstentionDecision


class AssessmentBuilder:
    @staticmethod
    def build_proposal(proposal_id, release_event_id, as_of_time,
                       surprise=None, regime=None, transmission=None,
                       confirmation=None, priced_in=None, crowding=None,
                       horizons=None, abstention=None,
                       expectation_quality="insufficient"):
        horizon_list = horizons or []
        overall = AssessmentBuilder._determine_overall_status(horizon_list, abstention)
        limitations = AssessmentBuilder._collect_limitations(surprise, regime, confirmation, priced_in, crowding)
        return MacroAssessmentProposal(
            proposal_id=proposal_id,
            release_event_id=release_event_id,
            as_of_time=as_of_time,
            release_summary=AssessmentBuilder._build_summary(surprise, horizon_list),
            expectation_quality=expectation_quality,
            surprise_summary=surprise,
            component_conflicts=[],
            regime_context=regime,
            transmission_paths=transmission or [],
            market_confirmation=confirmation,
            priced_in_status=priced_in,
            crowding_status=crowding,
            horizon_assessments=horizon_list,
            overall_status=overall,
            abstention_reason=abstention,
            limitations=limitations,
            validation_record=AssessmentBuilder._build_validation_record(proposal_id, release_event_id, as_of_time),
        )

    @staticmethod
    def _determine_overall_status(horizons, abstention=None):
        if abstention and abstention.should_abstain:
            return StrategyLifecycleState.INSUFFICIENT_EXPECTATION
        if not horizons:
            return StrategyLifecycleState.SCHEDULED
        states = [h.state for h in horizons]
        if StrategyLifecycleState.CONFIRMED in states:
            return StrategyLifecycleState.CONFIRMED
        if StrategyLifecycleState.MIXED in states:
            return StrategyLifecycleState.MIXED
        if StrategyLifecycleState.INVALIDATED in states:
            return StrategyLifecycleState.INVALIDATED
        if StrategyLifecycleState.INSUFFICIENT_MARKET_DATA in states:
            return StrategyLifecycleState.INSUFFICIENT_MARKET_DATA
        return StrategyLifecycleState.AWAITING_MARKET_CONFIRMATION

    @staticmethod
    def _collect_limitations(surprise=None, regime=None, confirmation=None, priced_in=None, crowding=None):
        limits = []
        if surprise and hasattr(surprise, 'limitations'):
            limits.extend(surprise.limitations)
        if regime and hasattr(regime, 'limitations'):
            limits.extend(regime.limitations)
        if confirmation and hasattr(confirmation, 'limitations'):
            limits.extend(confirmation.limitations)
        if priced_in and hasattr(priced_in, 'limitations'):
            limits.extend(priced_in.limitations)
        if crowding and hasattr(crowding, 'limitations'):
            limits.extend(crowding.limitations)
        return limits

    @staticmethod
    def _build_summary(surprise, horizons):
        parts = []
        if surprise:
            parts.append(f"Surprise computed for {surprise.release_event_id}")
        for h in horizons:
            parts.append(f"{h.horizon}: {h.direction.value}")
        return " | ".join(parts) if parts else "No assessment available"

    @staticmethod
    def _build_validation_record(proposal_id, release_event_id, as_of_time):
        return {
            "proposal_id": proposal_id,
            "release_event_id": release_event_id,
            "as_of_time": as_of_time.isoformat() if hasattr(as_of_time, 'isoformat') else str(as_of_time),
            "prediction_as_of_time": as_of_time.isoformat() if hasattr(as_of_time, 'isoformat') else str(as_of_time),
        }
