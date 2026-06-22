"""
Label contract — ground truth labels for validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import (
    Direction,
    VolatilityState,
    EventOutcome,
    LabelStatus,
    stable_fingerprint,
)


@dataclass(frozen=True)
class LabelMeta:
    """Metadata for a label, including maturity tracking."""

    label_status: LabelStatus = LabelStatus.IMMATURE
    matures_at: Optional[datetime] = None
    computed_at: Optional[datetime] = None
    label_source: str = ""


@dataclass(frozen=True)
class ReturnLabel:
    """Return-based label at a specific horizon."""

    event_id: str
    horizon: str  # e.g. "1h", "24h"
    raw_return: Optional[float] = None
    log_return: Optional[float] = None
    abnormal_return: Optional[float] = None
    relative_return: Optional[float] = None
    benchmark: Optional[str] = None
    meta: LabelMeta = field(default_factory=LabelMeta)


@dataclass(frozen=True)
class DirectionLabel:
    """Direction label (up/down/flat/unknown)."""

    event_id: str
    horizon: str
    direction: Direction = Direction.UNKNOWN
    flat_threshold: float = 0.0
    meta: LabelMeta = field(default_factory=LabelMeta)


@dataclass(frozen=True)
class VolatilityLabel:
    """Volatility change label."""

    event_id: str
    horizon: str
    state: VolatilityState = VolatilityState.UNKNOWN
    meta: LabelMeta = field(default_factory=LabelMeta)


@dataclass(frozen=True)
class DrawdownLabel:
    """Risk metrics for a prediction window."""

    event_id: str
    horizon: str
    max_drawdown: Optional[float] = None
    max_favorable_excursion: Optional[float] = None
    max_adverse_excursion: Optional[float] = None
    reversal: Optional[bool] = None
    continuation: Optional[bool] = None
    meta: LabelMeta = field(default_factory=LabelMeta)


@dataclass(frozen=True)
class EventOutcomeLabel:
    """Event outcome label (for scheduled events like rate decisions)."""

    event_id: str
    outcome: EventOutcome = EventOutcome.UNKNOWN
    meta: LabelMeta = field(default_factory=LabelMeta)
