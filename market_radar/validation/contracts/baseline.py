"""
Baseline contract — definition of comparison baselines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import Direction
from .prediction import PredictionRecord


@dataclass(frozen=True)
class BaselineSpecification:
    """Specification for a baseline model."""

    baseline_id: str
    name: str
    description: str
    category: str  # e.g. "neutral", "random", "event_prior", "sentiment", "momentum"
    seed: Optional[int] = None


BASELINE_NEUTRAL = BaselineSpecification(
    baseline_id="B1",
    name="Always Neutral",
    description="Always predicts flat/unknown direction with no confidence.",
    category="neutral",
)

BASELINE_RANDOM = BaselineSpecification(
    baseline_id="B2",
    name="Random Prior",
    description="Generates fixed probabilities from training set class distribution.",
    category="random",
    seed=42,
)

BASELINE_EVENT_TYPE_PRIOR = BaselineSpecification(
    baseline_id="B3",
    name="Event Type Prior",
    description="Uses historical distribution of event type outcomes.",
    category="event_prior",
    seed=42,
)

BASELINE_SENTIMENT_RULE = BaselineSpecification(
    baseline_id="B4",
    name="Simple Sentiment Rule",
    description="Uses directional sentiment from rule-based word list.",
    category="sentiment",
)

BASELINE_MOMENTUM = BaselineSpecification(
    baseline_id="B5",
    name="Price Momentum",
    description="Uses pre-event price momentum to predict direction.",
    category="momentum",
)

BASELINE_FUNDING = BaselineSpecification(
    baseline_id="B6",
    name="Funding Rule",
    description="Uses funding rate status to predict direction.",
    category="funding",
)

BASELINE_OI = BaselineSpecification(
    baseline_id="B7",
    name="OI Rule",
    description="Uses open interest change to predict direction.",
    category="oi",
)

BASELINE_MACRO_STATIC = BaselineSpecification(
    baseline_id="B8",
    name="Static Macro Rule",
    description="Uses predefined static macro direction rules.",
    category="macro",
)

BASELINE_REGIME_ONLY = BaselineSpecification(
    baseline_id="B9",
    name="Regime-only Prior",
    description="Uses only market regime (no event content).",
    category="regime",
)

BASELINE_LAST_KNOWN_RATE = BaselineSpecification(
    baseline_id="B10",
    name="Last-known Hit Rate",
    description="Uses historical event hit rate by type.",
    category="last_known_rate",
    seed=42,
)
