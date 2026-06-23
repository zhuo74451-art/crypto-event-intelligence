"""Validation, walk-forward, and calibration contracts.

This package provides the type-safe contracts and implementations for
the Lane D validation pipeline.
"""

from .contracts import (
    ValidationDatasetV1,
    SplitManifestV1,
    WalkforwardFoldV1,
    StrategyEvaluationV1,
    BaselineEvaluationV1,
    CalibrationArtifactV1,
    FailureExperimentV1,
    LeakageAuditV1,
    StatisticalEvidenceV1,
)
from .dataset_builder import DatasetBuilder
from .dependency_graph import DependencyGraph
from .splitter import ChronologicalSplitter
from .walkforward import WalkforwardExecutor
from .baselines import BaselineRunner
from .bootstrap import BootstrapEngine
from .multiple_testing import MultipleTestingAdjuster
from .calibration import CalibrationFitter
from .abstention_analysis import AbstentionAnalyzer
from .drift_analysis import DriftAnalyzer
from .leakage_audit import LeakageAuditor

__all__ = [
    "ValidationDatasetV1",
    "SplitManifestV1",
    "WalkforwardFoldV1",
    "StrategyEvaluationV1",
    "BaselineEvaluationV1",
    "CalibrationArtifactV1",
    "FailureExperimentV1",
    "LeakageAuditV1",
    "StatisticalEvidenceV1",
    "DatasetBuilder",
    "DependencyGraph",
    "ChronologicalSplitter",
    "WalkforwardExecutor",
    "BaselineRunner",
    "BootstrapEngine",
    "MultipleTestingAdjuster",
    "CalibrationFitter",
    "AbstentionAnalyzer",
    "DriftAnalyzer",
    "LeakageAuditor",
]
