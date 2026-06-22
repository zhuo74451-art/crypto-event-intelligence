"""ResearchHypothesis — a testable hypothesis derived from research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from research.intelligence.contracts.common import (
    HypothesisStatus,
    generate_id,
)
from research.intelligence.contracts.errors import (
    hypothesis_leakage_risk_missing,
    hypothesis_not_testable,
)


@dataclass
class ResearchHypothesis:
    """A testable hypothesis formed from research findings and claims."""

    hypothesis_id: str = field(default_factory=lambda: generate_id("HY"))
    statement: str = ""
    domains: list[str] = field(default_factory=list)
    affected_assets: list[str] = field(default_factory=list)
    time_horizon: str = ""
    regime_scope: list[str] = field(default_factory=list)
    supporting_claim_ids: list[str] = field(default_factory=list)
    opposing_claim_ids: list[str] = field(default_factory=list)
    knowledge_gap_ids: list[str] = field(default_factory=list)
    required_inputs: list[str] = field(default_factory=list)
    required_labels: list[str] = field(default_factory=list)
    expected_direction: str = ""
    null_hypothesis: str = ""
    alternative_hypotheses: list[str] = field(default_factory=list)
    minimum_sample: str = ""
    point_in_time_requirements: list[str] = field(default_factory=list)
    leakage_risks: list[str] = field(default_factory=list)
    baseline_models: list[str] = field(default_factory=list)
    validation_method: str = ""
    promotion_criteria: str = ""
    rejection_criteria: str = ""
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.hypothesis_id:
            errors.append("hypothesis_id is required")

        if not self.statement:
            errors.append("statement is required")

        if not self.leakage_risks:
            errors.append(str(hypothesis_leakage_risk_missing(self.hypothesis_id)))

        if not self.validation_method:
            errors.append("validation_method is required")

        if not isinstance(self.status, HypothesisStatus):
            errors.append("status must be a HypothesisStatus enum")

        return errors
