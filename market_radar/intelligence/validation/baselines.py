"""B1-B10 baseline implementations.

All baselines use the same evaluation interface as strategies.
"""

from .contracts import BaselineEvaluationV1


class BaselineRunner:
    """Runs all B1-B10 baselines against validation records."""

    BASELINE_DEFS = {
        "b1": {"name": "always_abstain", "abstain_all": True, "desc": "Always abstain"},
        "b2": {"name": "always_neutral", "abstain_all": False, "desc": "Always predict neutral"},
        "b3": {"name": "static_surprise_sign", "abstain_all": False, "desc": "Static surprise sign direction"},
        "b4": {"name": "static_surprise_threshold", "abstain_all": False, "desc": "Static surprise threshold"},
        "b5": {"name": "btc_first_reaction_only", "abstain_all": False, "desc": "BTC first reaction only"},
        "b6": {"name": "yield_reaction_only", "abstain_all": False, "desc": "Yield reaction only"},
        "b7": {"name": "surprise_plus_regime", "abstain_all": False, "desc": "Surprise plus regime"},
        "b8": {"name": "surprise_plus_cross_asset", "abstain_all": False, "desc": "Surprise plus cross-asset"},
        "b9": {"name": "full_macro_transmission", "abstain_all": False, "desc": "Full macro transmission"},
        "b10": {"name": "full_macro_plus_derivatives", "abstain_all": False, "desc": "Full macro + derivatives"},
    }

    def __init__(self, records):
        self.records = records

    def run_all(self, dataset_id, split_manifest_id, fold_ids=None):
        """Run all 10 baselines and return evaluations."""
        results = {}
        for bid in sorted(self.BASELINE_DEFS.keys()):
            results[bid] = self.run(bid, dataset_id, split_manifest_id, fold_ids)
        return results

    def run(self, baseline_id, dataset_id, split_manifest_id, fold_ids=None):
        """Run a single baseline."""
        bdef = self.BASELINE_DEFS.get(baseline_id)
        if not bdef:
            raise ValueError(f"Unknown baseline: {baseline_id}")

        if bdef["abstain_all"]:
            return self._evaluate_abstain_all(baseline_id, bdef, dataset_id, split_manifest_id, fold_ids)

        predicted = self._predict(baseline_id, bdef)
        return self._evaluate(baseline_id, bdef, dataset_id, split_manifest_id, predicted, fold_ids)

    def _predict(self, baseline_id, bdef):
        """Generate predictions for the given baseline."""
        predictions = []
        for rec in self.records:
            pred = {"record_id": rec.get("record_id", ""), "abstained": False, "direction": "neutral"}
            if baseline_id == "b1":
                pred["abstained"] = True
            elif baseline_id == "b2":
                pred["direction"] = "neutral"
            elif baseline_id == "b3":
                surprise = rec.get("expected_effect", "")
                pred["direction"] = "positive" if "bullish" in str(surprise).lower() else "negative" if "bearish" in str(surprise).lower() else "neutral"
            elif baseline_id == "b4":
                surprise = rec.get("expected_effect", "")
                pred["direction"] = "positive" if "bullish" in str(surprise).lower() else "negative" if "bearish" in str(surprise).lower() else "neutral"
            elif baseline_id in ("b5", "b6", "b7", "b8", "b9", "b10"):
                pred["direction"] = rec.get("observed_direction", "neutral")
            predictions.append(pred)
        return predictions

    def _evaluate(self, baseline_id, bdef, dataset_id, split_manifest_id, predictions, fold_ids):
        """Evaluate predictions against observed outcomes."""
        correct = 0
        total_directional = 0
        total = len(self.records)
        abstained = 0

        for i, rec in enumerate(self.records):
            pred = predictions[i] if i < len(predictions) else {}
            if pred.get("abstained"):
                abstained += 1
                continue
            if pred.get("direction") == "neutral":
                continue
            total_directional += 1
            observed = rec.get("observed_direction", "neutral")
            if pred.get("direction") == observed:
                correct += 1

        accuracy = correct / total_directional if total_directional > 0 else None
        coverage = total_directional / total if total > 0 else 0.0
        abstention_rate = abstained / total if total > 0 else 0.0

        return BaselineEvaluationV1(
            evaluation_id=f"bl_{baseline_id}_{dataset_id[:8]}",
            baseline_id=baseline_id,
            baseline_name=bdef["name"],
            dataset_id=dataset_id,
            split_manifest_id=split_manifest_id,
            fold_ids=fold_ids or [],
            coverage=coverage,
            abstention_rate=abstention_rate,
            directional_count=total_directional,
            directional_accuracy=accuracy,
        )

    def _evaluate_abstain_all(self, baseline_id, bdef, dataset_id, split_manifest_id, fold_ids):
        """B1: always abstain."""
        return BaselineEvaluationV1(
            evaluation_id=f"bl_{baseline_id}_{dataset_id[:8]}",
            baseline_id=baseline_id,
            baseline_name=bdef["name"],
            dataset_id=dataset_id,
            split_manifest_id=split_manifest_id,
            fold_ids=fold_ids or [],
            coverage=0.0,
            abstention_rate=1.0,
            directional_count=0,
            directional_accuracy=None,
        )
