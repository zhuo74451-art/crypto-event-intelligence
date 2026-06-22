"""Unemployment Strategy — Interprets unemployment rate changes."""
from __future__ import annotations
from datetime import datetime
from market_radar.strategies.macro_scheduled.contracts.strategy_input import EventInput
from market_radar.strategies.macro_scheduled.contracts.strategy_output import MacroAssessmentProposal
from market_radar.strategies.macro_scheduled.contracts.abstention import AbstentionDecision
from market_radar.strategies.macro_scheduled.contracts.surprise import MacroSurprise
from market_radar.strategies.macro_scheduled.engines.surprise_engine import SurpriseEngine
from market_radar.strategies.macro_scheduled.engines.macro_regime_adapter import MacroRegimeAdapter
from market_radar.strategies.macro_scheduled.engines.transmission_builder import TransmissionBuilder
from market_radar.strategies.macro_scheduled.engines.market_confirmation import MarketConfirmationEngine
from market_radar.strategies.macro_scheduled.engines.hypothesis_builder import HypothesisBuilder
from market_radar.strategies.macro_scheduled.engines.assessment_builder import AssessmentBuilder
from market_radar.strategies.macro_scheduled.engines.abstention_engine import AbstentionEngine
from market_radar.domains.macro.taxonomy.event_types import EventFamily


class UnemploymentStrategy:
    def __init__(self, strategy_version: str = "macro_scheduled_strategy_v1.0.0"):
        self.version = strategy_version
        self.surprise_engine = SurpriseEngine()
        self.regime_adapter = MacroRegimeAdapter()
        self.confirmation_engine = MarketConfirmationEngine()
        self.hypothesis_builder = HypothesisBuilder()
        self.assessment_builder = AssessmentBuilder()
        self.abstention_engine = AbstentionEngine()

    def run(self, event: EventInput) -> MacroAssessmentProposal | AbstentionDecision:
        abstention = self.abstention_engine.evaluate_abstention(event.calendar, event.expectations, event.actual_releases)
        if abstention.should_abstain:
            return abstention
        computed = {}
        for act in event.actual_releases:
            exp = event.expectations[0] if event.expectations else None
            cs = self.surprise_engine.compute_component_surprise(act.component_id, act.actual_value, exp.expected_value if exp else None)
            computed[act.component_id] = cs
        composite = self.surprise_engine.compute_composite_surprise(list(computed.values()))
        macro_surprise = MacroSurprise(release_event_id=event.calendar.calendar_event_id, component_surprises=computed, composite=composite)
        regime = self.regime_adapter.build_regime_context()
        horizons = self.hypothesis_builder.build_horizon_assessments(composite, regime)
        proposal = self.assessment_builder.build_proposal(
            proposal_id=f"unemp_{event.calendar.calendar_event_id}",
            release_event_id=event.calendar.calendar_event_id,
            as_of_time=datetime.utcnow(),
            surprise=macro_surprise, regime=regime, horizons=horizons,
        )
        return proposal
