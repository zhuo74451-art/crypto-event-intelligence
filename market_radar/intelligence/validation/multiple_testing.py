"""Multiple testing control — Holm-Bonferroni and Benjamini-Hochberg.

Only report adjusted p-values alongside raw p-values.
Never report only the best unadjusted results.
"""

import math
from typing import Any, Optional, Callable

from .contracts import StatisticalEvidenceV1


class MultipleTestingAdjuster:
    """Adjusts p-values for multiple comparisons."""

    @staticmethod
    def holm_bonferroni(p_values, family_id="", strategy_id="", strategy_version=""):
        """Holm-Bonferroni step-down correction."""
        n = len(p_values)
        sorted_idx = sorted(range(n), key=lambda i: p_values[i])
        adjusted = [0.0] * n
        for rank, idx in enumerate(sorted_idx):
            adjusted[idx] = min(1.0, p_values[idx] * (n - rank))
        return adjusted

    @staticmethod
    def benjamini_hochberg(p_values, family_id="", strategy_id="", strategy_version=""):
        """Benjamini-Hochberg FDR control."""
        n = len(p_values)
        sorted_idx = sorted(range(n), key=lambda i: p_values[i])
        adjusted = [0.0] * n
        min_bh = 1.0
        for rank in reversed(range(n)):
            idx = sorted_idx[rank]
            bh_val = p_values[idx] * n / (rank + 1)
            min_bh = min(min_bh, bh_val)
            adjusted[idx] = min_bh
        return adjusted

    @staticmethod
    def adjust(p_values, method="holm_bonferroni", family_id="",
               strategy_id="", strategy_version=""):
        """Apply the specified adjustment method."""
        if method == "holm_bonferroni":
            return MultipleTestingAdjuster.holm_bonferroni(
                p_values, family_id, strategy_id, strategy_version)
        elif method == "benjamini_hochberg":
            return MultipleTestingAdjuster.benjamini_hochberg(
                p_values, family_id, strategy_id, strategy_version)
        else:
            raise ValueError(f"Unknown adjustment method: {method}")
