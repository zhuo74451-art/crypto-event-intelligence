"""KnowledgeGap — an identified gap in the research coverage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from research.intelligence.contracts.common import GapStatus, Priority, generate_id
from research.intelligence.contracts.errors import knowledge_gap_duplicate


@dataclass
class KnowledgeGap:
    """A gap in knowledge that has been identified during research."""

    gap_id: str = field(default_factory=lambda: generate_id("KG"))
    question: str = ""
    domains: list[str] = field(default_factory=list)
    why_it_matters: str = ""
    current_knowns: list[str] = field(default_factory=list)
    current_unknowns: list[str] = field(default_factory=list)
    conflicting_claims: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
    missing_method: list[str] = field(default_factory=list)
    affected_strategies: list[str] = field(default_factory=list)
    priority: Priority = Priority.P3
    status: GapStatus = GapStatus.OPEN
    next_minimal_research_action: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.gap_id:
            errors.append("gap_id is required")

        if not self.question:
            errors.append("question is required")

        if not isinstance(self.status, GapStatus):
            errors.append("status must be a GapStatus enum")

        if not isinstance(self.priority, Priority):
            errors.append("priority must be a Priority enum")

        return errors
