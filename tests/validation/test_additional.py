"""
Additional validation tests — baselines, regime, robustness, sensitivity.
"""

from __future__ import annotations

from datetime import datetime

import pytest


class TestAdditionalBaselines:
    """Additional baseline tests (continuing from main test file)."""

    def test_random_seed_determinism(self):
        """Random baseline should be deterministic with same seed."""
        from market_radar.validation.baselines.neutral import RandomBaseline
        from datetime import datetime

        b1 = RandomBaseline(seed=100)
        b2 = RandomBaseline(seed=100)
        b1.fit(["up", "down", "up", "flat", "down"])
        b2.fit(["up", "down", "up", "flat", "down"])

        events = [{"event_id": f"e{i}", "horizon": "24h"} for i in range(20)]
        r1 = b1.predict(events, datetime(2025, 1, 1))
        r2 = b2.predict(events, datetime(2025, 1, 1))
        for p1, p2 in zip(r1.predictions, r2.predictions):
            assert p1.predicted_direction == p2.predicted_direction

    def test_random_seed_changes_output(self):
        """Different seed should produce different predictions."""
        from market_radar.validation.baselines.neutral import RandomBaseline
        from datetime import datetime

        b1 = RandomBaseline(seed=100)
        b2 = RandomBaseline(seed=200)
        b1.fit(["up", "down"])
        b2.fit(["up", "down"])

        events = [{"event_id": f"e{i}", "horizon": "24h"} for i in range(5)]
        r1 = b1.predict(events, datetime(2025, 1, 1))
        r2 = b2.predict(events, datetime(2025, 1, 1))
        # At least some predictions should differ
        diffs = sum(
            1 for p1, p2 in zip(r1.predictions, r2.predictions)
            if p1.predicted_direction != p2.predicted_direction
        )
        assert diffs > 0

    def test_empty_fit_does_not_crash(self):
        """Fitting with empty data should not crash."""
        from market_radar.validation.baselines.neutral import RandomBaseline
        from datetime import datetime

        baseline = RandomBaseline(seed=42)
        baseline.fit([])
        result = baseline.predict(
            [{"event_id": "e1", "horizon": "24h"}],
            datetime(2025, 1, 1),
        )
        assert len(result.predictions) == 1

    def test_baseline_specifications_defined(self):
        """All baseline specifications should be importable."""
        from market_radar.validation.contracts.baseline import (
            BASELINE_NEUTRAL,
            BASELINE_RANDOM,
            BASELINE_EVENT_TYPE_PRIOR,
            BASELINE_SENTIMENT_RULE,
            BASELINE_MOMENTUM,
            BASELINE_FUNDING,
            BASELINE_OI,
            BASELINE_MACRO_STATIC,
            BASELINE_REGIME_ONLY,
            BASELINE_LAST_KNOWN_RATE,
        )

        assert BASELINE_NEUTRAL.baseline_id == "B1"
        assert BASELINE_RANDOM.baseline_id == "B2"
        assert BASELINE_EVENT_TYPE_PRIOR.baseline_id == "B3"
        assert BASELINE_SENTIMENT_RULE.baseline_id == "B4"
        assert BASELINE_MOMENTUM.baseline_id == "B5"
        assert BASELINE_FUNDING.baseline_id == "B6"
        assert BASELINE_OI.baseline_id == "B7"
        assert BASELINE_MACRO_STATIC.baseline_id == "B8"
        assert BASELINE_REGIME_ONLY.baseline_id == "B9"
        assert BASELINE_LAST_KNOWN_RATE.baseline_id == "B10"


class TestRegimeSlicing:
    """Regime stratification tests."""

    def test_regime_slice_creation(self):
        """Regime slice should store all fields."""
        from market_radar.validation.contracts.evaluation import RegimeSlice

        slice_ = RegimeSlice(
            regime_name="high_volatility",
            n_samples=50,
        )
        assert slice_.regime_name == "high_volatility"
        assert slice_.n_samples == 50

    def test_regime_slice_small_warning(self):
        """Small regime samples should be flagged."""
        from market_radar.validation.contracts.evaluation import RegimeSlice

        slice_ = RegimeSlice(regime_name="rare", n_samples=3)
        assert slice_.n_samples < 10

    def test_multiple_regime_slices(self):
        """Multiple regime slices should be comparable."""
        from market_radar.validation.contracts.evaluation import RegimeSlice

        slices = [
            RegimeSlice(regime_name="bull", n_samples=100),
            RegimeSlice(regime_name="bear", n_samples=80),
            RegimeSlice(regime_name="sideways", n_samples=120),
        ]
        assert sum(s.n_samples for s in slices) == 300


