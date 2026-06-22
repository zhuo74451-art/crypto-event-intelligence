"""CoverageDomain — a named domain of research coverage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from research.intelligence.contracts.common import CoverageLevel, Priority, generate_id


@dataclass
class CoverageDomain:
    """Describes how well a particular topic / domain is covered by research."""

    domain_id: str = field(default_factory=lambda: generate_id("CD"))
    name: str = ""
    scope: str = ""
    included_questions: list[str] = field(default_factory=list)
    excluded_questions: list[str] = field(default_factory=list)
    key_entities: list[str] = field(default_factory=list)
    key_data_types: list[str] = field(default_factory=list)
    common_failure_modes: list[str] = field(default_factory=list)
    minimum_evidence_types: list[str] = field(default_factory=list)
    current_coverage_level: CoverageLevel = CoverageLevel.L0_ABSENT
    coverage_reasons: str = ""
    priority: Priority = Priority.P3
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.domain_id:
            errors.append("domain_id is required")

        if not self.name:
            errors.append("name is required")

        if not isinstance(self.current_coverage_level, CoverageLevel):
            errors.append("current_coverage_level must be a CoverageLevel enum")

        if not isinstance(self.priority, Priority):
            errors.append("priority must be a Priority enum")

        return errors
