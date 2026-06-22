"""ResearchClaim — a factual or analytical statement with provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from research.intelligence.contracts.common import (
    ClaimStatus,
    ClaimType,
    QualityRating,
    generate_id,
)
from research.intelligence.contracts.errors import (
    claim_method_missing,
    claim_period_missing,
    claim_without_source,
)


@dataclass
class ResearchClaim:
    """A claim derived from one or more research sources."""

    claim_id: str = field(default_factory=lambda: generate_id("CL"))
    claim_text: str = ""
    claim_type: ClaimType = ClaimType.DESCRIPTIVE_CLAIM
    domains: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    markets: list[str] = field(default_factory=list)
    time_horizons: list[str] = field(default_factory=list)
    regimes: list[str] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)
    primary_source_record_id: str = ""
    mechanism: str = ""
    causal_chain: str = ""
    required_conditions: list[str] = field(default_factory=list)
    boundary_conditions: list[str] = field(default_factory=list)
    data_period: str = ""
    sample_size: str = ""
    methodology: str = ""
    supporting_evidence: list[str] = field(default_factory=list)
    counter_evidence: list[str] = field(default_factory=list)
    null_evidence: list[str] = field(default_factory=list)
    effect_direction: str = ""
    effect_size: str = ""
    quality: QualityRating = QualityRating.UNKNOWN
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.claim_id:
            errors.append("claim_id is required")

        if not self.claim_text:
            errors.append("claim_text is required")

        if self.claim_type in (ClaimType.EMPIRICAL_RELATIONSHIP, ClaimType.CAUSAL_CLAIM):
            if not self.methodology:
                errors.append(str(claim_method_missing(self.claim_id)))
            if not self.data_period:
                errors.append(str(claim_period_missing(self.claim_id)))

        if not self.source_record_ids and not self.primary_source_record_id:
            errors.append(str(claim_without_source(self.claim_id)))

        if not isinstance(self.claim_type, ClaimType):
            errors.append("claim_type must be a ClaimType enum")

        if not isinstance(self.status, ClaimStatus):
            errors.append("status must be a ClaimStatus enum")

        if not isinstance(self.quality, QualityRating):
            errors.append("quality must be a QualityRating enum")

        return errors
