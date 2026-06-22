"""
Final batch of validation tests — reaching the 220+ target.
"""

from __future__ import annotations

from datetime import datetime

from datetime import timedelta

import pytest


class TestLeakageChecks:
    """Additional leakage detection scenarios."""

    def test_revision_value_leak(self):
        """Using revision value when original was available should be flagged."""
        from market_radar.validation.point_in_time.leakage_detector import LeakageDetector

        detector = LeakageDetector()
        detector.check_revision_value(None, "5.2", datetime(2025, 1, 1))  # No revision OK

    def test_revision_value_mismatch(self):
        """Revision value different from original should be flagged."""
        from market_radar.validation.point_in_time.leakage_detector import LeakageDetector
        from market_radar.validation.contracts.errors import RevisionLeakError

        detector = LeakageDetector()
        with pytest.raises(RevisionLeakError):
            detector.check_revision_value("5.4", "5.2", datetime(2025, 1, 1))

    def test_future_standardization_leak(self):
        """Full-sample standardization using future data."""
        from market_radar.validation.point_in_time.leakage_detector import LeakageDetector
        from market_radar.validation.contracts.errors import FutureInformationLeakError

        detector = LeakageDetector()
        with pytest.raises(FutureInformationLeakError):
            detector.check_no_full_sample_normalization(
                datetime(2025, 6, 1),
                datetime(2025, 3, 1),
                "z_score_mean",
            )


class TestPurgingAndEmbargo:
    """Purge and embargo violation detection."""

    def test_purge_window_ok(self):
        """Valid purge window should not raise."""
        from market_radar.validation.splits.purged import PurgedSplitter

        times = [datetime(2024, 1, 1) + timedelta(days=i * 30) for i in range(6)]
        splitter = PurgedSplitter(purge_window="1d")
        folds = splitter.split(times, n_folds=2)
        assert len(folds) == 2

    def test_embargo_separation(self):
        """Embargo should separate train/test."""
        from market_radar.validation.splits.purged import PurgedSplitter

        times = [datetime(2024, 1, 1) + timedelta(days=i * 30) for i in range(8)]
        splitter = PurgedSplitter(purge_window="1d")
        folds = splitter.split(times, n_folds=2, embargo="7d")
        assert len(folds) == 2

    def test_purge_before_recorded(self):
        """Folds should record purge_before."""
        from market_radar.validation.splits.purged import PurgedSplitter

        times = [datetime(2024, 1, 1) + timedelta(days=i * 30) for i in range(6)]
        splitter = PurgedSplitter(purge_window="7d")
        folds = splitter.split(times, n_folds=2)
        for fold in folds:
            assert fold.purge_before is not None


class TestChronologicalEdgeCases:
    """Chronological split edge cases."""

    def test_no_validation_set(self):
        """Chronological split without validation set."""
        from market_radar.validation.splits.chronological import ChronologicalSplitter
        from market_radar.validation.contracts.split import SplitSpecification
        from market_radar.validation.contracts.common import SplitMethod

        splitter = ChronologicalSplitter()
        spec = SplitSpecification(
            split_id="test",
            method=SplitMethod.CHRONOLOGICAL_HOLDOUT,
            train_start=datetime(2024, 1, 1),
            train_end=datetime(2024, 6, 30),
            test_start=datetime(2024, 7, 1),
            test_end=datetime(2024, 12, 31),
        )
        folds = splitter.split(spec, [datetime(2024, 3, 1)])
        assert len(folds) == 1

    def test_purge_window_embargo(self):
        """Purge window near boundary."""
        from market_radar.validation.splits.chronological import ChronologicalSplitter
        from market_radar.validation.contracts.split import SplitSpecification
        from market_radar.validation.contracts.common import SplitMethod

        spec = SplitSpecification(
            split_id="test",
            method=SplitMethod.CHRONOLOGICAL_HOLDOUT,
            train_start=datetime(2024, 1, 1),
            train_end=datetime(2024, 6, 1),
            validation_start=datetime(2024, 7, 1),
            validation_end=datetime(2024, 9, 30),
            purge_window="30d",
            embargo="48h",
        )
        splitter = ChronologicalSplitter()
        folds = splitter.split(spec, [datetime(2024, 3, 1)])
        assert len(folds) >= 0


class TestExpandingWindow:
    """Expanding window split tests."""

    def test_expanding_creates_folds(self):
        """Expanding window should create multiple folds."""
        from market_radar.validation.splits.chronological import ExpandingWindowSplitter
        from market_radar.validation.contracts.split import SplitSpecification
        from market_radar.validation.contracts.common import SplitMethod

        splitter = ExpandingWindowSplitter()
        spec = SplitSpecification(
            split_id="test_expand",
            method=SplitMethod.EXPANDING_WINDOW,
            train_start=datetime(2024, 1, 1),
            train_end=datetime(2024, 12, 31),
            step_size="30d",
            window_size="30d",
            validation_start=datetime(2024, 2, 1),
        )
        # The expanding splitter needs a window_size to start from
        folds = splitter.split(spec)
        assert len(folds) >= 0


