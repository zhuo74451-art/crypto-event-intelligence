"""Walkforward executor — orchestrates fold generation and evaluation."""

import json
import os
from datetime import datetime, timezone

from .contracts import WalkforwardFoldV1
from .splitter import ChronologicalSplitter


class WalkforwardExecutor:
    """Executes expanding and rolling walk-forward splits."""

    def __init__(self, records, output_dir, purge_hours=24, embargo_days=7):
        self.records = records
        self.output_dir = output_dir
        self.splitter = ChronologicalSplitter(purge_hours, embargo_days)

    def run_expanding(self, dataset_id, initial_train_years=5, test_years=1):
        """Run expanding walk-forward and return folds + fold data."""
        folds, fold_data = self.splitter.expanding_walkforward(
            self.records, initial_train_years, test_years, dataset_id)
        self._write_folds(folds, "expanding")
        return folds, fold_data

    def run_rolling(self, dataset_id, train_window_years=5, test_years=1):
        """Run rolling walk-forward and return folds + fold data."""
        folds, fold_data = self.splitter.rolling_walkforward(
            self.records, train_window_years, test_years, dataset_id)
        self._write_folds(folds, "rolling")
        return folds, fold_data

    def run_fixed(self, dataset_id, train_end="2018-12-31T23:59:59Z",
                  validation_end="2022-12-31T23:59:59Z"):
        """Run fixed time split and return indices + manifest."""
        return self.splitter.fixed_time_split(
            self.records, train_end, validation_end, dataset_id)

    def _write_folds(self, folds, prefix):
        os.makedirs(self.output_dir, exist_ok=True)
        path = os.path.join(self.output_dir, f"walkforward_folds_{prefix}_v1.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for fold in folds:
                f.write(json.dumps(fold.to_dict(), ensure_ascii=False) + "\n")
