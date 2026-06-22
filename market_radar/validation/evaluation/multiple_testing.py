"""
Multiple testing correction — controls for multiple comparison bias.
"""

from __future__ import annotations

import math
from typing import Optional

from ..contracts.evaluation import MultipleTestingResult
from ..contracts.common import MultipleTestingMethod
from ..contracts.errors import MultipleTestingUndeclaredError


class MultipleTestingCorrector:
    """Applies multiple testing corrections to p-values."""

    def __init__(self, method: MultipleTestingMethod):
        self.method = method

    def correct(
        self,
        p_values: list[float],
        n_comparisons: Optional[int] = None,
    ) -> MultipleTestingResult:
        """Apply multiple testing correction."""
        if n_comparisons is None:
            n_comparisons = len(p_values)

        if n_comparisons == 0:
            return MultipleTestingResult(
                method=self.method,
                n_comparisons=0,
            )

        if n_comparisons > 1 and self.method in (
            MultipleTestingMethod.BONFERRONI,
            MultipleTestingMethod.HOLM,
            MultipleTestingMethod.BENJAMINI_HOCHBERG,
        ):
            pass  # proceed with correction
        elif n_comparisons > 1:
            raise MultipleTestingUndeclaredError(
                detail=(
                    f"Multiple comparisons detected ({n_comparisons}) "
                    f"but no correction method applied"
                ),
                min_fix=f"Declare multiple testing family and apply {self.method.value}",
            )

        if self.method == MultipleTestingMethod.BONFERRONI:
            adjusted = [min(p * n_comparisons, 1.0) for p in p_values]
        elif self.method == MultipleTestingMethod.HOLM:
            sorted_indices = sorted(range(len(p_values)), key=lambda i: p_values[i])
            adjusted = [0.0] * len(p_values)
            for rank, idx in enumerate(sorted_indices):
                adjusted[idx] = min(p_values[idx] * (len(p_values) - rank), 1.0)
        elif self.method == MultipleTestingMethod.BENJAMINI_HOCHBERG:
            sorted_indices = sorted(range(len(p_values)), key=lambda i: p_values[i])
            adjusted = [0.0] * len(p_values)
            for rank, idx in enumerate(sorted_indices):
                adjusted[idx] = min(
                    p_values[idx] * len(p_values) / (rank + 1), 1.0
                )
        else:
            adjusted = list(p_values)

        significant = [p <= 0.05 for p in adjusted]

        return MultipleTestingResult(
            method=self.method,
            n_comparisons=n_comparisons,
            p_values=list(p_values),
            adjusted_p_values=adjusted,
            significant_at_05=significant,
        )


def bonferroni(p_values: list[float]) -> MultipleTestingResult:
    return MultipleTestingCorrector(MultipleTestingMethod.BONFERRONI).correct(p_values)


def holm(p_values: list[float]) -> MultipleTestingResult:
    return MultipleTestingCorrector(MultipleTestingMethod.HOLM).correct(p_values)


def benjamini_hochberg(p_values: list[float]) -> MultipleTestingResult:
    return MultipleTestingCorrector(MultipleTestingMethod.BENJAMINI_HOCHBERG).correct(p_values)
