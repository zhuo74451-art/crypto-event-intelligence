"""Drift analysis — distribution shifts between train/validation/holdout.

Uses PSI (Population Stability Index), KS statistic, and mean/variance shifts.
"""

import math
from statistics import mean, stdev
from typing import Any, Optional


class DriftAnalyzer:
    """Detects distribution shifts across splits, regimes, and years."""

    @staticmethod
    def population_stability_index(expected, actual, num_bins=10):
        """Calculate Population Stability Index."""
        if not expected or not actual:
            return None
        combined = expected + actual
        if not combined:
            return None
        mn, mx = min(combined), max(combined)
        if mn == mx:
            return 0.0
        bins = [mn + (mx - mn) * i / num_bins for i in range(num_bins + 1)]
        psi = 0.0
        for i in range(num_bins):
            e_count = sum(1 for v in expected if bins[i] <= v < bins[i + 1])
            a_count = sum(1 for v in actual if bins[i] <= v < bins[i + 1])
            e_pct = (e_count + 1e-10) / len(expected)
            a_pct = (a_count + 1e-10) / len(actual)
            psi += (e_pct - a_pct) * math.log(e_pct / a_pct)
        return psi

    @staticmethod
    def ks_statistic(sample_a, sample_b):
        """Two-sample Kolmogorov-Smirnov statistic."""
        if not sample_a or not sample_b:
            return None
        combined = sorted(set(sample_a + sample_b))
        max_diff = 0.0
        for point in combined:
            cdf_a = sum(1 for v in sample_a if v <= point) / len(sample_a)
            cdf_b = sum(1 for v in sample_b if v <= point) / len(sample_b)
            max_diff = max(max_diff, abs(cdf_a - cdf_b))
        return max_diff

    @staticmethod
    def mean_shift(sample_a, sample_b):
        """Relative mean shift."""
        if not sample_a or not sample_b:
            return None
        m_a, m_b = mean(sample_a), mean(sample_b)
        if m_a == 0:
            return m_b - m_a
        return (m_b - m_a) / abs(m_a)

    @staticmethod
    def variance_shift(sample_a, sample_b):
        """Relative variance shift."""
        if len(sample_a) < 2 or len(sample_b) < 2:
            return None
        v_a, v_b = stdev(sample_a), stdev(sample_b)
        if v_a == 0:
            return v_b - v_a
        return (v_b - v_a) / v_a

    def compare_splits(self, train_records, test_records, field="observed_return"):
        """Compare distributions of a field between train and test splits."""
        train_vals = [r.get(field) for r in train_records if r.get(field) is not None]
        test_vals = [r.get(field) for r in test_records if r.get(field) is not None]

        if not train_vals or not test_vals:
            return {"field": field, "status": "insufficient_data"}

        return {
            "field": field,
            "train_count": len(train_vals),
            "test_count": len(test_vals),
            "train_mean": mean(train_vals),
            "test_mean": mean(test_vals),
            "psi": self.population_stability_index(train_vals, test_vals),
            "ks_statistic": self.ks_statistic(train_vals, test_vals),
            "mean_shift": self.mean_shift(train_vals, test_vals),
            "variance_shift": self.variance_shift(train_vals, test_vals),
        }

    def analyze(self, train_records, test_records):
        """Full drift analysis across key fields."""
        fields = ["observed_return", "point_in_time_quality",
                   "consensus_quality", "regime"]
        results = {}
        for field in fields:
            results[field] = self.compare_splits(train_records, test_records, field)
        return results
