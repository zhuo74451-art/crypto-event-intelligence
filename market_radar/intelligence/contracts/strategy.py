"""Strategy contracts — Strategy Pack, Strategy Instance, and lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .common import ContractBase


class StrategyInstanceState(str, Enum):
    INACTIVE = "inactive"
    WATCHING = "watching"
    TRIGGERED = "triggered"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    WEAKENED = "weakened"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"


@dataclass
class StrategyOrigin(ContractBase):
    """Origin metadata for a strategy."""
    contract_name: str = "StrategyOrigin"
    schema_version: str = "1.0.0"

    origin_type: str = "internal"
    source_refs: list[str] = field(default_factory=list)


@dataclass
class StrategyPack(ContractBase):
    """A strategy pack — the reusable strategy definition.

    A Strategy Pack is NOT a persona agent, NOT a simple factor function.
    It is a structured trading/research strategy with explicit logic for
    each possible direction, plus invalidation conditions.
    """
    contract_name: str = "StrategyPack"
    schema_version: str = "1.0.0"

    strategy_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    origin: StrategyOrigin = field(default_factory=StrategyOrigin)
    strategy_family: str = ""
    market_domains: list[str] = field(default_factory=list)
    applicable_assets: list[str] = field(default_factory=list)
    time_horizons: list[str] = field(default_factory=list)

    thesis: str = ""
    information_edge: str = ""

    required_inputs: list[str] = field(default_factory=list)
    optional_inputs: list[str] = field(default_factory=list)

    valid_regimes: list[str] = field(default_factory=list)
    invalid_regimes: list[str] = field(default_factory=list)
    regime_adjustments: dict[str, Any] = field(default_factory=dict)

    context_conditions: list[str] = field(default_factory=list)
    trigger_conditions: list[str] = field(default_factory=list)
    confirmation_conditions: list[str] = field(default_factory=list)

    bullish_logic: str = ""
    bearish_logic: str = ""
    neutral_logic: str = ""
    abstention_logic: str = ""

    priced_in_method: str = ""
    crowding_method: str = ""
    transmission_template: str = ""

    invalidation_conditions: list[str] = field(default_factory=list)
    expiry_conditions: list[str] = field(default_factory=list)
    known_failure_modes: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)

    historical_validation_status: str = "unverified"
    shadow_validation_status: str = "unverified"
    calibration_status: str = "uncalibrated"

    def validate(self) -> list[str]:
        """Validate that the strategy pack meets minimum requirements."""
        errors = []
        if not self.abstention_logic:
            errors.append("Missing abstention_logic — every strategy must define when to abstain")
        if not self.invalidation_conditions:
            errors.append("Missing invalidation_conditions — every strategy must define when invalidated")
        if not self.strategy_id:
            errors.append("Missing strategy_id")
        if not self.name:
            errors.append("Missing name")
        return errors


@dataclass
class InstanceTransition(ContractBase):
    """A transition in a strategy instance's lifecycle."""
    contract_name: str = "InstanceTransition"
    schema_version: str = "1.0.0"

    from_state: StrategyInstanceState = StrategyInstanceState.INACTIVE
    to_state: StrategyInstanceState = StrategyInstanceState.WATCHING
    transition_time: str = ""
    reason: str = ""
    evidence_refs: list[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.from_state, str):
            self.from_state = StrategyInstanceState(self.from_state)
        if isinstance(self.to_state, str):
            self.to_state = StrategyInstanceState(self.to_state)


@dataclass
class StrategyInstance(ContractBase):
    """A running instance of a strategy pack.

    Each instance tracks its own lifecycle state, evidence, and transitions.
    """
    contract_name: str = "StrategyInstance"
    schema_version: str = "1.0.0"

    instance_id: str = ""
    strategy_id: str = ""
    asset: str = ""
    time_horizon: str = ""
    state: StrategyInstanceState = StrategyInstanceState.INACTIVE
    transitions: list[InstanceTransition] = field(default_factory=list)
    current_evidence_refs: list[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.state, str):
            self.state = StrategyInstanceState(self.state)
        if self.transitions:
            converted = []
            for t in self.transitions:
                if isinstance(t, dict):
                    converted.append(InstanceTransition(**t))
                else:
                    converted.append(t)
            self.transitions = converted
