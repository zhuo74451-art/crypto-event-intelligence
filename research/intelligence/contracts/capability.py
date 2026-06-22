"""Capability — a specific analytical or operational capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from research.intelligence.contracts.common import generate_id


@dataclass
class Capability:
    """A named capability that the research system or a strategy possesses."""

    capability_id: str = field(default_factory=lambda: generate_id("CA"))
    name: str = ""
    definition: str = ""
    required_inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    common_confusions: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    example_claim_ids: list[str] = field(default_factory=list)
    example_strategy_seed_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.capability_id:
            errors.append("capability_id is required")

        if not self.name:
            errors.append("name is required")

        if not self.definition:
            errors.append("definition is required")

        return errors
