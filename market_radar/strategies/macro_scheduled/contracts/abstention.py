from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class AbstentionReason(str, Enum):
    EXPECTATION_MISSING = "expectation_missing"
    EXPECTATION_RECONSTRUCTED_ONLY = "expectation_reconstructed_only"
    EXPECTATION_CONFLICTING = "expectation_conflicting"
    OFFICIAL_RESULT_UNVERIFIED = "official_result_unverified"
    COMPONENT_CONFLICT_UNRESOLVED = "component_conflict_unresolved"
    MAJOR_CONCURRENT_EVENT = "major_concurrent_event"
    REGIME_UNKNOWN = "regime_unknown"
    MARKET_DATA_MISSING = "market_data_missing"
    MARKET_CONFIRMATION_CONFLICTING = "market_confirmation_conflicting"
    REACTION_ALREADY_REVERSED = "reaction_already_reversed"
    PRICED_IN_UNKNOWN = "priced_in_unknown"
    DATA_REVISION_RISK = "data_revision_risk"
    SOURCE_DEPENDENCE = "source_dependence"


@dataclass(frozen=True)
class AbstentionDecision:
    should_abstain: bool
    reasons: List[AbstentionReason] = field(default_factory=list)
    details: str = ""
