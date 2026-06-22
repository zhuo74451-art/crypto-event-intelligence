"""Market assessment contracts — the final output of the intelligence kernel."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .common import ContractBase
from .calibration import ConfidenceStatement


class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    VOLATILITY_UP = "volatility_up"
    VOLATILITY_DOWN = "volatility_down"
    NEUTRAL = "neutral"
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    INVALIDATED = "invalidated"


class OverallStatus(str, Enum):
    ACTIONABLE = "actionable"
    WATCHING = "watching"
    INSUFFICIENT = "insufficient"
    INVALIDATED = "invalidated"


class ActionGuidance(str, Enum):
    OBSERVE = "observe"
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"
    RISK_BIAS_UP = "risk_bias_up"
    RISK_BIAS_DOWN = "risk_bias_down"
    AVOID_CHASING = "avoid_chasing"
    MONITOR_INVALIDATION = "monitor_invalidation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class HorizonDirectionAssessment(ContractBase):
    """Directional assessment for a single time horizon."""
    contract_name: str = "HorizonDirectionAssessment"
    schema_version: str = "1.0.0"

    horizon: str = ""
    direction: Direction = Direction.NEUTRAL
    state: str = ""
    eligible_strategies: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    opposing_evidence: list[str] = field(default_factory=list)
    market_confirmation: str = ""
    priced_in_status: str = ""
    crowding_status: str = ""
    alternative_explanations: list[str] = field(default_factory=list)
    invalidation_conditions: list[str] = field(default_factory=list)
    confidence_statement: Optional[ConfidenceStatement] = None

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.direction, str):
            self.direction = Direction(self.direction)
        if isinstance(self.confidence_statement, dict):
            self.confidence_statement = ConfidenceStatement(**self.confidence_statement)

    def validate(self) -> list[str]:
        errors = []
        if self.direction in (Direction.BULLISH, Direction.BEARISH,
                              Direction.VOLATILITY_UP, Direction.VOLATILITY_DOWN):
            if not self.alternative_explanations:
                errors.append("Directional assessment must have at least one alternative explanation")
            if not self.invalidation_conditions:
                errors.append("Directional assessment must have invalidation conditions")
            if self.confidence_statement:
                if self.confidence_statement.confidence_type == "calibrated_probability":
                    cal_errors = self.confidence_statement.validate()
                    errors.extend(cal_errors)
        return errors


@dataclass
class MarketAssessment(ContractBase):
    """The final market assessment — combines all intelligence layers."""
    contract_name: str = "MarketAssessment"
    schema_version: str = "1.0.0"

    assessment_id: str = ""
    event: dict = field(default_factory=dict)
    evidence_state: dict = field(default_factory=dict)
    event_state: dict = field(default_factory=dict)
    regime_state: dict = field(default_factory=dict)
    expectation_gap: dict = field(default_factory=dict)
    transmission_summary: dict = field(default_factory=dict)

    horizon_assessments: list[HorizonDirectionAssessment] = field(default_factory=list)

    overall_status: OverallStatus = OverallStatus.INSUFFICIENT
    action_guidance: ActionGuidance = ActionGuidance.INSUFFICIENT_EVIDENCE
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.overall_status, str):
            self.overall_status = OverallStatus(self.overall_status)
        if isinstance(self.action_guidance, str):
            self.action_guidance = ActionGuidance(self.action_guidance)
        if self.horizon_assessments:
            converted = []
            for h in self.horizon_assessments:
                if isinstance(h, dict):
                    converted.append(HorizonDirectionAssessment(**h))
                else:
                    converted.append(h)
            self.horizon_assessments = converted
