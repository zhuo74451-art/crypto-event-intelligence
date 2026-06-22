from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from market_radar.domains.macro.taxonomy.transmission_channels import TransmissionEdge


class TransmissionStatus(str, Enum):
    ACTIVE = "active"
    CONDITIONAL = "conditional"
    BLOCKED = "blocked"
    INVALIDATED = "invalidated"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class TransmissionPath:
    name: str
    edges: List[TransmissionEdge] = field(default_factory=list)
    status: TransmissionStatus = TransmissionStatus.UNKNOWN
    primary_sign: Optional[str] = None
    blocking_conditions: List[str] = field(default_factory=list)
    invalidation_reason: Optional[str] = None
