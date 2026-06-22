from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ConfirmationStatus(str, Enum):
    CONFIRMING = "confirming"
    CONTRADICTING = "contradicting"
    MIXED = "mixed"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class ConfirmationChannel:
    channel: str
    status: ConfirmationStatus
    value: Optional[float] = None
    direction: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class MarketConfirmationSnapshot:
    channels: Dict[str, ConfirmationChannel] = field(default_factory=dict)
    overall_status: ConfirmationStatus = ConfirmationStatus.MISSING
    has_spot_confirmation: bool = False
    has_derivatives_only: bool = False
    contradictory_channels: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
