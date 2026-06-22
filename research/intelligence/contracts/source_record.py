"""ResearchSourceRecord — provenance of a research source."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from research.intelligence.contracts.common import (
    AccessType,
    OriginType,
    ProvenanceStatus,
    QualityRating,
    RedistributionStatus,
    SourceRole,
    generate_id,
)


@dataclass
class ResearchSourceRecord:
    """Metadata about a raw information source used in research."""

    source_record_id: str = field(default_factory=lambda: generate_id("SR"))
    title: str = ""
    authors: list[str] = field(default_factory=list)
    organization: str = ""
    publication_type: str = ""
    publication_date: datetime | None = None
    retrieved_at: datetime | None = None
    url: str = ""
    doi: str = ""
    repository: str = ""
    upstream_commit: str = ""
    domains: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    time_horizons: list[str] = field(default_factory=list)
    access_type: AccessType = AccessType.UNKNOWN
    license: str = ""
    redistribution_status: RedistributionStatus = RedistributionStatus.UNKNOWN
    full_text_stored: bool = False
    stored_content_scope: str = ""
    source_role: SourceRole = SourceRole.INDUSTRY_RESEARCH
    primary_or_secondary: str = ""
    author_incentives: str = ""
    known_biases: list[str] = field(default_factory=list)
    quality_notes: str = ""
    provenance_status: ProvenanceStatus = ProvenanceStatus.UNVERIFIED
    schema_version: str = "research_intelligence_v1"
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.source_record_id:
            errors.append("source_record_id is required")

        if not self.title:
            errors.append("title is required")

        if not isinstance(self.access_type, AccessType):
            errors.append("access_type must be an AccessType enum")

        if not isinstance(self.source_role, SourceRole):
            errors.append("source_role must be a SourceRole enum")

        if not isinstance(self.redistribution_status, RedistributionStatus):
            errors.append("redistribution_status must be a RedistributionStatus enum")

        if not isinstance(self.provenance_status, ProvenanceStatus):
            errors.append("provenance_status must be a ProvenanceStatus enum")

        return errors