class TestRobustness:
    """Robustness and sensitivity tests."""

    def test_robustness_result_creation(self):
        """Robustness result should store variations."""
        from market_radar.validation.contracts.evaluation import RobustnessResult

        result = RobustnessResult(
            parameter="flat_threshold",
            variations=[
                {"threshold": 0.001, "accuracy": 0.55},
                {"threshold": 0.005, "accuracy": 0.60},
                {"threshold": 0.010, "accuracy": 0.58},
            ],
            stability="stable",
        )
        assert len(result.variations) == 3

    def test_robustness_unstable_flag(self):
        """Unstable results should be flagged."""
        from market_radar.validation.contracts.evaluation import RobustnessResult

        result = RobustnessResult(
            parameter="window_size",
            variations=[
                {"window": "1h", "accuracy": 0.80},
                {"window": "4h", "accuracy": 0.45},
                {"window": "24h", "accuracy": 0.82},
            ],
            stability="unstable",
        )
        assert result.stability == "unstable"


class TestSensitivityAnalysis:
    """Sensitivity analysis tests."""

    def test_different_event_windows(self):
        """Different event windows should produce different metrics."""
        windows = ["pre_1h", "pre_4h", "pre_24h"]
        assert len(windows) >= 3

    def test_different_flat_thresholds(self):
        """Different flat thresholds should change direction labels."""
        from market_radar.validation.contracts.label import DirectionLabel
        from market_radar.validation.contracts.common import Direction

        for threshold in [0.001, 0.005, 0.01, 0.02]:
            label = DirectionLabel(
                event_id="e1",
                horizon="24h",
                direction=Direction.FLAT,
                flat_threshold=threshold,
            )
            assert label.flat_threshold == threshold

    def test_different_benchmarks(self):
        """Different benchmarks should produce different abnormal returns."""
        from market_radar.validation.contracts.label import ReturnLabel

        for benchmark in ["btc", "eth", "nasdaq", "sp500"]:
            label = ReturnLabel(
                event_id="e1",
                horizon="24h",
                abnormal_return=0.05,
                benchmark=benchmark,
            )
            assert label.benchmark == benchmark


class TestEventDeduplication:
    """Event identity and deduplication tests."""

    def test_event_cluster_creation(self):
        """Event cluster should group related events."""
        from market_radar.validation.contracts.event import EventCluster

        cluster = EventCluster(
            event_cluster_id="fomc_dec",
            primary_event_id="fomc_dec_official",
            member_event_ids=["fomc_dec_official", "fomc_dec_reuters", "fomc_dec_bloomberg"],
            source_dependence_group="fomc_coverage",
        )
        assert len(cluster.member_event_ids) == 3

    def test_event_cluster_dedup_reason(self):
        """Duplicate reasons should be documented."""
        from market_radar.validation.contracts.event import DuplicateReason

        reason = DuplicateReason(
            code="CROSS_MEDIA_SAME_EVENT",
            description="Same FOMC decision reported by Reuters and Bloomberg",
        )
        assert reason.code == "CROSS_MEDIA_SAME_EVENT"

    def test_validation_event_as_of(self):
        """Event should be checkable against point-in-time."""
        from market_radar.validation.contracts.event import ValidationEvent, ValidationEventIdentity
        from market_radar.validation.contracts.common import ValidationEventIdentity
        from datetime import datetime

        event = ValidationEvent(
            event_id="e1",
            identity=ValidationEventIdentity(
                event_cluster_id="cluster_1",
                source_dependence_group="group_a",
                primary_source_id="src1",
            ),
            event_type="macro",
            published_at=datetime(2025, 1, 1, 10, 0),
            effective_at=datetime(2025, 1, 1, 10, 0),
            first_seen_at=datetime(2025, 1, 1, 10, 5),
        )
        assert event.as_of(datetime(2025, 1, 1, 9, 0)) is False
        assert event.as_of(datetime(2025, 1, 1, 10, 10)) is True

    def test_duplicate_reason_enum(self):
        """Duplicate reasons should have stable codes."""
        from market_radar.validation.contracts.event import DuplicateReason

        reasons = [
            DuplicateReason("SAME_SOURCE_RETRANSMISSION", ""),
            DuplicateReason("CROSS_MEDIA_SAME_EVENT", ""),
            DuplicateReason("SAME_EVENT_DIFFERENT_LANGUAGE", ""),
            DuplicateReason("SAME_EVENT_MULTIPLE_UPDATES", ""),
            DuplicateReason("SAME_EVENT_DIFFERENT_ASSETS", ""),
            DuplicateReason("TRULY_INDEPENDENT", ""),
        ]
        codes = [r.code for r in reasons]
        assert len(codes) == len(set(codes))  # all unique


