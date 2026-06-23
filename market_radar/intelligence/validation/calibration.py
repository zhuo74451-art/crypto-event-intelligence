"""Calibration fitter — empirical binning calibration with sample guards.

Only generates CalibrationArtifactV1 when minimum sample requirements are met.
"""

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Optional

from .contracts import CalibrationArtifactV1


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
           datetime.now(timezone.utc).strftime("%f")[:3] + "Z"


class CalibrationFitter:
    """Fits empirical binning calibration.

    Requirements (from Section 20):
    - minimum_total_samples: 100
    - minimum_positive_samples: 20
    - minimum_negative_samples: 20
    - minimum_bin_count: 10
    """

    def __init__(self, min_total=100, min_positive=20,
                 min_negative=20, min_bins=10):
        self.min_total = min_total
        self.min_positive = min_positive
        self.min_negative = min_negative
        self.min_bins = min_bins

    def fit_empirical_binning(self, confidences, outcomes,
                               strategy_id="", strategy_version="",
                               horizon="", asset="", dataset_id="",
                               fit_split_ids=None, num_bins=10):
        """Fit empirical binning calibration.

        Args:
            confidences: list of confidence scores (0.0 to 1.0)
            outcomes: list of binary outcomes (0 or 1)
            All other args for metadata.
        Returns:
            CalibrationArtifactV1 or None if samples insufficient
        """
        n = len(confidences)
        n_pos = sum(outcomes)
        n_neg = n - n_pos

        if n < self.min_total or n_pos < self.min_positive or n_neg < self.min_negative:
            return None

        n_bins = min(num_bins, n // 5)
        n_bins = max(n_bins, self.min_bins)

        paired = list(zip(confidences, outcomes))
        paired.sort(key=lambda x: x[0])
        bin_size = len(paired) // n_bins

        bin_edges = []
        bin_counts = []
        observed_frequencies = []

        for i in range(n_bins):
            start = i * bin_size
            end = start + bin_size if i < n_bins - 1 else len(paired)
            bin_items = paired[start:end]
            if not bin_items:
                continue
            edge = bin_items[-1][0] if bin_items else 0.0
            bin_edges.append(edge)
            bin_counts.append(len(bin_items))
            observed_frequencies.append(
                sum(o for _, o in bin_items) / len(bin_items)
            )

        brier = sum((c - o) ** 2 for c, o in zip(confidences, outcomes)) / n
        log_loss_val = self._log_loss(confidences, outcomes)
        ece = self._expected_calibration_error(
            confidences, outcomes, bin_edges, bin_counts, observed_frequencies)
        mce = self._maximum_calibration_error(
            confidences, outcomes, bin_edges, bin_counts, observed_frequencies)

        artifact_id = hashlib.sha256(
            f"{strategy_id}|{horizon}|{asset}|{_utc_now()}".encode()
        ).hexdigest()[:24]

        return CalibrationArtifactV1(
            calibration_artifact_id=artifact_id,
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            horizon=horizon,
            asset=asset,
            method="empirical_binning",
            fit_dataset_id=dataset_id,
            fit_split_ids=fit_split_ids or [],
            fit_date_start="",
            fit_date_end="",
            input_confidence_type="uncalibrated_score",
            output_confidence_type="calibrated_probability",
            parameters={"num_bins": n_bins},
            bin_edges=bin_edges,
            bin_counts=bin_counts,
            observed_frequencies=observed_frequencies,
            brier_score=brier,
            log_loss=log_loss_val,
            expected_calibration_error=ece,
            maximum_calibration_error=mce,
            minimum_sample_requirement=self.min_total,
            sample_count=n,
            generated_at_utc=_utc_now(),
            limitations=["Empirical binning only; isotonic/platt not fitted"],
        )

    def _log_loss(self, confidences, outcomes):
        eps = 1e-15
        total = 0.0
        for c, o in zip(confidences, outcomes):
            c = max(eps, min(1 - eps, c))
            total += o * math.log(c) + (1 - o) * math.log(1 - c)
        return -total / len(confidences)

    def _expected_calibration_error(self, confidences, outcomes,
                                     bin_edges, bin_counts, observed_freqs):
        n = len(confidences)
        if n == 0:
            return 0.0
        total = 0.0
        idx = 0
        for i in range(len(bin_edges)):
            bin_size = bin_counts[i] if i < len(bin_counts) else 0
            if bin_size == 0:
                continue
            avg_conf = sum(confidences[idx:idx + bin_size]) / bin_size
            total += bin_size * abs(observed_freqs[i] - avg_conf)
            idx += bin_size
        return total / n

    def _maximum_calibration_error(self, confidences, outcomes,
                                    bin_edges, bin_counts, observed_freqs):
        n = len(confidences)
        if n == 0:
            return 0.0
        max_err = 0.0
        idx = 0
        for i in range(len(bin_edges)):
            bin_size = bin_counts[i] if i < len(bin_counts) else 0
            if bin_size == 0:
                continue
            avg_conf = sum(confidences[idx:idx + bin_size]) / bin_size
            err = abs(observed_freqs[i] - avg_conf)
            max_err = max(max_err, err)
            idx += bin_size
        return max_err

    def check_sample_requirements(self, n, n_pos, n_neg):
        """Check if sample requirements are met."""
        return {
            "total_ok": n >= self.min_total,
            "positive_ok": n_pos >= self.min_positive,
            "negative_ok": n_neg >= self.min_negative,
            "total_available": n,
            "min_total_required": self.min_total,
            "min_positive_required": self.min_positive,
            "min_negative_required": self.min_negative,
        }
