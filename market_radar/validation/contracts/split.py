"""
Split contract — time series partitioning definitions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .common import SplitMethod, TimeInterval


@dataclass(frozen=True)
class SplitFold:
    """A single fold in a split."""

    fold_id: str
    train_interval: TimeInterval
    validation_interval: Optional[TimeInterval] = None
    test_interval: Optional[TimeInterval] = None

    embargo_before: Optional[datetime] = None
    embargo_after: Optional[datetime] = None
    purge_before: Optional[datetime] = None
    purge_after: Optional[datetime] = None


@dataclass(frozen=True)
class SplitSpecification:
    """Specification for how to partition the time series."""

    split_id: str
    method: SplitMethod

    train_start: datetime
    train_end: datetime
    validation_start: Optional[datetime] = None
    validation_end: Optional[datetime] = None
    test_start: Optional[datetime] = None
    test_end: Optional[datetime] = None

    n_folds: int = 1
    window_size: Optional[str] = None  # e.g. "90d"
    step_size: Optional[str] = None  # e.g. "30d"
    purge_window: Optional[str] = None  # e.g. "24h"
    embargo: Optional[str] = None  # e.g. "48h"

    group_columns: list[str] = field(default_factory=list)  # e.g. ["event_cluster_id"]


@dataclass(frozen=True)
class WalkForwardSpecification:
    """Specification for walk-forward cross-validation."""

    experiment_id: str
    n_folds: int
    train_window: Optional[str] = None  # e.g. "180d", or None for expanding
    validation_window: str = "30d"
    step_size: str = "30d"
    purge_window: Optional[str] = None
    embargo: Optional[str] = None
    expand_training: bool = True


@dataclass
class WalkForwardFold:
    """A single fold in the walk-forward process."""

    fold_id: str
    train_start: datetime
    train_end: datetime
    validation_start: datetime
    validation_end: datetime
    test_start: Optional[datetime] = None
    test_end: Optional[datetime] = None
    fit_data_fingerprint: str = ""
    evaluation_data_fingerprint: str = ""
    parameters_before: dict = field(default_factory=dict)
    parameters_selected: dict = field(default_factory=dict)
    selection_metric: str = ""
    predictions_ref: str = ""
    metrics_ref: str = ""
