"""
Calibration contract — calibration artifact and protocol definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import CalibrationMethod, ConfidenceType, stable_fingerprint
from .evaluation import CalibrationMetrics


@dataclass(frozen=True)
class CalibrationArtifact:
    """A saved calibration mapping from scores to calibrated probabilities."""

    calibration_artifact_id: str
    method: CalibrationMethod
    created_at: datetime

    model_id: str = ""
    strategy_candidate_id: str = ""
    dataset_id: str = ""
    fit_period: str = ""

    sample_size: int = 0
    input_score_type: str = "raw_score"
    output_probability_type: str = "probability"

    parameters: dict = field(default_factory=dict)
    metrics_before: Optional[CalibrationMetrics] = None
    metrics_after: Optional[CalibrationMetrics] = None
    out_of_sample_evaluation: Optional[CalibrationMetrics] = None

    artifact_fingerprint: str = ""

    def __post_init__(self):
        if not self.artifact_fingerprint:
            object.__setattr__(self, "artifact_fingerprint", self._compute_fingerprint())

    def _compute_fingerprint(self) -> str:
        data = {
            "calibration_artifact_id": self.calibration_artifact_id,
            "method": self.method.value,
            "model_id": self.model_id,
            "dataset_id": self.dataset_id,
            "fit_period": self.fit_period,
        }
        return stable_fingerprint(data)
