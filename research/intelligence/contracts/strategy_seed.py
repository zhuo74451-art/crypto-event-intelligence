"""StrategySeed — an early-stage research idea for a trading strategy."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from research.intelligence.contracts.common import (
    OriginType,
    StrategySeedStatus,
    generate_id,
)


@dataclass
class StrategySeed:
    """An early-stage research idea (seed) for a potential trading strategy."""

    strategy_seed_id: str = field(default_factory=lambda: generate_id("SS"))
    name: str = ""
    version: str = ""
    origin_type: OriginType = OriginType.INTERNAL
    origin_refs: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    counter_claim_ids: list[str] = field(default_factory=list)
    strategy_family: str = ""
    domains: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    time_horizons: list[str] = field(default_factory=list)
    regime_scope: list[str] = field(default_factory=list)
    thesis: str = ""
    information_edge: str = ""
    causal_mechanism: str = ""
    required_inputs: list[str] = field(default_factory=list)
    optional_inputs: list[str] = field(default_factory=list)
    context_conditions: list[str] = field(default_factory=list)
    trigger_conditions: list[str] = field(default_factory=list)
    confirmation_conditions: list[str] = field(default_factory=list)
    bullish_logic: str = ""
    bearish_logic: str = ""
    neutral_logic: str = ""
    abstention_logic: str = ""
    priced_in_method: str = ""
    crowding_method: str = ""
    transmission_hypothesis: str = ""
    invalidation_conditions: list[str] = field(default_factory=list)
    expiry_conditions: list[str] = field(default_factory=list)
    known_failure_modes: list[str] = field(default_factory=list)
    counterexamples: list[str] = field(default_factory=list)
    data_requirements: list[str] = field(default_factory=list)
    label_requirements: list[str] = field(default_factory=list)
    point_in_time_requirements: list[str] = field(default_factory=list)
    validation_requirements: list[str] = field(default_factory=list)
    source_verification_status: str = ""
    research_status: StrategySeedStatus = StrategySeedStatus.UNVERIFIED
    production_eligible: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.strategy_seed_id:
            errors.append("strategy_seed_id is required")

        if not self.name:
            errors.append("name is required")

        if not isinstance(self.origin_type, OriginType):
            errors.append("origin_type must be an OriginType enum")

        if not isinstance(self.research_status, StrategySeedStatus):
            errors.append("research_status must be a StrategySeedStatus enum")

        return errors
