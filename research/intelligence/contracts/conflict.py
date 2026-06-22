"""ClaimConflict — a detected conflict between two or more claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from research.intelligence.contracts.common import (
    ConflictType,
    ResolutionStatus,
    generate_id,
)
from research.intelligence.contracts.errors import conflict_type_invalid


@dataclass
class ClaimConflict:
    """A conflict (contradiction / tension) detected between claims."""

    conflict_id: str = field(default_factory=lambda: generate_id("CF"))
    left_claim_id: str = ""
    right_claim_id: str = ""
    conflict_type: ConflictType = ConflictType.APPARENT_CONFLICT
    shared_question: str = ""
    difference_summary: str = ""
    sample_difference: str = ""
    method_difference: str = ""
    measurement_difference: str = ""
    regime_difference: str = ""
    current_resolution: str = ""
    resolution_status: ResolutionStatus = ResolutionStatus.UNRESOLVED
    required_research: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.conflict_id:
            errors.append("conflict_id is required")

        if not self.left_claim_id:
            errors.append("left_claim_id is required")

        if not self.right_claim_id:
            errors.append("right_claim_id is required")

        if self.left_claim_id == self.right_claim_id:
            errors.append("left_claim_id and right_claim_id must be different")

        if not isinstance(self.conflict_type, ConflictType):
            errors.append(str(conflict_type_invalid(self.conflict_id)))

        if not isinstance(self.resolution_status, ResolutionStatus):
            errors.append("resolution_status must be a ResolutionStatus enum")

        return errors
