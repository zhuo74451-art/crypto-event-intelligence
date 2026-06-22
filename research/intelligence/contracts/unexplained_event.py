"""UnexplainedEvent — an event that cannot yet be explained by existing research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from research.intelligence.contracts.common import UnexplainedEventStatus, generate_id


@dataclass
class UnexplainedEvent:
    """An event that has been detected but cannot (yet) be explained by our research."""

    unexplained_event_id: str = field(default_factory=lambda: generate_id("UE"))
    event_time: datetime | None = None
    description: str = ""
    assets: list[str] = field(default_factory=list)
    observed_market_move: str = ""
    expected_move: str = ""
    prediction_source: str = ""
    magnitude: str = ""
    known_concurrent_events: list[str] = field(default_factory=list)
    data_quality_checks: list[str] = field(default_factory=list)
    candidate_explanations: list[str] = field(default_factory=list)
    rejected_explanations: list[str] = field(default_factory=list)
    related_claims: list[str] = field(default_factory=list)
    related_strategy_seeds: list[str] = field(default_factory=list)
    research_status: UnexplainedEventStatus = UnexplainedEventStatus.OPEN
    next_action: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.unexplained_event_id:
            errors.append("unexplained_event_id is required")

        if not self.description:
            errors.append("description is required")

        if not isinstance(self.research_status, UnexplainedEventStatus):
            errors.append("research_status must be an UnexplainedEventStatus enum")

        return errors
