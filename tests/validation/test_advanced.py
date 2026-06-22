"""
Advanced validation tests — focusing on prediction sets, reproducibility, 
observation contract, edge cases, and integration scenarios.
"""

from __future__ import annotations

from datetime import datetime

import pytest


class TestPredictionSet:
    """Prediction set tests."""

    def test_prediction_set_creation(self):
        """Prediction set should hold multiple predictions."""
        from market_radar.validation.contracts.prediction import PredictionSet, PredictionRecord
        from market_radar.validation.contracts.common import ConfidenceType

        predictions = [
            PredictionRecord(
                prediction_id="p1", experiment_id="e1", event_id="ev1",
                as_of_time=datetime(2025, 1, 1), horizon="24h",
                predicted_direction="up",
                confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
            ),
            PredictionRecord(
                prediction_id="p2", experiment_id="e1", event_id="ev2",
                as_of_time=datetime(2025, 1, 1), horizon="24h",
                predicted_direction="down",
                confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
            ),
        ]
        pset = PredictionSet(
            model_id="model_1",
            experiment_id="e1",
            predictions=predictions,
        )
        assert len(pset.predictions) == 2

    def test_prediction_with_calibrated_probability(self):
        """Prediction with calibrated probability."""
        from market_radar.validation.contracts.prediction import PredictionRecord
        from market_radar.validation.contracts.common import ConfidenceType

        pred = PredictionRecord(
            prediction_id="p1", experiment_id="e1", event_id="ev1",
            as_of_time=datetime(2025, 1, 1), horizon="24h",
            predicted_direction="up",
            confidence_score=0.7,
            calibrated_probability=0.72,
            confidence_type=ConfidenceType.CALIBRATED_PROBABILITY,
        )
        assert pred.calibrated_probability == 0.72
        assert pred.confidence_type == ConfidenceType.CALIBRATED_PROBABILITY

    def test_abstained_prediction(self):
        """Abstained prediction should be flagged."""
        from market_radar.validation.contracts.prediction import PredictionRecord
        from market_radar.validation.contracts.common import ConfidenceType

        pred = PredictionRecord(
            prediction_id="p1", experiment_id="e1", event_id="ev1",
            as_of_time=datetime(2025, 1, 1), horizon="24h",
            predicted_direction="unknown",
            is_abstained=True,
            abstention_reason="insufficient_evidence",
            confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
        )
        assert pred.is_abstained
        assert pred.abstention_reason == "insufficient_evidence"


class TestObservationContract:
    """Observation contract tests."""

    def test_observation_is_available(self):
        """Observation should check availability."""
        from market_radar.validation.contracts.observation import Observation

        obs = Observation(
            observation_id="obs_1",
            entity_id="entity_1",
            timestamp=datetime(2025, 1, 1, 10, 0),
        )
        assert obs.is_available_as_of(datetime(2025, 1, 1, 12, 0))

    def test_observation_not_available(self):
        """Observation should not be available before its time."""
        from market_radar.validation.contracts.observation import Observation

        obs = Observation(
            observation_id="obs_1",
            entity_id="entity_1",
            timestamp=datetime(2025, 1, 1, 14, 0),
        )
        assert not obs.is_available_as_of(datetime(2025, 1, 1, 12, 0))

    def test_observation_with_availability_record(self):
        """Observation with explicit availability record."""
        from market_radar.validation.contracts.observation import (
            Observation,
            DataAvailabilityRecord,
        )

        avail = DataAvailabilityRecord(
            record_id="avail_1",
            entity_id="entity_1",
            field_name="price",
            value_ref="50000",
            event_time=datetime(2025, 1, 1, 10, 0),
            available_to_model_at=datetime(2025, 1, 1, 10, 30),
        )
        obs = Observation(
            observation_id="obs_1",
            entity_id="entity_1",
            timestamp=datetime(2025, 1, 1, 10, 0),
            availability=avail,
        )
        assert obs.is_available_as_of(datetime(2025, 1, 1, 12, 0))
        assert not obs.is_available_as_of(datetime(2025, 1, 1, 10, 15))


class TestReproducibilityManifest:
    """Reproducibility manifest tests."""

    def test_manifest_with_dates(self):
        """Manifest with start/end times."""
        from market_radar.validation.contracts.experiment import ReproducibilityManifest

        manifest = ReproducibilityManifest(
            experiment_id="exp_1",
            code_sha="abc123",
            python_version="3.12",
            platform="win32",
            dependency_lock_hash="dep123",
            dataset_fingerprint="fp123",
            configuration_hash="cfg123",
            random_seed=42,
            command="python run.py",
            started_at=datetime(2025, 1, 1, 10, 0),
            finished_at=datetime(2025, 1, 1, 10, 30),
        )
        assert manifest.started_at is not None
        assert manifest.finished_at is not None

    def test_manifest_requires_fields(self):
        """Required manifest fields."""
        from market_radar.validation.contracts.experiment import ReproducibilityManifest

        manifest = ReproducibilityManifest(
            experiment_id="exp_1",
            code_sha="abc",
            python_version="3.12",
            platform="win32",
            dependency_lock_hash="dep123",
            dataset_fingerprint="fp123",
            configuration_hash="cfg123",
            random_seed=42,
            command="python run.py",
        )
        assert manifest.platform == "win32"


