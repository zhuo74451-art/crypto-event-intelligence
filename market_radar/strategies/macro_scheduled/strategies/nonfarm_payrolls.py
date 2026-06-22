"""NFP Strategy — Interprets the Employment Situation Report."""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from market_radar.strategies.macro_scheduled.contracts.strategy_input import EventInput
from market_radar.strategies.macro_scheduled.contracts.strategy_output import (
    MacroAssessmentProposal, StrategyLifecycleState,
)
from market_radar.strategies.macro_scheduled.contracts.abstention import AbstentionDecision, AbstentionReason
from market_radar.strategies.macro_scheduled.contracts.surprise import MacroSurprise
from market_radar.strategies.macro_scheduled.engines.surprise_engine import SurpriseEngine
from market_radar.strategies.macro_scheduled.engines.component_interpreter import ComponentInterpreter
from market_radar.strategies.macro_scheduled.engines.macro_regime_adapter import MacroRegimeAdapter
from market_radar.strategies.macro_scheduled.engines.transmission_builder import TransmissionBuilder
from market_radar.strategies.macro_scheduled.engines.market_confirmation import MarketConfirmationEngine
from market_radar.strategies.macro_scheduled.engines.hypothesis_builder import HypothesisBuilder
from market_radar.strategies.macro_scheduled.engines.assessment_builder import AssessmentBuilder
from market_radar.strategies.macro_scheduled.engines.abstention_engine import AbstentionEngine
from market_radar.domains.macro.taxonomy.event_types import EventFamily, EventComponent


class NonfarmPayrollsStrategy:
    def __init__(self, strategy_version: str = "macro_scheduled_strategy_v1.0.0"):
        self.strategy_version = strategy_version
        self.surprise_engine = SurpriseEngine()
        self.component_interpreter = ComponentInterpreter()
        self.regime_adapter = MacroRegimeAdapter()
        self.transmission_builder = TransmissionBuilder()
        self.confirmation_engine = MarketConfirmationEngine()
        self.hypothesis_builder = HypothesisBuilder()
        self.assessment_builder = AssessmentBuilder()
        self.abstention_engine = AbstentionEngine()

    def run(self, event: EventInput) -> MacroAssessmentProposal | AbstentionDecision:
        abstention = self.abstention_engine.evaluate_abstention(
            event.calendar, event.expectations, event.actual_releases
        )
        if abstention.should_abstain:
            return abstention

        expectations = event.expectations[0] if event.expectations else None
        actuals = event.actual_releases[0] if event.actual_releases else None

        computed_surprises = {}
        for act in event.actual_releases:
            exp = None
            if event.expectations:
                exp = event.expectations[0]
            cs = self.surprise_engine.compute_component_surprise(
                act.component_id, act.actual_value,
                exp.expected_value if exp else None
            )
            computed_surprises[act.component_id] = cs

        composite = self.surprise_engine.compute_composite_surprise(list(computed_surprises.values()))
        macro_surprise = MacroSurprise(
            release_event_id=event.calendar.calendar_event_id,
            component_surprises={k: v for k, v in computed_surprises.items()},
            composite=composite,
            computed_at=datetime.utcnow().isoformat(),
        )

        regime = self.regime_adapter.build_regime_context()
        transmission = self.transmission_builder.build_transmission_paths(
            EventFamily.NONFARM_PAYROLLS, composite.primary_direction.value if composite.primary_direction else "neutral"
        )
        confirmation = self.confirmation_engine.build_confirmation_snapshot({}, None)
        horizons = self.hypothesis_builder.build_horizon_assessments(
            composite, regime, transmission, confirmation
        )
        proposal = self.assessment_builder.build_proposal(
            proposal_id=f"nfp_{event.calendar.calendar_event_id}",
            release_event_id=event.calendar.calendar_event_id,
            as_of_time=datetime.utcnow(),
            surprise=macro_surprise,
            regime=regime,
            transmission=transmission,
            confirmation=confirmation,
            horizons=horizons,
        )
        return proposal
