from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import Dict, List, Optional
from market_radar.strategies.macro_scheduled.contracts.strategy_input import EventInput
from market_radar.strategies.macro_scheduled.contracts.strategy_output import MacroAssessmentProposal
from market_radar.strategies.macro_scheduled.contracts.abstention import AbstentionDecision
from market_radar.strategies.macro_scheduled.engines.macro_regime_adapter import MacroRegimeAdapter
from market_radar.strategies.macro_scheduled.engines.hypothesis_builder import HypothesisBuilder
from market_radar.strategies.macro_scheduled.engines.assessment_builder import AssessmentBuilder
from market_radar.strategies.macro_scheduled.engines.abstention_engine import AbstentionEngine


@dataclass(frozen=True)
class StatementDiffEvidence:
    prior_hash: str = ""
    current_hash: str = ""
    paragraphs_added: List[str] = field(default_factory=list)
    paragraphs_removed: List[str] = field(default_factory=list)
    keyword_changes: Dict[str, str] = field(default_factory=dict)
    negation_changes: List[str] = field(default_factory=list)
    forward_guidance_changes: List[str] = field(default_factory=list)
    potentially_hawkish: List[str] = field(default_factory=list)
    potentially_dovish: List[str] = field(default_factory=list)
    ambiguous_changes: List[str] = field(default_factory=list)


class FomcStatementStrategy:
    HAWKISH = ["tighten", "inflation risk", "upside risks", "further increase"]
    DOVISH = ["ease", "disinflation", "downside risks", "hold steady", "patient"]

    def __init__(self, strategy_version: str = "macro_scheduled_strategy_v1.0.0"):
        self.version = strategy_version
        self.regime_adapter = MacroRegimeAdapter()
        self.hypothesis_builder = HypothesisBuilder()
        self.assessment_builder = AssessmentBuilder()
        self.abstention_engine = AbstentionEngine()

    def compute_statement_diff(self, prior, current):
        if prior is None or current is None:
            return StatementDiffEvidence()
        ph = sha256(prior.encode()).hexdigest()[:16]
        ch = sha256(current.encode()).hexdigest()[:16]
        if ph == ch:
            return StatementDiffEvidence(prior_hash=ph, current_hash=ch)
        hawkish, dovish = [], []
        lp, lc = prior.lower(), current.lower()
        for kw in self.HAWKISH:
            if kw in lc and kw not in lp: hawkish.append(kw)
            if kw in lp and kw not in lc: dovish.append(kw)
        for kw in self.DOVISH:
            if kw in lc and kw not in lp: dovish.append(kw)
            if kw in lp and kw not in lc: hawkish.append(kw)
        kc = {}
        for k in hawkish: kc[k] = "added_hawkish"
        for k in dovish: kc[k] = "removed_dovish"
        return StatementDiffEvidence(prior_hash=ph, current_hash=ch, keyword_changes=kc, potentially_hawkish=hawkish, potentially_dovish=dovish)

    def run(self, event, prior_statement=None):
        abstention = self.abstention_engine.evaluate_abstention(event.calendar, event.expectations, event.actual_releases)
        if abstention.should_abstain:
            return abstention
        curr = event.actual_releases[0].source_document_ref if event.actual_releases else None
        diff = self.compute_statement_diff(prior_statement, curr)
        regime = self.regime_adapter.build_regime_context()
        horizons = self.hypothesis_builder.build_horizon_assessments(regime=regime)
        return self.assessment_builder.build_proposal(
            proposal_id=f"stmt_{event.calendar.calendar_event_id}",
            release_event_id=event.calendar.calendar_event_id,
            as_of_time=datetime.utcnow(),
            regime=regime, horizons=horizons,
        )
