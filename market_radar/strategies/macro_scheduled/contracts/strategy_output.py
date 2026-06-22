from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from market_radar.strategies.macro_scheduled.contracts.surprise import MacroSurprise
from market_radar.strategies.macro_scheduled.contracts.regime_context import RegimeContext
from market_radar.strategies.macro_scheduled.contracts.transmission import TransmissionPath
from market_radar.strategies.macro_scheduled.contracts.confirmation import MarketConfirmationSnapshot
from market_radar.strategies.macro_scheduled.contracts.pricing import PricedInEstimate, CrowdingAssessment
from market_radar.strategies.macro_scheduled.contracts.abstention import AbstentionDecision


class AssessmentDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    VOLATILITY_UP = "volatility_up"
    VOLATILITY_DOWN = "volatility_down"
    NEUTRAL = "neutral"
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    INVALIDATED = "invalidated"


class StrategyLifecycleState(str, Enum):
    SCHEDULED = "scheduled"
    EXPECTATION_CAPTURED = "expectation_captured"
    AWAITING_RELEASE = "awaiting_release"
    RELEASED = "released"
    SURPRISE_COMPUTED = "surprise_computed"
    AWAITING_MARKET_CONFIRMATION = "awaiting_market_confirmation"
    CONFIRMED = "confirmed"
    MIXED = "mixed"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    INSUFFICIENT_EXPECTATION = "insufficient_expectation"
    INSUFFICIENT_MARKET_DATA = "insufficient_market_data"


@dataclass(frozen=True)
class HorizonAssessment:
    horizon: str
    direction: AssessmentDirection = AssessmentDirection.INSUFFICIENT_EVIDENCE
    state: StrategyLifecycleState = StrategyLifecycleState.SCHEDULED
    rationale: List[str] = field(default_factory=list)
    supporting_channels: List[str] = field(default_factory=list)
    contradicting_channels: List[str] = field(default_factory=list)
    alternative_explanations: List[str] = field(default_factory=list)
    invalidation_conditions: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class MacroAssessmentProposal:
    proposal_id: str
    release_event_id: str
    as_of_time: datetime
    release_summary: str = ""
    expectation_quality: str = "insufficient"
    official_result_quality: str = "insufficient"
    surprise_summary: Optional[MacroSurprise] = None
    component_conflicts: List[str] = field(default_factory=list)
    regime_context: Optional[RegimeContext] = None
    transmission_paths: List[TransmissionPath] = field(default_factory=list)
    market_confirmation: Optional[MarketConfirmationSnapshot] = None
    priced_in_status: Optional[PricedInEstimate] = None
    crowding_status: Optional[CrowdingAssessment] = None
    horizon_assessments: List[HorizonAssessment] = field(default_factory=list)
    overall_status: StrategyLifecycleState = StrategyLifecycleState.SCHEDULED
    abstention_reason: Optional[AbstentionDecision] = None
    limitations: List[str] = field(default_factory=list)
    validation_record: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyOutput:
    strategy_version: str
    proposals: List[MacroAssessmentProposal] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
