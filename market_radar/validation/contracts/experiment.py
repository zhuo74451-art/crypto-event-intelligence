"""
Experiment contract — experiment specification and registration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import (
    ExperimentStatus,
    SplitMethod,
    MultipleTestingMethod,
    ExperimentStatus,
)


@dataclass(frozen=True)
class ExperimentSpecification:
    """Frozen specification for a validation experiment."""

    experiment_id: str
    experiment_version: str
    created_at: datetime

    research_question: str = ""
    hypothesis_id: str = ""
    strategy_candidate_id: str = ""

    dataset_id: str = ""
    prediction_target: str = ""
    time_horizons: list[str] = field(default_factory=list)

    feature_set: list[str] = field(default_factory=list)
    label_set: list[str] = field(default_factory=list)
    baseline_set: list[str] = field(default_factory=list)

    split_method: SplitMethod = SplitMethod.CHRONOLOGICAL_HOLDOUT
    purge_policy: str = ""
    embargo_policy: str = ""

    primary_metrics: list[str] = field(default_factory=list)
    secondary_metrics: list[str] = field(default_factory=list)
    calibration_metrics: list[str] = field(default_factory=list)
    abstention_metrics: list[str] = field(default_factory=list)

    parameter_space: dict = field(default_factory=dict)
    selection_method: str = ""
    maximum_trials: int = 100

    multiple_testing_family: str = ""
    promotion_criteria: str = ""
    rejection_criteria: str = ""

    seed: int = 42
    environment: str = ""


@dataclass(frozen=True)
class ExperimentRegistration:
    """Complete experiment registration including execution context."""

    spec: ExperimentSpecification
    status: ExperimentStatus = ExperimentStatus.DRAFT

    data_fingerprint: str = ""
    code_sha: str = ""
    python_version: str = ""
    dependency_hash: str = ""

    random_seed: int = 42

    input_artifact_paths: list[str] = field(default_factory=list)
    output_artifact_paths: list[str] = field(default_factory=list)

    stdout_summary: str = ""
    stderr_summary: str = ""
    failure_reason: str = ""
    goal_mode_used: bool = False

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    machine_summary: str = ""


@dataclass(frozen=True)
class TrialRecord:
    """A single parameter trial in an experiment."""

    trial_id: str
    parameters: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    status: str = "pending"  # pending / running / completed / failed
    failure_reason: str = ""


@dataclass(frozen=True)
class ReproducibilityManifest:
    """Manifest for reproducing an experiment."""

    experiment_id: str
    code_sha: str
    python_version: str
    platform: str
    dependency_lock_hash: str
    dataset_fingerprint: str
    configuration_hash: str
    random_seed: int
    command: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