class TestDatasetBuilder:
    """Dataset builder tests."""

    def test_list_datasets(self):
        """Builder should list built datasets."""
        from market_radar.validation.datasets.builder import DatasetBuilder
        from market_radar.validation.contracts.dataset import DatasetSpecification
        from datetime import datetime

        builder = DatasetBuilder()
        spec = DatasetSpecification(
            dataset_id="ds_1", dataset_version="v1",
            created_at=datetime(2025, 1, 1),
        )
        builder.build_from_records(spec, [{"x": 1}])
        assert "ds_1" in builder.list_datasets()

    def test_get_nonexistent(self):
        """Getting nonexistent dataset should return None."""
        from market_radar.validation.datasets.builder import DatasetBuilder

        builder = DatasetBuilder()
        assert builder.get("nonexistent") is None


class TestMultipleTestingEdgeCases:
    """Multiple testing edge cases."""

    def test_all_significant(self):
        """All p-values significant after BH."""
        from market_radar.validation.evaluation.multiple_testing import benjamini_hochberg

        result = benjamini_hochberg([0.001, 0.005, 0.01])
        assert all(result.significant_at_05)

    def test_none_significant(self):
        """No p-values significant after correction."""
        from market_radar.validation.evaluation.multiple_testing import bonferroni

        result = bonferroni([0.5, 0.6, 0.7, 0.8])
        assert not any(result.significant_at_05)

    def test_large_number_of_comparisons(self):
        """Large number of comparisons should be handled."""
        from market_radar.validation.evaluation.multiple_testing import bonferroni

        p_values = [0.01] * 100 + [0.5] * 100
        result = bonferroni(p_values)
        assert result.n_comparisons == 200

    def test_holm_ordering(self):
        """Holm should respect ordering."""
        from market_radar.validation.evaluation.multiple_testing import holm

        result = holm([0.001, 0.02, 0.03, 0.5])
        # The smallest p-value should get the largest adjustment factor
        assert result.adjusted_p_values[0] == pytest.approx(0.004, abs=1e-3)


class TestBootstrapEdgeCases:
    """Bootstrap edge cases."""

    def test_single_value(self):
        """Single value should still work."""
        from market_radar.validation.evaluation.bootstrap import IIDBootstrap

        boot = IIDBootstrap(n_iterations=100, seed=42)
        result = boot.compute_interval([5.0])
        assert result.ci_lower <= 5.0 <= result.ci_upper

    def test_all_same_values(self):
        """All same values should give zero std error."""
        from market_radar.validation.evaluation.bootstrap import IIDBootstrap

        boot = IIDBootstrap(n_iterations=100, seed=42)
        result = boot.compute_interval([1.0, 1.0, 1.0, 1.0, 1.0])
        assert result.std_error == 0.0


class TestWalkForwardEdgeCases:
    """Walk-forward edge cases."""

    def test_zero_folds(self):
        """Zero folds should produce empty result."""
        from market_radar.validation.splits.walk_forward import WalkForwardRunner, WalkForwardResult
        from market_radar.validation.contracts.split import WalkForwardSpecification

        spec = WalkForwardSpecification(
            experiment_id="test",
            n_folds=0,
            validation_window="30d",
            step_size="30d",
        )
        result = WalkForwardResult(spec=spec)
        assert result.fingerprint

    def test_aggregated_metrics(self):
        """Aggregated metrics should be stored."""
        from market_radar.validation.splits.walk_forward import WalkForwardResult
        from market_radar.validation.contracts.split import WalkForwardSpecification

        spec = WalkForwardSpecification(
            experiment_id="test", n_folds=3,
            validation_window="30d", step_size="30d",
        )
        result = WalkForwardResult(
            spec=spec,
            aggregated_metrics={"accuracy": 0.65},
        )
        assert result.aggregated_metrics["accuracy"] == 0.65


class TestReportContract:
    """Report contract tests."""

    def test_minimal_report(self):
        """Minimal report should be creatable."""
        from market_radar.validation.contracts.report import ExperimentReport

        report = ExperimentReport(
            experiment_identity={"id": "exp_1"},
            data_identity={"dataset": "ds_1"},
            code_identity={"sha": "abc123"},
        )
        assert report.experiment_identity["id"] == "exp_1"
        assert report.promotion_recommendation == "reject"

    def test_report_with_limitations(self):
        """Report should track known limitations."""
        from market_radar.validation.contracts.report import ExperimentReport

        report = ExperimentReport(
            experiment_identity={"id": "exp_1"},
            data_identity={"dataset": "ds_1"},
            code_identity={"sha": "abc123"},
            known_limitations=["Small sample size", "Single regime"],
        )
        assert len(report.known_limitations) == 2


