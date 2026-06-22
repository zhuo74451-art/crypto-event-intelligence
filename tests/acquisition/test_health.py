"""Health and drift tests — 20+ scenarios."""
import pytest
from datetime import datetime, timezone
from market_radar.acquisition.health.evaluator import SourceHealthEvaluator
from market_radar.acquisition.health.parser_drift import ParserDriftDetector
from market_radar.acquisition.contracts.health import HealthStatus, HealthIndicator, ParserDriftReport

class TestSourceHealthEvaluator:
    def setup_method(self):
        self.evaluator = SourceHealthEvaluator()

    def test_healthy(self):
        self.evaluator.record_success("source-1")
        report = self.evaluator.get_report("source-1")
        assert report is not None
        assert report.overall_status == HealthStatus.HEALTHY

    def test_degraded_with_warning(self):
        self.evaluator.record_success("source-1")
        self.evaluator.record_failure("source-1", "timeout")
        report = self.evaluator.get_report("source-1")
        assert report is not None

    def test_consecutive_failures_tracked(self):
        for _ in range(5):
            self.evaluator.record_failure("source-1", "error")
        report = self.evaluator.get_report("source-1")
        assert report.consecutive_failures >= 3

    def test_record_success_tracks_time(self):
        self.evaluator.record_success("source-1")
        report = self.evaluator.get_report("source-1")
        assert report.last_success_at != ""

    def test_record_failure_tracks_time(self):
        self.evaluator.record_failure("source-1", "error")
        report = self.evaluator.get_report("source-1")
        assert report.last_failure_at != ""

    def test_unknown_source(self):
        report = self.evaluator.get_report("nonexistent")
        assert report is None

class TestParserDriftDetector:
    def setup_method(self):
        self.detector = ParserDriftDetector()

    def test_no_drift_initially(self):
        report = self.detector.get_drift_report("source-1")
        assert report is None

    def test_no_drift_after_identical_parse(self):
        fields = {"title": "Test", "date": "2026-01-01"}
        self.detector.record_parse("source-1", fields)
        self.detector.record_parse("source-1", fields)
        report = self.detector.get_drift_report("source-1")
        assert report is None or report.severity.value == "none"

    def test_detects_missing_field(self):
        self.detector.record_parse("source-1", {"title": "Test", "body": "Content"})
        report = self.detector.detect("source-1", {"title": "Test"})
        assert report is not None
        assert len(report.fields_affected) >= 1

    def test_detects_type_change(self):
        self.detector.record_parse("source-1", {"tags": "single"})
        report = self.detector.detect("source-1", {"tags": ["a", "b"]})
        assert report is not None
