"""
Prediction contract — model output representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import ConfidenceType


@dataclass(frozen=True)
class PredictionRecord:
    """A single prediction made by a model or baseline."""

    prediction_id: str
    experiment_id: str
    event_id: str
    as_of_time: datetime
    horizon: str

    predicted_direction: str  # "up" / "down" / "flat" / "unknown"
    confidence_score: Optional[float] = None  # raw score
    calibrated_probability: Optional[float] = None  # after calibration
    confidence_type: ConfidenceType = ConfidenceType.UNCALIBRATED_SCORE

    model_id: str = ""
    fold_id: str = ""
    features_hash: str = ""

    # Abstention
    is_abstained: bool = False
    abstention_reason: Optional[str] = None


@dataclass(frozen=True)
class PredictionSet:
    """A collection of predictions from one model for one experiment."""

    model_id: str
    experiment_id: str
    predictions: list[PredictionRecord] = field(default_factory=list)
    fingerprint: str = ""
    created_at: Optional[datetime] = None
