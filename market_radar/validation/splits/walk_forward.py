"""
Walk-forward engine — executes walk-forward validation across folds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from ..contracts.split import WalkForwardSpecification, WalkForwardFold
from ..contracts.common import stable_fingerprint


@dataclass
class WalkForwardResult:
    """Aggregated result from a walk-forward validation run."""

    spec: WalkForwardSpecification
    folds: list[WalkForwardFold] = field(default_factory=list)
    aggregated_metrics: dict[str, float] = field(default_factory=dict)
    fold_metrics: list[dict[str, float]] = field(default_factory=list)
    fingerprint: str = ""

    def __post_init__(self):
        if not self.fingerprint:
            self.fingerprint = self._compute_fingerprint()

    def _compute_fingerprint(self) -> str:
        data = {
            "experiment_id": self.spec.experiment_id,
            "n_folds": self.spec.n_folds,
            "n_folds_completed": len(self.folds),
        }
        return stable_fingerprint(data)


class WalkForwardRunner:
    """Executes walk-forward validation.

    Each fold:
    1. Trains on the training window.
    2. Validates on the validation window (parameter selection).
    3. Evaluates on the test window.
    """

    def __init__(self, spec: WalkForwardSpecification):
        self.spec = spec
        self._results: list[WalkForwardFold] = []

    def _parse_duration(self, duration_str: str) -> timedelta:
        import re

        match = re.match(r"(\d+)([dhms])", duration_str)
        if not match:
            raise ValueError(f"Cannot parse duration: {duration_str}")
        value = int(match.group(1))
        unit = match.group(2)
        if unit == "d":
            return timedelta(days=value)
        elif unit == "h":
            return timedelta(hours=value)
        elif unit == "m":
            return timedelta(minutes=value)
        elif unit == "s":
            return timedelta(seconds=value)
        raise ValueError(f"Unknown duration unit: {unit}")

    def run(
        self,
        train_fn: Callable[..., dict[str, Any]],
        predict_fn: Callable[..., Any],
        available_times: list[datetime],
    ) -> WalkForwardResult:
        """Run walk-forward validation.

        Args:
            train_fn: Function that accepts (train_times, fold_params) and returns fitted parameters.
            predict_fn: Function that accepts (trained_params, test_times) and returns predictions.
            available_times: All available timestamps sorted.
        """
        sorted_times = sorted(available_times)
        total = len(sorted_times)
        step_delta = self._parse_duration(self.spec.step_size)
        val_delta = self._parse_duration(self.spec.validation_window)
        train_window = self._parse_duration(self.spec.train_window) if self.spec.train_window else None
        purge_delta = self._parse_duration(self.spec.purge_window) if self.spec.purge_window else timedelta(0)
        embargo_delta = self._parse_duration(self.spec.embargo) if self.spec.embargo else timedelta(0)

        start_time = sorted_times[0] if sorted_times else datetime.now()
        # Build folds
        current = start_time
        fold_idx = 0
        accumulated_folds = []

        while fold_idx < self.spec.n_folds and current < sorted_times[-1]:
            if self.spec.expand_training and train_window is None:
                train_start = start_time
            elif train_window:
                train_start = current - train_window
            else:
                train_start = current - step_delta * 3  # default: 3 steps

            train_end = current
            val_start = train_end + embargo_delta
            val_end = val_start + val_delta
            test_start = val_end + purge_delta
            test_end = test_start + step_delta

            if test_start > sorted_times[-1]:
                break

            fold = WalkForwardFold(
                fold_id=f"wf_fold_{fold_idx}",
                train_start=train_start,
                train_end=train_end,
                validation_start=val_start,
                validation_end=val_end,
                test_start=test_start,
                test_end=test_end,
            )

            # Train
            train_times = [t for t in sorted_times if train_start <= t <= train_end]
            params = train_fn(train_times, {"fold_id": fold.fold_id})
            fold.parameters_selected = params

            accumulated_folds.append(fold)
            current += step_delta
            fold_idx += 1

        result = WalkForwardResult(
            spec=self.spec,
            folds=accumulated_folds,
        )
        return result