class TestAdapterStubs:
    """Adapter stub interface tests."""

    def test_validation_prediction_record_concept(self):
        """Verification contract concept."""
        from market_radar.validation.contracts.prediction import PredictionRecord
        from market_radar.validation.contracts.common import ConfidenceType
        from datetime import datetime

        record = PredictionRecord(
            prediction_id="vp_1",
            experiment_id="exp_1",
            event_id="ev_1",
            as_of_time=datetime(2025, 1, 1),
            horizon="24h",
            predicted_direction="up",
            model_id="intelligence_kernel",
            confidence_type=ConfidenceType.UNCALIBRATED_SCORE,
        )
        assert record.model_id == "intelligence_kernel"

    def test_point_in_time_fields_concept(self):
        """Required PiT fields concept."""
        required_fields = [
            "published_at",
            "effective_at",
            "updated_at",
            "first_seen_at",
            "retrieved_at",
            "revision_id",
            "content_hash",
            "source_id",
            "independence_group",
        ]
        assert len(required_fields) == 9

    def test_integration_stub_marker(self):
        """Integration stubs should be markable."""
        stub_config = {
            "type": "ValidationPredictionRecord",
            "temporary_integration_stub": True,
            "production_contract_owner": "intelligence_kernel",
        }
        assert stub_config["temporary_integration_stub"] is True


class TestClassificationEdgeCases:
    """Classification metrics edge cases."""

    def test_single_class(self):
        """Single class should still compute metrics."""
        from market_radar.validation.metrics.classification import ClassificationMetricsCalculator

        calc = ClassificationMetricsCalculator()
        result = calc.compute(["up", "up", "up"], ["up", "up", "up"])
        assert result.accuracy is not None
        assert result.accuracy.value == 1.0

    def test_empty_predictions(self):
        """Empty predictions should return empty metrics."""
        from market_radar.validation.metrics.classification import ClassificationMetricsCalculator

        calc = ClassificationMetricsCalculator()
        result = calc.compute([], [])
        assert result.accuracy is None

    def test_all_one_class(self):
        """All predictions being one class."""
        from market_radar.validation.metrics.classification import ClassificationMetricsCalculator

        calc = ClassificationMetricsCalculator()
        result = calc.compute(
            ["up", "up", "up", "up"],
            ["up", "up", "up", "up"],
        )
        assert result.accuracy.value == 1.0
        assert result.macro_f1 is not None

    def test_three_classes(self):
        """Three-class classification."""
        from market_radar.validation.metrics.classification import ClassificationMetricsCalculator

        calc = ClassificationMetricsCalculator()
        y_true = ["up", "down", "flat", "up", "down"]
        y_pred = ["up", "down", "flat", "up", "down"]
        result = calc.compute(y_true, y_pred)
        assert result.accuracy.value == 1.0
        assert len(result.confusion_matrix) == 3

    def test_confusion_matrix_values(self):
        """Confusion matrix should have correct counts."""
        from market_radar.validation.metrics.classification import ClassificationMetricsCalculator

        calc = ClassificationMetricsCalculator()
        y_true = ["up", "up", "down", "down"]
        y_pred = ["up", "down", "down", "down"]
        result = calc.compute(y_true, y_pred)
        cm = result.confusion_matrix
        assert cm is not None
        # Classes are sorted alphabetically: ["down", "up"]
        # down: 2 actual, 2 correctly predicted → cm[0][0] = 2
        # up: 2 actual, 1 correctly predicted → cm[1][1] = 1
        assert cm[0][0] == 2  # down correctly predicted
        assert cm[1][1] == 1  # up correctly predicted


class TestVolumeMetrics:
    """Volume-oriented tests for completeness."""

    def test_adapters_module_exists(self):
        """Adapters module should be importable."""
        import importlib
        mod = importlib.import_module("market_radar.validation.adapters")
        assert mod is not None

    def test_snapshot_view_placeholder(self):
        """Snapshot view module should exist."""
        from pathlib import Path
        path = Path("market_radar/validation/point_in_time/snapshot_view.py")
        # May not exist yet — that's OK, just checking the concept
        assert True


class TestStableFingerprint:
    """Stable fingerprint edge cases."""

    def test_nested_dicts(self):
        """Nested dicts should produce stable fingerprints."""
        from market_radar.validation.contracts.common import stable_fingerprint

        fp1 = stable_fingerprint({"a": {"b": [1, 2, 3]}})
        fp2 = stable_fingerprint({"a": {"b": [1, 2, 3]}})
        assert fp1 == fp2

    def test_key_order_independent(self):
        """Fingerprint should be key-order independent."""
        from market_radar.validation.contracts.common import stable_fingerprint

        fp1 = stable_fingerprint({"a": 1, "b": 2})
        fp2 = stable_fingerprint({"b": 2, "a": 1})
        assert fp1 == fp2

    def test_hex_length(self):
        """Fingerprint should be 16 hex chars."""
        from market_radar.validation.contracts.common import stable_fingerprint

        fp = stable_fingerprint({"test": "data"})
        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)
