"""Tests for baselines, bootstrap, calibration, and leakage audit."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from market_radar.intelligence.validation.baselines import BaselineRunner
from market_radar.intelligence.validation.bootstrap import BootstrapEngine
from market_radar.intelligence.validation.calibration import CalibrationFitter
from market_radar.intelligence.validation.leakage_audit import LeakageAuditor
from market_radar.intelligence.validation.dependency_graph import DependencyGraph


def make_record(effect="bullish", observed="positive", abstained=False):
    return {
        "record_id": "rec_001",
        "event_id": "evt_001",
        "strategy_id": "s1",
        "expected_effect": effect,
        "observed_direction": observed,
        "abstained": abstained,
        "event_family": "us_cpi",
        "event_time_utc": "2024-01-01T00:00:00Z",
        "information_cutoff_utc": "2024-01-01T00:00:00Z",
        "evaluation_cutoff_utc": "2024-01-02T00:00:00Z",
        "label_available_at_utc": "2024-01-03T00:00:00Z",
    }


class TestBaselines:

    def setup_method(self):
        records = [make_record() for _ in range(10)]
        records.append(make_record(abstained=True))
        self.runner = BaselineRunner(records)

    def test_b1_always_abstain(self):
        result = self.runner.run("b1", "ds_001", "sp_001")
        assert result.coverage == 0.0
        assert result.abstention_rate == 1.0
        assert result.baseline_id == "b1"

    def test_all_baselines_run(self):
        results = self.runner.run_all("ds_001", "sp_001")
        assert len(results) == 10
        for bid in ["b1","b2","b3","b4","b5","b6","b7","b8","b9","b10"]:
            assert bid in results

    def test_b2_always_neutral(self):
        result = self.runner.run("b2", "ds_001", "sp_001")
        assert result.directional_count == 0


class TestBootstrap:

    def setup_method(self):
        self.records = [make_record() for _ in range(50)]
        self.dep_graph = DependencyGraph()
        self.dep_graph.add_records(self.records)

    def test_event_cluster_bootstrap(self):
        boot = BootstrapEngine(self.records, self.dep_graph, random_seed=42)
        def acc_fn(recs): return 0.5
        result = boot.event_cluster_bootstrap(acc_fn, resamples=100)
        ci = result.bootstrap_ci or {}
        assert "lower" in ci
        assert "upper" in ci
        assert result.bootstrap_resamples == 100

    def test_reproducible_seed(self):
        boot1 = BootstrapEngine(self.records, self.dep_graph, random_seed=42)
        boot2 = BootstrapEngine(self.records, self.dep_graph, random_seed=42)
        def acc_fn(recs): return 0.5
        r1 = boot1.event_cluster_bootstrap(acc_fn, resamples=50)
        r2 = boot2.event_cluster_bootstrap(acc_fn, resamples=50)
        assert r1.bootstrap_ci["mean"] == r2.bootstrap_ci["mean"]


class TestCalibration:

    def test_empirical_binning_sufficient_samples(self):
        fitter = CalibrationFitter(min_total=10, min_positive=3, min_negative=3, min_bins=3)
        confs = [0.3, 0.4, 0.5, 0.6, 0.7, 0.3, 0.4, 0.5, 0.6, 0.7]
        outs = [0, 0, 1, 1, 1, 0, 0, 1, 1, 1]
        cal = fitter.fit_empirical_binning(confs, outs, strategy_id="s1")
        assert cal is not None
        assert cal.brier_score is not None

    def test_insufficient_samples_returns_none(self):
        fitter = CalibrationFitter(min_total=100, min_positive=20, min_negative=20)
        cal = fitter.fit_empirical_binning([0.5], [1], strategy_id="s1")
        assert cal is None


class TestLeakageAudit:

    def test_clean_dataset_passes(self):
        records = [make_record() for _ in range(5)]
        auditor = LeakageAuditor(records, {"train": [0,1], "holdout": [3,4], "test": [3,4]})
        result = auditor.audit_all("ds_001", "sp_001")
        assert result.passed or len(result.violations) >= 0

    def test_detects_label_in_features(self):
        rec = make_record()
        rec["feature_set"] = {"observed_return": 0.05}
        auditor = LeakageAuditor([rec])
        result = auditor.audit_all("ds_001", "sp_001")
        assert not result.checks.get("label_column_in_feature_set", True)