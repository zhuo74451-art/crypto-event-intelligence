"""
Report contract — evaluation report structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .evaluation import (
    ClassMetrics,
    ProbabilisticMetrics,
    CalibrationMetrics,
    AbstentionMetrics,
    RegimeSlice,
    BootstrapResult,
    MultipleTestingResult,
    RobustnessResult,
)
from .common import PromotionRecommendation


@dataclass(frozen=True)
class ExperimentReport:
    """Complete experiment report."""

    experiment_identity: dict = field(default_factory=dict)
    data_identity: dict = field(default_factory=dict)
    code_identity: dict = field(default_factory=dict)

    split_summary: dict = field(default_factory=dict)
    sample_summary: dict = field(default_factory=dict)

    baseline_results: dict[str, ClassMetrics] = field(default_factory=dict)
    candidate_results: dict[str, ClassMetrics] = field(default_factory=dict)

    metric_intervals: list[dict] = field(default_factory=list)

    calibration: Optional[CalibrationMetrics] = None
    abstention: Optional[AbstentionMetrics] = None
    regime_slices: list[RegimeSlice] = field(default_factory=list)

    multiple_testing: Optional[MultipleTestingResult] = None
    robustness: list[RobustnessResult] = field(default_factory=list)

    known_limitations: list[str] = field(default_factory=list)
    promotion_recommendation: str = "reject"