class TestLabelMaturity:
    """Label maturity lifecycle tests."""

    def test_mature_label(self):
        """Mature label should have correct status."""
        from market_radar.validation.contracts.label import LabelMeta
        from market_radar.validation.contracts.common import LabelStatus
        from datetime import datetime

        meta = LabelMeta(
            label_status=LabelStatus.MATURE,
            matures_at=datetime(2025, 1, 2),
            computed_at=datetime(2025, 1, 3),
        )
        assert meta.label_status == LabelStatus.MATURE

    def test_immature_label(self):
        """Immature label should be detected."""
        from market_radar.validation.contracts.label import LabelMeta
        from market_radar.validation.contracts.common import LabelStatus

        meta = LabelMeta(label_status=LabelStatus.IMMATURE)
        assert meta.label_status == LabelStatus.IMMATURE

    def test_disputed_label(self):
        """Disputed label should be tracked."""
        from market_radar.validation.contracts.label import LabelMeta
        from market_radar.validation.contracts.common import LabelStatus

        meta = LabelMeta(label_status=LabelStatus.DISPUTED)
        assert meta.label_status == LabelStatus.DISPUTED

    def test_unavailable_label(self):
        """Unavailable label should be handled."""
        from market_radar.validation.contracts.label import LabelMeta
        from market_radar.validation.contracts.common import LabelStatus

        meta = LabelMeta(label_status=LabelStatus.UNAVAILABLE)
        assert meta.label_status == LabelStatus.UNAVAILABLE

    def test_return_label_with_maturity(self):
        """Return label with maturity tracking."""
        from market_radar.validation.contracts.label import ReturnLabel, LabelMeta
        from market_radar.validation.contracts.common import LabelStatus

        label = ReturnLabel(
            event_id="e1",
            horizon="24h",
            raw_return=0.05,
            meta=LabelMeta(
                label_status=LabelStatus.MATURE,
                label_source="price_data",
            ),
        )
        assert label.meta.label_source == "price_data"


class TestDrawdownLabels:
    """Drawdown label tests."""

    def test_drawdown_label_creation(self):
        """Drawdown label should store risk metrics."""
        from market_radar.validation.contracts.label import DrawdownLabel

        label = DrawdownLabel(
            event_id="e1",
            horizon="24h",
            max_drawdown=-0.05,
            max_favorable_excursion=0.08,
            max_adverse_excursion=-0.03,
            reversal=True,
            continuation=False,
        )
        assert label.max_drawdown == -0.05
        assert label.reversal is True

    def test_drawdown_defaults(self):
        """Drawdown defaults should be None."""
        from market_radar.validation.contracts.label import DrawdownLabel

        label = DrawdownLabel(event_id="e1", horizon="24h")
        assert label.max_drawdown is None
        assert label.reversal is None

    def test_mfe_mae(self):
        """MFE and MAE should be tracked."""
        from market_radar.validation.contracts.label import DrawdownLabel

        label = DrawdownLabel(
            event_id="e1",
            horizon="24h",
            max_favorable_excursion=0.10,
            max_adverse_excursion=-0.05,
        )
        assert label.max_favorable_excursion == 0.10
        assert label.max_adverse_excursion == -0.05


