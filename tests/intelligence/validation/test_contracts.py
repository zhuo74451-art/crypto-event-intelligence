"""Tests for Lane D validation contracts and core modules."""

import json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from market_radar.intelligence.validation.contracts import (
    ValidationDatasetV1, SplitManifestV1, WalkforwardFoldV1,
    StrategyEvaluationV1, BaselineEvaluationV1, CalibrationArtifactV1,
    FailureExperimentV1, LeakageAuditV1, StatisticalEvidenceV1,
    ValidationStatus, CalibrationMethod, SplitMethod, DirectionLabel, LeakageSeverity,
)
from market_radar.intelligence.validation.dependency_graph import DependencyGraph


class TestContracts:
    """Test all validation contracts can be instantiated and serialized."""

    def test_validation_dataset_v1(self):
        ds = ValidationDatasetV1(dataset_id="test_ds_001")
        assert ds.dataset_id == "test_ds_001"
        assert ds.contract_name == "ValidationDatasetV1"
        d = ds.to_dict()
        assert d["dataset_id"] == "test_ds_001"

    def test_split_manifest_v1(self):
        sm = SplitManifestV1(split_manifest_id="test_sp_001", split_method="fixed_time")
        assert sm.split_manifest_id == "test_sp_001"
        assert sm.split_method == "fixed_time"

    def test_walkforward_fold_v1(self):
        wf = WalkforwardFoldV1(fold_id="test_wf_001", fold_index=0, test_count=10)
        assert wf.fold_id == "test_wf_001"
        assert wf.test_count == 10

    def test_strategy_evaluation_v1(self):
        se = StrategyEvaluationV1(evaluation_id="test_ev_001", strategy_id="strat_a")
        assert se.evaluation_id == "test_ev_001"
        assert se.calibration_status == "unavailable"

    def test_baseline_evaluation_v1(self):
        be = BaselineEvaluationV1(evaluation_id="bl_b1_001", baseline_id="b1", baseline_name="always_abstain")
        assert be.baseline_id == "b1"
        assert be.coverage == 0.0

    def test_calibration_artifact_v1(self):
        ca = CalibrationArtifactV1(calibration_artifact_id="cal_001", strategy_id="strat_a")
        assert ca.calibration_artifact_id == "cal_001"
        assert ca.minimum_sample_requirement == 100

    def test_failure_experiment_v1(self):
        fe = FailureExperimentV1(experiment_id="fail_001", hypothesis="test hypothesis")
        assert fe.experiment_id == "fail_001"
        assert not fe.leakage_detected

    def test_leakage_audit_v1(self):
        la = LeakageAuditV1(audit_id="audit_001", passed=True)
        assert la.audit_id == "audit_001"
        assert la.passed

    def test_statistical_evidence_v1(self):
        se = StatisticalEvidenceV1(evidence_id="stat_001", sufficient_sample=True)
        assert se.evidence_id == "stat_001"
        assert se.sufficient_sample


class TestDependencyGraph:
    """Test dependency graph construction and queries."""

    def setup_method(self):
        self.records = [
            {"event_id": "evt_001", "event_family": "us_cpi", "reference_period": "2024-01", "strategy_id": "s1"},
            {"event_id": "evt_001", "event_family": "us_cpi", "reference_period": "2024-01", "strategy_id": "s2"},
            {"event_id": "evt_002", "event_family": "us_nfp", "reference_period": "2024-02", "strategy_id": "s1"},
        ]

    def test_event_dependency_groups(self):
        g = DependencyGraph()
        g.add_records(self.records)
        groups = g.get_event_dependency_groups()
        assert len(groups) == 2  # two unique events

    def test_independent_group_count(self):
        g = DependencyGraph()
        g.add_records(self.records)
        assert g.count_independent_groups() == 2

    def test_all_groups(self):
        g = DependencyGraph()
        g.add_records(self.records)
        all_g = g.get_all_groups()
        assert "event_dependency_group" in all_g
        assert "origin_dependency_group" in all_g


class TestEnums:
    """Test validation enum values."""

    def test_validation_status_values(self):
        statuses = [e.value for e in ValidationStatus]
        assert "not_evaluated" in statuses
        assert "calibration_available" in statuses
        assert "leakage_blocked" in statuses

    def test_split_method_values(self):
        methods = [e.value for e in SplitMethod]
        assert "fixed_time" in methods
        assert "expanding_walkforward" in methods
        assert "rolling_walkforward" in methods

    def test_calibration_method_values(self):
        methods = [e.value for e in CalibrationMethod]
        assert "empirical_binning" in methods

    def test_leakage_severity_values(self):
        sev = [e.value for e in LeakageSeverity]
        assert "critical" in sev
        assert "low" in sev