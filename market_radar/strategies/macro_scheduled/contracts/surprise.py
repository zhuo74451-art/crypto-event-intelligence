from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class StandardizationStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    INSUFFICIENT_SAMPLE = "insufficient_sample"


class DirectionalInterpretation(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    VOLATILITY_UP = "volatility_up"
    VOLATILITY_DOWN = "volatility_down"
    NEUTRAL = "neutral"
    AMBIGUOUS = "ambiguous"
    EVENT_SPECIFIC = "event_specific"


@dataclass(frozen=True)
class ComponentSurprise:
    component_id: str
    actual_value: Optional[float]
    expected_value: Optional[float]
    raw_gap: Optional[float]
    relative_gap: Optional[float]
    standardized_gap: Optional[float]
    standardization_status: StandardizationStatus = StandardizationStatus.UNAVAILABLE
    sign: Optional[str] = None  # "above", "below", "inline"


@dataclass(frozen=True)
class CompositeSurpriseContext:
    components: Dict[str, ComponentSurprise] = field(default_factory=dict)
    has_conflict: bool = False
    primary_direction: Optional[DirectionalInterpretation] = None


@dataclass(frozen=True)
class MacroSurprise:
    release_event_id: str
    component_surprises: Dict[str, ComponentSurprise] = field(default_factory=dict)
    composite: Optional[CompositeSurpriseContext] = None
    computed_at: Optional[str] = None
    limitations: List[str] = field(default_factory=list)
