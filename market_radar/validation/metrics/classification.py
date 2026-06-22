"""
Classification and probabilistic metrics for validation.
"""

from __future__ import annotations

import math
from typing import Optional

from ..contracts.evaluation import (
    MetricValue,
    ClassMetrics,
    ProbabilisticMetrics,
    CalibrationMetrics,
)


class ClassificationMetricsCalculator:
    """Computes classification metrics from predictions and labels."""

    def compute(
        self,
        y_true: list[str],
        y_pred: list[str],
        classes: Optional[list[str]] = None,
    ) -> ClassMetrics:
        """Compute classification metrics."""
        if not y_true or not y_pred:
            return ClassMetrics()

        if classes is None:
            classes = sorted(set(y_true + y_pred))

        n = len(y_true)
        correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
        accuracy = correct / n if n > 0 else 0.0

        # Confusion matrix
        class_to_idx = {c: i for i, c in enumerate(classes)}
        n_classes = len(classes)
        cm = [[0] * n_classes for _ in range(n_classes)]
        for t, p in zip(y_true, y_pred):
            ti = class_to_idx.get(t, 0)
            pi = class_to_idx.get(p, 0)
            cm[ti][pi] += 1

        # Per-class metrics
        per_class_recall = {}
        precisions = []
        recalls = []

        for i, c in enumerate(classes):
            tp = cm[i][i]
            fp = sum(cm[j][i] for j in range(n_classes) if j != i)
            fn = sum(cm[i][j] for j in range(n_classes) if j != i)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            precisions.append(precision)
            recalls.append(recall)
            per_class_recall[c] = recall

        macro_precision = sum(precisions) / len(precisions) if precisions else 0.0
        macro_recall = sum(recalls) / len(recalls) if recalls else 0.0
        macro_f1 = (
            2 * macro_precision * macro_recall / (macro_precision + macro_recall)
            if (macro_precision + macro_recall) > 0
            else 0.0
        )

        # Weighted F1 (support-weighted)
        class_counts = {c: y_true.count(c) for c in classes}
        total = sum(class_counts.values()) or 1
        weighted_f1 = sum(
            (class_counts[c] / total) * (
                2 * (cm[class_to_idx[c]][class_to_idx[c]] / max(sum(cm[class_to_idx[c]]), 1))
                * (cm[class_to_idx[c]][class_to_idx[c]] / max(sum(cm[i][class_to_idx[c]] for i in range(n_classes)), 1))
                / ((
                    cm[class_to_idx[c]][class_to_idx[c]] / max(sum(cm[class_to_idx[c]]), 1)
                    + cm[class_to_idx[c]][class_to_idx[c]] / max(sum(cm[i][class_to_idx[c]] for i in range(n_classes)), 1)
                ) or 1)
                * 2 if (
                    cm[class_to_idx[c]][class_to_idx[c]] / max(sum(cm[class_to_idx[c]]), 1)
                    + cm[class_to_idx[c]][class_to_idx[c]] / max(sum(cm[i][class_to_idx[c]] for i in range(n_classes)), 1)
                ) > 0 else 0
            )
            for c in classes
        )

        return ClassMetrics(
            accuracy=MetricValue(name="accuracy", value=accuracy, n_samples=n),
            balanced_accuracy=MetricValue(
                name="balanced_accuracy",
                value=macro_recall,
                n_samples=n,
            ),
            precision=MetricValue(name="precision", value=macro_precision, n_samples=n),
            recall=MetricValue(name="recall", value=macro_recall, n_samples=n),
            f1=MetricValue(name="f1", value=macro_f1, n_samples=n),
            confusion_matrix=cm,
            macro_f1=MetricValue(name="macro_f1", value=macro_f1, n_samples=n),
            weighted_f1=MetricValue(name="weighted_f1", value=weighted_f1, n_samples=n),
            per_class_recall=per_class_recall,
        )


