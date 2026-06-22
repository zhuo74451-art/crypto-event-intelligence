from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class PricedInStatus(str, Enum):
    UNDERPRICED = "underpriced"
    PARTIALLY_PRICED = "partially_priced"
    LARGELY_PRICED = "largely_priced"
    OVERPRICED_OR_CROWDED = "overpriced_or_crowded"
    UNKNOWN = "unknown"


class CrowdingStatus(str, Enum):
    CROWDED_LONG = "crowded_long"
    CROWDED_SHORT = "crowded_short"
    BALANCED = "balanced"
    DELEVERAGING = "deleveraging"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PricedInEstimate:
    status: PricedInStatus = PricedInStatus.UNKNOWN
    reasons: List[str] = field(default_factory=list)
    missing_inputs: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CrowdingAssessment:
    status: CrowdingStatus = CrowdingStatus.UNKNOWN
    reasons: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