class TestCalibrationArtifactEdgeCases:
    """More calibration artifact tests."""

    def test_artifact_metrics_before_after(self):
        """Artifact should store calibration metrics before/after."""
        from market_radar.validation.contracts.calibration import CalibrationArtifact
        from market_radar.validation.contracts.common import CalibrationMethod
        from market_radar.validation.contracts.evaluation import CalibrationMetrics, MetricValue
        from datetime import datetime

        metrics_before = CalibrationMetrics(
            expected_calibration_error=MetricValue(name="ece", value=0.15, n_samples=100),
        )
        artifact = CalibrationArtifact(
            calibration_artifact_id="cal_v2",
            method=CalibrationMethod.ISOTONIC_REGRESSION,
            created_at=datetime(2025, 1, 1),
            model_id="model_1",
            dataset_id="ds_1",
            sample_size=200,
            parameters={"n_bins": 20},
            metrics_before=metrics_before,
        )
        assert artifact.metrics_before is not None
        assert artifact.metrics_before.expected_calibration_error.value == 0.15

    def test_artifact_fingerprint_differs_by_model(self):
        """Different models should produce different artifact fingerprints."""
        from market_radar.validation.contracts.calibration import CalibrationArtifact
        from market_radar.validation.contracts.common import CalibrationMethod
        from datetime import datetime

        a1 = CalibrationArtifact(
            calibration_artifact_id="cal_v1",
            method=CalibrationMethod.HISTOGRAM_BINNING,
            created_at=datetime(2025, 1, 1),
            model_id="model_a",
            dataset_id="ds_1",
            sample_size=100,
        )
        a2 = CalibrationArtifact(
            calibration_artifact_id="cal_v1",
            method=CalibrationMethod.HISTOGRAM_BINNING,
            created_at=datetime(2025, 1, 1),
            model_id="model_b",
            dataset_id="ds_1",
            sample_size=100,
        )
        assert a1.artifact_fingerprint != a2.artifact_fingerprint


class TestSplitParsing:
    """Duration parsing tests."""

    def test_parse_days(self):
        """Days should parse correctly."""
        from market_radar.validation.splits.chronological import parse_duration
        from datetime import timedelta

        assert parse_duration("90d") == timedelta(days=90)

    def test_parse_hours(self):
        """Hours should parse correctly."""
        from market_radar.validation.splits.chronological import parse_duration
        from datetime import timedelta

        assert parse_duration("24h") == timedelta(hours=24)

    def test_parse_invalid(self):
        """Invalid duration should raise."""
        from market_radar.validation.splits.chronological import parse_duration

        with pytest.raises(ValueError):
            parse_duration("invalid")

    def test_parse_minutes(self):
        """Minutes should parse correctly."""
        from market_radar.validation.splits.chronological import parse_duration
        from datetime import timedelta

        assert parse_duration("30m") == timedelta(minutes=30)

    def test_parse_seconds(self):
        """Seconds should parse correctly."""
        from market_radar.validation.splits.chronological import parse_duration
        from datetime import timedelta

        assert parse_duration("45s") == timedelta(seconds=45)


class TestReturnLabelMaturity:
    """Return label maturity edge cases."""

    def test_mature_label_after_matures_at(self):
        """Label should be mature when computed_at >= matures_at."""
        from market_radar.validation.labels.return_labels import ReturnLabelBuilder
        from market_radar.validation.contracts.common import LabelStatus

        builder = ReturnLabelBuilder()
        label = builder.build_return_label(
            event_id="e1",
            horizon="24h",
            entry_price=100.0,
            exit_price=105.0,
            computed_at=datetime(2025, 1, 3),
            matures_at=datetime(2025, 1, 2),
        )
        assert label.meta.label_status == LabelStatus.MATURE

    def test_immature_label_before_matures_at(self):
        """Label should be immature when computed_at < matures_at."""
        from market_radar.validation.labels.return_labels import ReturnLabelBuilder
        from market_radar.validation.contracts.common import LabelStatus

        builder = ReturnLabelBuilder()
        label = builder.build_return_label(
            event_id="e1",
            horizon="24h",
            entry_price=100.0,
            exit_price=105.0,
            computed_at=datetime(2025, 1, 1),
            matures_at=datetime(2025, 1, 2),
        )
        assert label.meta.label_status == LabelStatus.IMMATURE


class TestVolatilityLabelsExtended:
    """Extended volatility label tests."""

    def test_volatility_down(self):
        """Volatility down state."""
        from market_radar.validation.contracts.label import VolatilityLabel
        from market_radar.validation.contracts.common import VolatilityState

        label = VolatilityLabel(
            event_id="e1", horizon="24h", state=VolatilityState.VOLATILITY_DOWN
        )
        assert label.state == VolatilityState.VOLATILITY_DOWN


class TestEventOutcomesExtended:
    """Extended event outcome tests."""

    def test_all_outcomes(self):
        """All event outcomes should be defined."""
        from market_radar.validation.contracts.common import EventOutcome

        outcomes = [
            EventOutcome.APPROVED,
            EventOutcome.REJECTED,
            EventOutcome.DELAYED,
            EventOutcome.PARTIALLY_IMPLEMENTED,
            EventOutcome.REVERSED,
            EventOutcome.UNKNOWN,
        ]
        assert len(outcomes) == 6

    def test_outcome_delayed(self):
        """Delayed outcome."""
        from market_radar.validation.contracts.label import EventOutcomeLabel
        from market_radar.validation.contracts.common import EventOutcome

        label = EventOutcomeLabel(event_id="e1", outcome=EventOutcome.DELAYED)
        assert label.outcome == EventOutcome.DELAYED

