"""
Abstention evaluation — selective prediction metrics.
"""

from __future__ import annotations

from typing import Optional

from ..contracts.evaluation import AbstentionMetrics, MetricValue
from ..contracts.prediction import PredictionRecord


class AbstentionEvaluator:
    """Evaluates selective prediction (abstention) performance."""

    def evaluate(
        self,
        predictions: list[PredictionRecord],
        y_true: list[str],
    ) -> AbstentionMetrics:
        """Compute abstention metrics.

        Args:
            predictions: List of prediction records (some may be abstained).
            y_true: Ground truth labels.

        Returns:
            AbstentionMetrics including coverage, selective accuracy, etc.
        """
        if not predictions:
            return AbstentionMetrics()

        total = len(predictions)
        abstained = sum(1 for p in predictions if p.is_abstained)
        covered = total - abstained

        coverage = covered / total if total > 0 else 0.0
        abstention_rate = abstained / total if total > 0 else 0.0

        # Selective accuracy
        correct = 0
        for p, t in zip(predictions, y_true):
            if not p.is_abstained and p.predicted_direction == t:
                correct += 1

        selective_accuracy = correct / covered if covered > 0 else 0.0

        # Risk-coverage curve (error rate at different coverage levels)
        # Sort non-abstained predictions by confidence
        non_abstained = [
            (p.confidence_score or 0.0, p.predicted_direction == t)
            for p, t in zip(predictions, y_true)
            if not p.is_abstained
        ]
        non_abstained.sort(key=lambda x: x[0], reverse=True)

        risk_curve = []
        n_non_abstained = len(non_abstained)
        for step in [0.25, 0.5, 0.75, 1.0]:
            n_take = int(n_non_abstained * step)
            if n_take == 0:
                continue
            take = non_abstained[:n_take]
            errors = sum(1 for _, correct in take if not correct)
            risk_curve.append({
                "coverage_fraction": step,
                "n_predictions": n_take,
                "error_rate": errors / n_take if n_take > 0 else 0.0,
            })

        return AbstentionMetrics(
            coverage=coverage,
            abstention_rate=abstention_rate,
            selective_accuracy=MetricValue(
                name="selective_accuracy",
                value=selective_accuracy,
                n_samples=covered,
            ),
            selective_brier_score=None,
            error_rate_at_coverage=risk_curve,
        )

    @staticmethod
    def coverage_at_threshold(
        predictions: list[PredictionRecord],
        threshold: float,
        threshold_field: str = "confidence_score",
    ) -> float:
        """Calculate coverage at a given abstention threshold."""
        if not predictions:
            return 0.0
        covered = sum(
            1 for p in predictions
            if getattr(p, threshold_field, 0.0) or 0.0 >= threshold
        )
        return covered / len(predictions)