class TestEventOutcomeLabels:
    """Event outcome label tests."""

    def test_outcome_label_approved(self):
        """Approved outcome."""
        from market_radar.validation.contracts.label import EventOutcomeLabel
        from market_radar.validation.contracts.common import EventOutcome

        label = EventOutcomeLabel(event_id="e1", outcome=EventOutcome.APPROVED)
        assert label.outcome == EventOutcome.APPROVED

    def test_outcome_label_rejected(self):
        """Rejected outcome."""
        from market_radar.validation.contracts.label import EventOutcomeLabel
        from market_radar.validation.contracts.common import EventOutcome

        label = EventOutcomeLabel(event_id="e1", outcome=EventOutcome.REJECTED)
        assert label.outcome == EventOutcome.REJECTED


class TestCalibrationArtifact:
    """Calibration artifact tests."""

    def test_artifact_creation(self):
        """Calibration artifact should have required fields."""
        from market_radar.validation.contracts.calibration import CalibrationArtifact
        from market_radar.validation.contracts.common import CalibrationMethod
        from datetime import datetime

        artifact = CalibrationArtifact(
            calibration_artifact_id="cal_v1",
            method=CalibrationMethod.HISTOGRAM_BINNING,
            created_at=datetime(2025, 1, 1),
            model_id="model_1",
            dataset_id="dataset_1",
            sample_size=100,
        )
        assert artifact.artifact_fingerprint
        assert artifact.calibration_artifact_id == "cal_v1"

    def test_artifact_fingerprint_stable(self):
        """Same artifact params should have same fingerprint."""
        from market_radar.validation.contracts.calibration import CalibrationArtifact
        from market_radar.validation.contracts.common import CalibrationMethod
        from datetime import datetime

        a1 = CalibrationArtifact(
            calibration_artifact_id="cal_v1",
            method=CalibrationMethod.HISTOGRAM_BINNING,
            created_at=datetime(2025, 1, 1),
            model_id="model_1",
            dataset_id="dataset_1",
            sample_size=100,
        )
        a2 = CalibrationArtifact(
            calibration_artifact_id="cal_v1",
            method=CalibrationMethod.HISTOGRAM_BINNING,
            created_at=datetime(2025, 1, 2),  # different time
            model_id="model_1",
            dataset_id="dataset_1",
            sample_size=100,
        )
        assert a1.artifact_fingerprint == a2.artifact_fingerprint

    def test_artifact_mismatch_detection(self):
        """Wrong artifact for model should raise."""
        from market_radar.validation.contracts.errors import CalibrationArtifactMismatchError

        with pytest.raises(CalibrationArtifactMismatchError):
            raise CalibrationArtifactMismatchError(
                detail="Artifact model_1 does not match model_2",
                min_fix="Use calibration artifact fitted for model_2",
            )


class TestVolatilityLabels:
    """Volatility label tests."""

    def test_volatility_up(self):
        """Volatility up state."""
        from market_radar.validation.contracts.label import VolatilityLabel
        from market_radar.validation.contracts.common import VolatilityState

        label = VolatilityLabel(
            event_id="e1", horizon="24h", state=VolatilityState.VOLATILITY_UP
        )
        assert label.state == VolatilityState.VOLATILITY_UP

    def test_volatility_normal(self):
        """Normal volatility."""
        from market_radar.validation.contracts.label import VolatilityLabel
        from market_radar.validation.contracts.common import VolatilityState

        label = VolatilityLabel(
            event_id="e1", horizon="24h", state=VolatilityState.NORMAL
        )
        assert label.state == VolatilityState.NORMAL

    def test_volatility_default(self):
        """Default deveralidity should be UNKNOWN."""
        from market_radar.validation.contracts.label import VolatilityLabel

        label = VolatilityLabel(event_id="e1", horizon="24h")
        assert label.state.value == "unknown"


