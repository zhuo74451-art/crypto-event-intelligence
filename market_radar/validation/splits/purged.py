"""
Purged cross-validation split — prevents label leakage between train and test.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from ..contracts.split import SplitFold, TimeInterval
from ..contracts.errors import PurgeWindowViolationError


class PurgedSplitter:
    """Creates purged cross-validation splits to prevent label leakage.

    Labels in the test set may overlap with training features if the label
    horizon extends backward. Purging removes training samples whose labels
    would overlap with test samples.
    """

    def __init__(self, purge_window: str = "24h"):
        self.purge_window = purge_window

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

    def split(
        self,
        timestamps: list[datetime],
        n_folds: int = 5,
        embargo: Optional[str] = None,
    ) -> list[SplitFold]:
        """Create purged folds."""
        sorted_times = sorted(timestamps)
        total = len(sorted_times)
        fold_size = total // n_folds
        purge_delta = self._parse_duration(self.purge_window)
        embargo_delta = self._parse_duration(embargo) if embargo else timedelta(0)

        folds = []
        for i in range(n_folds):
            test_start_idx = i * fold_size
            test_end_idx = (i + 1) * fold_size if i < n_folds - 1 else total

            test_start = sorted_times[test_start_idx]
            test_end = sorted_times[test_end_idx - 1] if test_end_idx > test_start_idx else test_start

            # Purge window: exclude training data whose labels might overlap with test
            purge_cutoff = test_start - purge_delta

            # Embargo
            embargo_cutoff = test_end + embargo_delta

            train_times = [t for t in sorted_times[:test_start_idx] if t <= purge_cutoff]

            folds.append(SplitFold(
                fold_id=f"purged_fold_{i}",
                train_interval=TimeInterval(
                    start=sorted_times[0] if train_times else test_start,
                    end=train_times[-1] if train_times else purge_cutoff,
                ),
                validation_interval=None,
                test_interval=TimeInterval(start=test_start, end=test_end),
                purge_before=purge_cutoff,
                embargo_after=embargo_cutoff if embargo_delta > timedelta(0) else None,
            ))

        return folds