class ProbabilisticMetricsCalculator:
    """Computes probabilistic metrics from predicted probabilities and labels."""

    def compute(
        self,
        y_true: list[str],
        y_prob: list[dict[str, float]],
        classes: list[str],
    ) -> ProbabilisticMetrics:
        """Compute Brier score and log loss."""
        if not y_true or not y_prob:
            return ProbabilisticMetrics()

        n = len(y_true)
        brier = 0.0
        log_loss = 0.0

        for true_class, prob_dict in zip(y_true, y_prob):
            for c in classes:
                p = prob_dict.get(c, 0.0)
                p = max(1e-15, min(p, 1 - 1e-15))  # clip
                target = 1.0 if c == true_class else 0.0
                brier += (p - target) ** 2
                if c == true_class:
                    log_loss += -math.log(p)

        brier /= n
        log_loss /= n

        return ProbabilisticMetrics(
            brier_score=MetricValue(name="brier_score", value=brier, n_samples=n),
            log_loss=MetricValue(name="log_loss", value=log_loss, n_samples=n),
        )


class CalibrationMetricsCalculator:
    """Computes calibration metrics (ECE, MCE, reliability diagram data)."""

    def compute(
        self,
        y_true: list[str],
        y_prob: list[dict[str, float]],
        target_class: str,
        n_bins: int = 10,
    ) -> CalibrationMetrics:
        """Compute Expected Calibration Error and related metrics."""
        if not y_true or not y_prob:
            return CalibrationMetrics()

        probs = [p.get(target_class, 0.0) for p in y_prob]
        bin_edges = [i / n_bins for i in range(n_bins + 1)]
        bin_data = {i: {"count": 0, "sum_prob": 0.0, "sum_acc": 0} for i in range(n_bins)}

        for true_class, prob in zip(y_true, probs):
            bin_idx = min(int(prob * n_bins), n_bins - 1)
            bin_data[bin_idx]["count"] += 1
            bin_data[bin_idx]["sum_prob"] += prob
            if true_class == target_class:
                bin_data[bin_idx]["sum_acc"] += 1

        ece = 0.0
        mce = 0.0
        bins = []

        for bin_idx in range(n_bins):
            count = bin_data[bin_idx]["count"]
            if count == 0:
                continue
            avg_prob = bin_data[bin_idx]["sum_prob"] / count
            avg_acc = bin_data[bin_idx]["sum_acc"] / count
            diff = abs(avg_acc - avg_prob)
            ece += diff * (count / len(y_true))
            mce = max(mce, diff)
            bins.append({
                "bin": bin_idx,
                "count": count,
                "avg_probability": avg_prob,
                "avg_accuracy": avg_acc,
                "error": diff,
            })

        # Simple calibration slope and intercept via linear regression of
        # accuracy on predicted probability (weighted by bin count)
        n_bins_nonzero = len(bins)
        if n_bins_nonzero > 1:
            sum_x = sum(b["avg_probability"] * b["count"] for b in bins)
            sum_y = sum(b["avg_accuracy"] * b["count"] for b in bins)
            sum_xy = sum(b["avg_probability"] * b["avg_accuracy"] * b["count"] for b in bins)
            sum_x2 = sum(b["avg_probability"] ** 2 * b["count"] for b in bins)
            total_w = sum(b["count"] for b in bins)
            if total_w > 0 and (sum_x2 * total_w - sum_x ** 2) != 0:
                slope = (sum_xy * total_w - sum_x * sum_y) / (sum_x2 * total_w - sum_x ** 2)
                intercept = (sum_y - slope * sum_x) / total_w
            else:
                slope = 0.0
                intercept = 0.0
        else:
            slope = 0.0
            intercept = 0.0

        return CalibrationMetrics(
            expected_calibration_error=MetricValue(
                name="ece", value=ece, n_samples=len(y_true)
            ),
            maximum_calibration_error=MetricValue(
                name="mce", value=mce, n_samples=len(y_true)
            ),
            calibration_slope=slope,
            calibration_intercept=intercept,
            reliability_bins=bins,
        )
