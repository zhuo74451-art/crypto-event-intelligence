"""
Chronological time-series split implementation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from ..contracts.split import SplitFold, SplitSpecification, TimeInterval
from ..contracts.common import SplitMethod
from ..contracts.errors import (
    TrainTestTimeOverlapError,
    PurgeWindowViolationError,
    EmbargoViolationError,
)


def parse_duration(duration_str: str) -> timedelta:
    """Parse a duration string like '90d', '24h', '30m'."""
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


class ChronologicalSplitter:
    """Splits time series chronologically without random shuffling."""

    def split(
        self,
        spec: SplitSpecification,
        timestamps: list[datetime],
    ) -> list[SplitFold]:
        """Create chronological train/validation/holdout splits."""
        sorted_times = sorted(timestamps)

        # Simple chronological split by time intervals
        fold = SplitFold(
            fold_id="fold_0",
            train_interval=TimeInterval(
                start=spec.train_start,
                end=spec.train_end,
            ),
            validation_interval=TimeInterval(
                start=spec.validation_start,
                end=spec.validation_end,
            ) if spec.validation_start else None,
            test_interval=TimeInterval(
                start=spec.test_start,
                end=spec.test_end,
            ) if spec.test_start else None,
        )

        # Apply purging
        if spec.purge_window:
            purge_delta = parse_duration(spec.purge_window)
            purge_before = spec.validation_start - purge_delta if spec.validation_start else None
            if purge_before and purge_before < spec.train_end:
                raise PurgeWindowViolationError(
                    detail=f"Purge window {spec.purge_window} extends into training period",
                    object_id=spec.split_id,
                    min_fix="Ensure purge window doesn't overlap with training",
                )

        # Apply embargo
        if spec.embargo:
            embargo_delta = parse_duration(spec.embargo)

        return [fold]


class RollingWindowSplitter:
    """Creates rolling window splits."""

    def split(self, spec: SplitSpecification) -> list[SplitFold]:
        if not spec.window_size or not spec.step_size:
            raise ValueError("Rolling window requires window_size and step_size")

        window = parse_duration(spec.window_size)
        step = parse_duration(spec.step_size)

        folds = []
        current_start = spec.train_start
        fold_idx = 0

        while current_start + window <= (spec.test_end or spec.train_end):
            train_end = current_start + window
            val_start = train_end
            val_end = val_start + parse_duration(spec.validation_window) if hasattr(spec, "validation_window") and spec.validation_window else val_start + step

            test_start = val_end if not spec.test_start else spec.test_start
            test_end = test_start + step if not spec.test_end else spec.test_end

            if test_end > (spec.test_end or spec.train_end):
                break

            folds.append(SplitFold(
                fold_id=f"fold_{fold_idx}",
                train_interval=TimeInterval(start=current_start, end=train_end),
                validation_interval=TimeInterval(start=val_start, end=val_end) if spec.validation_start else None,
                test_interval=TimeInterval(start=test_start, end=test_end),
            ))

            current_start += step
            fold_idx += 1

        return folds


class ExpandingWindowSplitter:
    """Creates expanding window splits (accumulating training data)."""

    def split(self, spec: SplitSpecification) -> list[SplitFold]:
        if not spec.step_size:
            raise ValueError("Expanding window requires step_size")

        step = parse_duration(spec.step_size)

        folds = []
        current_end = spec.train_start + parse_duration("30d") if spec.window_size else spec.train_start + step
        fold_idx = 0

        while current_end <= (spec.test_end or spec.train_end):
            val_start = current_end
            val_end = val_start + step
            test_start = val_end if spec.test_start else val_end
            test_end = test_start + step if not spec.test_end else spec.test_end

            if test_end > (spec.test_end or spec.train_end):
                break

            folds.append(SplitFold(
                fold_id=f"fold_{fold_idx}",
                train_interval=TimeInterval(start=spec.train_start, end=current_end),
                validation_interval=TimeInterval(start=val_start, end=val_end) if spec.validation_start else None,
                test_interval=TimeInterval(start=test_start, end=test_end),
            ))

            current_end += step
            fold_idx += 1

        return folds
