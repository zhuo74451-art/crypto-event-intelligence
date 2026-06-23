"""Abstention analysis — coverage-quality tradeoff and abstention reason breakdown."""

import json
from statistics import mean, stdev
from typing import Any, Optional

from .contracts import StrategyEvaluationV1


class AbstentionAnalyzer:
    """Analyzes abstention patterns and coverage-quality tradeoffs."""

    def __init__(self, records):
        self.records = records

    def analyze(self, strategy_id=""):
        """Analyze abstention patterns and return metrics dict."""
        total = len(self.records)
        if total == 0:
            return self._empty_result()

        directional = [r for r in self.records if not r.get("abstained", False)
                       and r.get("observed_direction", "neutral") != "neutral"]
        abstained = [r for r in self.records if r.get("abstained", False)]
        conflicted = [r for r in self.records if "conflict" in str(r.get("abstention_reasons", [])).lower()]
        insufficient = [r for r in self.records if "insufficient" in str(r.get("abstention_reasons", [])).lower()]

        def accuracy(recs):
            if not recs:
                return None
            correct = sum(1 for r in recs
                          if r.get("expected_effect", "") == r.get("observed_direction", ""))
            return correct / len(recs)

        all_acc = accuracy(self.records)
        dir_acc = accuracy(directional)

        reasons = {}
        for r in abstained:
            for reason in r.get("abstention_reasons", ["unknown"]):
                reasons[reason] = reasons.get(reason, 0) + 1

        # Coverage-quality curve points
        cq_curve = self._build_coverage_quality_curve()

        return {
            "strategy_id": strategy_id,
            "total_events": total,
            "directional_count": len(directional),
            "abstained_count": len(abstained),
            "conflict_count": len(conflicted),
            "insufficient_count": len(insufficient),
            "coverage": len(directional) / total if total > 0 else 0.0,
            "abstention_rate": len(abstained) / total if total > 0 else 0.0,
            "all_events_accuracy": all_acc,
            "directional_accuracy": dir_acc,
            "abstained_events_accuracy": accuracy(abstained),
            "abstention_reasons_breakdown": reasons,
            "coverage_quality_curve": cq_curve,
            "conflict_accuracy": accuracy(conflicted),
            "insufficient_accuracy": accuracy(insufficient),
        }

    def _build_coverage_quality_curve(self, steps=10):
        """Build coverage vs accuracy curve by varying abstention threshold."""
        n = len(self.records)
        if n == 0:
            return []
        scores = []
        for i, r in enumerate(self.records):
            conf = len(r.get("abstention_reasons", []))
            scores.append((conf, r))

        scores.sort(key=lambda x: x[0])
        curve = []
        for step in range(steps + 1):
            threshold = step / steps * max(s[0] for s in scores) if scores else 0
            included = [s[1] for s in scores if s[0] <= threshold]
            if included:
                correct = sum(1 for r in included
                              if r.get("expected_effect", "") == r.get("observed_direction", ""))
                acc = correct / len(included)
                curve.append({
                    "abstention_threshold": threshold,
                    "coverage": len(included) / n,
                    "accuracy": acc,
                })
        return curve

    def _empty_result(self):
        return {
            "total_events": 0,
            "directional_count": 0,
            "abstained_count": 0,
            "coverage": 0.0,
            "abstention_rate": 0.0,
            "all_events_accuracy": None,
            "directional_accuracy": None,
            "coverage_quality_curve": [],
        }
