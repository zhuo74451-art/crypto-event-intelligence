"""KnowledgeDecayRecord — tracks when research knowledge has decayed / gone stale."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from research.intelligence.contracts.common import DecayRisk, generate_id
from research.intelligence.contracts.errors import decay_trigger_missing


@dataclass
class KnowledgeDecayRecord:
    """A record of knowledge decay for a particular source, claim or domain."""

    decay_id: str = field(default_factory=lambda: generate_id("KD"))
    claim_ids: list[str] = field(default_factory=list)
    strategy_seed_ids: list[str] = field(default_factory=list)
    original_market_structure: str = ""
    original_data_period: str = ""
    applicable_regimes: list[str] = field(default_factory=list)
    structural_change: str = ""
    decay_risk: DecayRisk = DecayRisk.UNKNOWN
    last_validated_at: datetime | None = None
    revalidation_trigger: str = ""
    status: str = "monitored"
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate(self) -> list[str]:
        """Run validation rules and return a list of error messages (empty = valid)."""
        errors: list[str] = []

        if not self.decay_id:
            errors.append("decay_id is required")

        if not self.revalidation_trigger:
            errors.append(str(decay_trigger_missing(self.decay_id)))

        if not isinstance(self.decay_risk, DecayRisk):
            errors.append("decay_risk must be a DecayRisk enum")

        return errors
