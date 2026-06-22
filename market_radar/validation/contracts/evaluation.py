"""
Evaluation and metric contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import (
    MultipleTestingMethod,
    BootstrapMethod,
    DataAvailabilityLevel,
    PredictionIncrement,
    CalibrationQuality,
    RegimeStability,
    PromotionRecommendation,
)


@dataclass(frozen=True)
class MetricValue:
    """A single computed metric value with optional confidence interval."""

    name: str
    value: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    n_samples: int = 0
    method: str = ""


@dataclass(frozen=True)
class ClassMetrics:
    accuracy: Optional[MetricValue] = None
    balanced_accuracy: Optional[MetricValue] = None
    precision: Optional[MetricValue] = None
    recall: Optional[MetricValue] = None
    f1: Optional[MetricValue] = None
    confusion_matrix: Optional[list[list[int]]] = None
    macro_f1: Optional[MetricValue] = None
    weighted_f1: Optional[MetricValue] = None
    per_class_recall: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ProbabilisticMetrics:
    brier_score: Optional[MetricValue] = None
    log_loss: Optional[MetricValue] = None


@dataclass(frozen=True)
class CalibrationMetrics:
    expected_calibration_error: Optional[MetricValue] = None
    maximum_calibration_error: Optional[MetricValue] = None
    calibration_slope: Optional[float] = None
    calibration_intercept: Optional[float] = None
    reliability_bins: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class AbstentionMetrics:
    coverage: float = 0.0
    abstention_rate: float = 0.0
    selective_accuracy: Optional[MetricValue] = None
    selective_brier_score: Optional[MetricValue] = None
    error_rate_at_coverage: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class RegimeSlice:
    regime_name: str
    n_samples: int
    class_metrics: Optional[ClassMetrics] = None
    prob_metrics: Optional[ProbabilisticMetrics] = None
    calibration_metrics: Optional[CalibrationMetrics] = None
    abstention_metrics: Optional[AbstentionMetrics] = None
    prediction_interval: Optional[str] = None


@dataclass(frozen=True)
class BootstrapResult:
    method: BootstrapMethod
    n_iterations: int
    seed: int
    metric_values: list[float] = field(default_factory=list)
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    std_error: float = 0.0


@dataclass(frozen=True)
class MultipleTestingResult:
    method: MultipleTestingMethod
    n_comparisons: int
    p_values: list[float] = field(default_factory=list)
    adjusted_p_values: list[float] = field(default_factory=list)
    significant_at_05: list[bool] = field(default_factory=list)


@dataclass(frozen=True)
class RobustnessResult:
    parameter: str
    variations: list[dict] = field(default_factory=list)
    stability: str = "unknown"  # stable / unstable / unknown


@dataclass(frozen=True)
class EvaluationResult:
    data_availability: DataAvailabilityLevel = DataAvailabilityLevel.INSUFFICIENT
    prediction_increment: PredictionIncrement = PredictionIncrement.NONE
    calibration_quality: CalibrationQuality = CalibrationQuality.NOT_AVAILABLE
    regime_stability: RegimeStability = RegimeStability.UNKNOWN
    promotion: PromotionRecommendation = PromotionRecommendation.REJECT
