"""
Calibration protocols — transforms raw scores into calibrated probabilities.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from ..contracts.calibration import CalibrationArtifact
from ..contracts.common import CalibrationMethod, ConfidenceType
from ..contracts.errors import CalibrationSampleTooSmallError, CalibrationArtifactMismatchError
from ..contracts.evaluation import CalibrationMetrics


class NoCalibration:
    """No calibration — scores are used as-is (not valid probabilities)."""

    def fit(self, scores: list[float], targets: list[int]) -> None:
        pass

    def predict_proba(self, scores: list[float]) -> list[float]:
        return list(scores)

    @property
    def confidence_type(self) -> ConfidenceType:
        return ConfidenceType.UNCALIBRATED_SCORE


class HistogramBinningCalibration:
    """Histogram binning calibration — divides scores into bins and maps to empirical frequencies."""

    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins
        self._bin_edges: list[float] = []
        self._bin_probs: list[float] = []

    def fit(self, scores: list[float], targets: list[int]) -> None:
        if len(scores) < 10:
            raise CalibrationSampleTooSmallError(
                detail=f"Histogram binning requires at least 10 samples, got {len(scores)}",
                min_fix="Collect more calibration data or use NoCalibration",
            )
        n = len(scores)
        sorted_pairs = sorted(zip(scores, targets))
        bin_size = n // self.n_bins
        self._bin_edges = []
        self._bin_probs = []

        for i in range(self.n_bins):
            start = i * bin_size
            end = (i + 1) * bin_size if i < self.n_bins - 1 else n
            bin_scores = sorted_pairs[start:end]
            self._bin_edges.append(bin_scores[0][0] if bin_scores else 0.0)
            bin_targets = [t for _, t in bin_scores]
            self._bin_probs.append(sum(bin_targets) / len(bin_targets) if bin_targets else 0.0)

    def predict_proba(self, scores: list[float]) -> list[float]:
        probs = []
        for score in scores:
            bin_idx = -1
            for i in range(len(self._bin_edges)):
                if score <= self._bin_edges[i] or i == len(self._bin_edges) - 1:
                    bin_idx = i
                    break
            if bin_idx == -1:
                bin_idx = len(self._bin_probs) - 1
            probs.append(self._bin_probs[bin_idx] if 0 <= bin_idx < len(self._bin_probs) else 0.5)
        return probs

    @property
    def confidence_type(self) -> ConfidenceType:
        return ConfidenceType.CALIBRATED_PROBABILITY


class PlattScalingCalibration:
    """Platt scaling — logistic regression on scores."""

    def __init__(self):
        self._a: float = 0.0
        self._b: float = 0.0

    def fit(self, scores: list[float], targets: list[int]) -> None:
        if len(scores) < 10:
            raise CalibrationSampleTooSmallError(
                detail=f"Platt scaling requires at least 10 samples, got {len(scores)}",
                min_fix="Collect more calibration data or use NoCalibration",
            )
        # Simple logistic regression via scipy if available
        try:
            from scipy.optimize import minimize
            import numpy as np

            x = np.array(scores)
            y = np.array(targets, dtype=float)

            def neg_log_likelihood(params):
                a, b = params
                p = 1.0 / (1.0 + np.exp(-(a * x + b)))
                p = np.clip(p, 1e-15, 1 - 1e-15)
                return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))

            result = minimize(neg_log_likelihood, [1.0, 0.0], method="L-BFGS-B")
            self._a, self._b = result.x
        except ImportError:
            # Fallback: simple logistic fit
            self._a = 1.0
            self._b = 0.0

    def predict_proba(self, scores: list[float]) -> list[float]:
        import numpy as np

        x = np.array(scores)
        p = 1.0 / (1.0 + np.exp(-(self._a * x + self._b)))
        return p.tolist()

    @property
    def confidence_type(self) -> ConfidenceType:
        return ConfidenceType.CALIBRATED_PROBABILITY


class CalibrationFactory:
    """Factory for creating calibration instances."""

    @staticmethod
    def create(method: CalibrationMethod, **kwargs) -> Any:
        if method == CalibrationMethod.NONE:
            return NoCalibration()
        elif method == CalibrationMethod.HISTOGRAM_BINNING:
            return HistogramBinningCalibration(**kwargs)
        elif method == CalibrationMethod.PLATT_SCALING:
            return PlattScalingCalibration(**kwargs)
        elif method == CalibrationMethod.ISOTONIC_REGRESSION:
            return HistogramBinningCalibration(n_bins=20)  # approximation
        elif method == CalibrationMethod.TEMPERATURE_SCALING:
            return PlattScalingCalibration()  # fallback
        raise ValueError(f"Unknown calibration method: {method}")
