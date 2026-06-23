"""Validation contracts — typed data structures for the entire Lane D pipeline.

All contracts inherit from ContractBase for serialization and ID support.
P0 anti-spoofing: no probability outputs without CalibrationArtifactV1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ..contracts.common import ContractBase


class ValidationStatus(str, Enum):
    NOT_EVALUATED = "not_evaluated"
    PIPELINE_VERIFIED = "pipeline_verified"
    HISTORICAL_IN_SAMPLE_ONLY = "historical_in_sample_only"
    HISTORICAL_WALKFORWARD_MIXED = "historical_walkforward_mixed"
    HISTORICAL_WALKFORWARD_SUPPORTED = "historical_walkforward_supported"
    HOLDOUT_FAILED = "holdout_failed"
    INSUFFICIENT_SAMPLE = "insufficient_sample"
    LEAKAGE_BLOCKED = "leakage_blocked"
    CALIBRATION_UNAVAILABLE = "calibration_unavailable"
    CALIBRATION_AVAILABLE = "calibration_available"


class CalibrationMethod(str, Enum):
    ISOTONIC = "isotonic"
    PLATT_SCALING = "platt_scaling"
    EMPIRICAL_BINNING = "empirical_binning"


class SplitMethod(str, Enum):
    FIXED_TIME = "fixed_time"
    EXPANDING_WALKFORWARD = "expanding_walkforward"
    ROLLING_WALKFORWARD = "rolling_walkforward"


class DirectionLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class LeakageSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ValidationDatasetV1(object):
    """Section 11 — Point-in-Time validation dataset metadata."""
    contract_name: str = "ValidationDatasetV1"
    schema_version: str = "1.0.0"

    dataset_id: str = ""
    dataset_version: str = "1.0.0"
    generated_at_utc: str = ""

    producer_shas: dict = None

    event_count: int = 0
    event_families: list = None
    date_start: str = ""
    date_end: str = ""

    feature_cutoff_policy: str = ""
    label_availability_policy: str = ""
    point_in_time_policy: str = ""
    revision_policy: str = ""

    records_path: str = ""
    records_sha256: str = ""
    schema_path: str = ""

    quality_distribution: dict = None
    missingness_distribution: dict = None
    abstention_count: int = 0
    quarantined_count: int = 0

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.producer_shas is None:
            self.producer_shas = {}
        if self.event_families is None:
            self.event_families = []
        if self.quality_distribution is None:
            self.quality_distribution = {}
        if self.missingness_distribution is None:
            self.missingness_distribution = {}

    def to_dict(self):
        return self.__dict__


@dataclass
class SplitManifestV1(object):
    """Section 13 — Chronological split definition with purge/embargo."""
    contract_name: str = "SplitManifestV1"
    schema_version: str = "1.0.0"

    split_manifest_id: str = ""
    dataset_id: str = ""
    split_method: str = ""

    train_start: str = ""
    train_end: str = ""
    validation_start: str = ""
    validation_end: str = ""
    holdout_start: str = ""
    holdout_end: str = ""

    purge_window: str = ""
    embargo_window: str = ""

    event_family_distribution: dict = None
    regime_distribution: dict = None
    point_in_time_quality_distribution: dict = None

    overlap_checks: dict = None
    leakage_checks: dict = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.event_family_distribution is None:
            self.event_family_distribution = {}
        if self.regime_distribution is None:
            self.regime_distribution = {}
        if self.point_in_time_quality_distribution is None:
            self.point_in_time_quality_distribution = {}
        if self.overlap_checks is None:
            self.overlap_checks = {}
        if self.leakage_checks is None:
            self.leakage_checks = {}

    def to_dict(self):
        return self.__dict__


@dataclass
class WalkforwardFoldV1(object):
    """Section 13 — A single walk-forward fold."""
    contract_name: str = "WalkforwardFoldV1"
    schema_version: str = "1.0.0"

    fold_id: str = ""
    fold_index: int = 0

    train_start: str = ""
    train_end: str = ""
    validation_start: str = ""
    validation_end: str = ""
    test_start: str = ""
    test_end: str = ""

    purge_start: str = ""
    purge_end: str = ""
    embargo_start: str = ""
    embargo_end: str = ""

    train_count: int = 0
    validation_count: int = 0
    test_count: int = 0

    strategy_versions: list = None
    baseline_versions: list = None
    feature_contract_version: str = ""
    label_contract_version: str = ""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.strategy_versions is None:
            self.strategy_versions = []
        if self.baseline_versions is None:
            self.baseline_versions = []

    def to_dict(self):
        return self.__dict__


@dataclass
class StrategyEvaluationV1(object):
    """Section 16 — Per-strategy evaluation results with uncertainty."""
    contract_name: str = "StrategyEvaluationV1"
    schema_version: str = "1.0.0"

    evaluation_id: str = ""
    strategy_id: str = ""
    strategy_version: str = ""
    dataset_id: str = ""
    split_manifest_id: str = ""
    fold_ids: list = None

    coverage: float = 0.0
    abstention_rate: float = 0.0
    directional_count: int = 0

    directional_accuracy: float = None
    balanced_accuracy: float = None
    precision_positive: float = None
    precision_negative: float = None
    recall_positive: float = None
    recall_negative: float = None
    macro_f1: float = None
    mcc: float = None

    mean_signed_return: float = None
    median_signed_return: float = None
    mean_absolute_reaction: float = None
    downside_tail_reaction: float = None

    confidence_interval: dict = None
    bootstrap_method: str = ""
    sample_count: int = 0

    regime_breakdown: dict = None
    event_family_breakdown: dict = None
    horizon_breakdown: dict = None
    point_in_time_quality_breakdown: dict = None

    calibration_status: str = "unavailable"
    calibration_artifact_id: str = None
    warnings: list = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.fold_ids is None: self.fold_ids = []
        if self.regime_breakdown is None: self.regime_breakdown = {}
        if self.event_family_breakdown is None: self.event_family_breakdown = {}
        if self.horizon_breakdown is None: self.horizon_breakdown = {}
        if self.point_in_time_quality_breakdown is None: self.point_in_time_quality_breakdown = {}
        if self.warnings is None: self.warnings = []
        if self.confidence_interval is None: self.confidence_interval = {}

    def to_dict(self):
        return self.__dict__


@dataclass
class BaselineEvaluationV1(object):
    """Section 15 — Baseline evaluation result (B1-B10)."""
    contract_name: str = "BaselineEvaluationV1"
    schema_version: str = "1.0.0"

    evaluation_id: str = ""
    baseline_id: str = ""
    baseline_name: str = ""
    dataset_id: str = ""
    split_manifest_id: str = ""
    fold_ids: list = None

    coverage: float = 0.0
    abstention_rate: float = 0.0
    directional_count: int = 0

    directional_accuracy: float = None
    balanced_accuracy: float = None
    precision_positive: float = None
    precision_negative: float = None
    macro_f1: float = None
    mcc: float = None

    mean_signed_return: float = None
    median_signed_return: float = None

    warnings: list = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.fold_ids is None: self.fold_ids = []
        if self.warnings is None: self.warnings = []

    def to_dict(self):
        return self.__dict__


@dataclass
class CalibrationArtifactV1(object):
    """Section 20 — Fitted calibration artifact.

    Only generated when minimum sample requirements are met.
    """
    contract_name: str = "CalibrationArtifactV1"
    schema_version: str = "1.0.0"

    calibration_artifact_id: str = ""
    strategy_id: str = ""
    strategy_version: str = ""
    horizon: str = ""
    asset: str = ""

    method: str = ""
    fit_dataset_id: str = ""
    fit_split_ids: list = None
    fit_date_start: str = ""
    fit_date_end: str = ""

    input_confidence_type: str = ""
    output_confidence_type: str = ""

    parameters: dict = None
    bin_edges: list = None
    bin_counts: list = None
    observed_frequencies: list = None

    brier_score: float = None
    log_loss: float = None
    expected_calibration_error: float = None
    maximum_calibration_error: float = None

    minimum_sample_requirement: int = 100
    sample_count: int = 0
    applicable_regimes: list = None
    applicable_event_families: list = None

    artifact_sha256: str = ""
    generated_at_utc: str = ""
    limitations: list = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.fit_split_ids is None: self.fit_split_ids = []
        if self.parameters is None: self.parameters = {}
        if self.bin_edges is None: self.bin_edges = []
        if self.bin_counts is None: self.bin_counts = []
        if self.observed_frequencies is None: self.observed_frequencies = []
        if self.applicable_regimes is None: self.applicable_regimes = []
        if self.applicable_event_families is None: self.applicable_event_families = []
        if self.limitations is None: self.limitations = []

    def to_dict(self):
        return self.__dict__


@dataclass
class FailureExperimentV1(object):
    """Section 28 — Record of a failed or inconclusive experiment."""
    contract_name: str = "FailureExperimentV1"
    schema_version: str = "1.0.0"

    experiment_id: str = ""
    experiment_name: str = ""
    strategy_id: str = ""
    strategy_version: str = ""

    dataset_id: str = ""
    split_manifest_id: str = ""
    fold_ids: list = None

    hypothesis: str = ""
    configuration: dict = None
    result_summary: str = ""
    failure_reason: str = ""

    leakage_detected: bool = False
    overfit_suspected: bool = False
    sample_size_insufficient: bool = False
    unstable_across_folds: bool = False
    unstable_across_regimes: bool = False
    multiple_testing_adjusted: bool = False

    raw_artifact_refs: list = None
    created_at_utc: str = ""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.fold_ids is None: self.fold_ids = []
        if self.configuration is None: self.configuration = {}
        if self.raw_artifact_refs is None: self.raw_artifact_refs = []

    def to_dict(self):
        return self.__dict__


@dataclass
class LeakageAuditV1(object):
    """Section 25 — Leakage audit findings."""
    contract_name: str = "LeakageAuditV1"
    schema_version: str = "1.0.0"

    audit_id: str = ""
    dataset_id: str = ""
    split_manifest_id: str = ""

    checks: dict = None
    violations: list = None
    quarantine_refs: list = None
    passed: bool = False

    generated_at_utc: str = ""
    auditor_version: str = "1.0.0"

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.checks is None: self.checks = {}
        if self.violations is None: self.violations = []
        if self.quarantine_refs is None: self.quarantine_refs = []

    def to_dict(self):
        return self.__dict__


@dataclass
class StatisticalEvidenceV1(object):
    """Section 18-19 — Bootstrap and multiple-testing evidence."""
    contract_name: str = "StatisticalEvidenceV1"
    schema_version: str = "1.0.0"

    evidence_id: str = ""
    strategy_id: str = ""
    strategy_version: str = ""

    bootstrap_resamples: int = 0
    bootstrap_ci: dict = None
    bootstrap_method: str = ""

    raw_p_value: float = None
    adjusted_p_value: float = None
    adjustment_method: str = ""
    comparison_count: int = 0
    family_id: str = ""

    sufficient_sample: bool = False
    notes: list = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.bootstrap_ci is None: self.bootstrap_ci = {}
        if self.notes is None: self.notes = []

    def to_dict(self):
        return self.__dict__
