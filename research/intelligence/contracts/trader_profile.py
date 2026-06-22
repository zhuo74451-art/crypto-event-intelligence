"""TraderProfile — a researched profile of a trader or trading entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from research.intelligence.contracts.common import (
    QualityRating,
    TraderVerificationStatus,
    generate_id,
)
from research.intelligence.contracts.errors import trader_source_unverified


@dataclass
class TraderProfile:
    """A compiled profile about a trader or trading entity derived from research."""

    trader_profile_id: str = field(default_factory=lambda: generate_id("TP"))
    display_name: str = ""
    public_identity_status: str = ""
    source_record_ids: list[str] = field(default_factory=list)
    markets: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    time_horizons: list[str] = field(default_factory=list)
    strategy_families: list[str] = field(default_factory=list)
    observed_capabilities: list[str] = field(default_factory=list)
    observed_inputs: list[str] = field(default_factory=list)
    observed_triggers: list[str] = field(default_factory=list)
    observed_confirmations: list[str] = field(default_factory=list)
    observed_invalidations: list[str] = field(default_factory=list)
    observed_risk_controls: list[str] = field(default_factory=list)
    public_claims: list[str] = field(default_factory=list)
    contradictory_claims: list[str] = field(default_factory=list)
    unverified_performance_claims: list[str] = field(default_factory=list)
    source_verification_status: TraderVerificationStatus = TraderVerificationStatus.UNVERIFIED
    provenance_quality: str = ""
    coverage_period: str = ""
    known_selection_bias: str = ""
    known_survivorship_bias: str = ""
    production_eligible: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.trader_profile_id:
            errors.append("trader_profile_id is required")

        if not self.display_name:
            errors.append("display_name is required")

        if not isinstance(self.source_verification_status, TraderVerificationStatus):
            errors.append("source_verification_status must be a TraderVerificationStatus enum")

        return errors