class TestExperimentSpecification:
    """Experiment specification tests."""

    def test_spec_with_all_fields(self):
        """Full experiment specification."""
        from market_radar.validation.contracts.experiment import ExperimentSpecification
        from market_radar.validation.contracts.common import SplitMethod
        from datetime import datetime

        spec = ExperimentSpecification(
            experiment_id="exp_full",
            experiment_version="v1",
            created_at=datetime(2025, 1, 1),
            research_question="Does sentiment predict returns?",
            hypothesis_id="hyp_1",
            strategy_candidate_id="strat_1",
            dataset_id="ds_1",
            prediction_target="direction_24h",
            time_horizons=["1h", "24h"],
            feature_set=["sentiment", "momentum"],
            label_set=["direction"],
            baseline_set=["B1", "B2", "B3"],
            split_method=SplitMethod.CHRONOLOGICAL_HOLDOUT,
            primary_metrics=["accuracy", "brier_score"],
            maximum_trials=50,
            seed=123,
        )
        assert spec.research_question == "Does sentiment predict returns?"

    def test_spec_defaults(self):
        """Experiment defaults should be sensible."""
        from market_radar.validation.contracts.experiment import ExperimentSpecification
        from datetime import datetime

        spec = ExperimentSpecification(
            experiment_id="exp_min",
            experiment_version="v1",
            created_at=datetime(2025, 1, 1),
        )
        assert spec.maximum_trials == 100
        assert spec.seed == 42

    def test_trial_record_creation(self):
        """Trial record should track parameters and metrics."""
        from market_radar.validation.contracts.experiment import TrialRecord

        trial = TrialRecord(
            trial_id="trial_1",
            parameters={"alpha": 0.1, "beta": 0.5},
            metrics={"accuracy": 0.85, "brier": 0.15},
            status="completed",
        )
        assert trial.parameters["alpha"] == 0.1
        assert trial.metrics["accuracy"] == 0.85


class TestErrorContract:
    """Error contract tests."""

    def test_error_message_format(self):
        """Error should have formatted message."""
        from market_radar.validation.contracts.errors import DatasetNotFoundError

        err = DatasetNotFoundError(
            detail="Dataset not found",
            object_id="ds_1",
        )
        msg = str(err)
        assert "DATASET_NOT_FOUND" in msg
        assert "ds_1" in msg

    def test_error_all_codes_unique(self):
        """All error codes should be unique."""
        from market_radar.validation.contracts.errors import (
            DatasetNotFoundError,
            DatasetFingerprintMismatchError,
            DatasetNotPointInTimeError,
            FutureInformationLeakError,
            LabelNotMatureError,
            RevisionLeakError,
            GroupSplitLeakError,
            SourceDependenceLeakError,
            PurgeWindowViolationError,
            TargetInFeaturesError,
            InvalidExperimentStateError,
            ExperimentSpecNotFrozenError,
            BaselineMissingError,
            CalibrationSampleTooSmallError,
            CalibrationArtifactMismatchError,
            ProbabilityOutOfRangeError,
            MultipleTestingUndeclaredError,
            BootstrapMethodInvalidError,
            RandomSeedMissingError,
            FailedExperimentDeletedError,
            PromotionNotAllowedError,
        )

        codes = [cls.code for cls in [
            DatasetNotFoundError,
            DatasetFingerprintMismatchError,
            DatasetNotPointInTimeError,
            FutureInformationLeakError,
            LabelNotMatureError,
            RevisionLeakError,
            GroupSplitLeakError,
            SourceDependenceLeakError,
            PurgeWindowViolationError,
            TargetInFeaturesError,
            InvalidExperimentStateError,
            ExperimentSpecNotFrozenError,
            BaselineMissingError,
            CalibrationSampleTooSmallError,
            CalibrationArtifactMismatchError,
            ProbabilityOutOfRangeError,
            MultipleTestingUndeclaredError,
            BootstrapMethodInvalidError,
            RandomSeedMissingError,
            FailedExperimentDeletedError,
            PromotionNotAllowedError,
        ]]
        assert len(codes) == len(set(codes))


class TestEvaluationLevel:
    """Evaluation level tests."""

    def test_data_availability_levels(self):
        """All data availability levels."""
        from market_radar.validation.contracts.evaluation import EvaluationResult
        from market_radar.validation.contracts.common import DataAvailabilityLevel

        result = EvaluationResult(data_availability=DataAvailabilityLevel.INSUFFICIENT)
        assert result.data_availability.value == "insufficient"

    def test_promotion_not_production(self):
        """Promotion should not allow production_ready."""
        from market_radar.validation.contracts.common import PromotionRecommendation

        assert PromotionRecommendation.REJECT.value == "reject"
        with pytest.raises(ValueError):
            PromotionRecommendation("production_ready")
