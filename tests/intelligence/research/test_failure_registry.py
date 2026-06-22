"""
Tests for Failure Registry (§22, §41 item 9).
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.research.failure_registry import FailureRegistry, ResearchFailureRecord


class TestFailureRegistry:
    """Test 9: Failed experiments enter the cognition layer."""

    def test_add_failure(self):
        registry = FailureRegistry()
        rec = ResearchFailureRecord(
            strategy_version="S001_v1",
            dataset_label="walkforward_2018_2022",
            time_split="2018-2020|2020-2022",
            failure_reason="insufficient_sharpe",
            affected_regimes=["inflation_dominant"],
            affected_event_families=["cpi"],
        )
        fid = registry.add_failure(rec)
        assert fid.startswith("FL-")
        assert registry.count() == 1

    def test_add_failure_idempotent(self):
        registry = FailureRegistry()
        rec = ResearchFailureRecord(
            strategy_version="S001_v1",
            dataset_label="test",
            time_split="split",
            failure_reason="reason",
        )
        registry.add_failure(rec)
        registry.add_failure(rec)  # same record again
        assert registry.count() == 1

    def test_get_failure(self):
        registry = FailureRegistry()
        rec = ResearchFailureRecord(
            strategy_version="S002_v1",
            dataset_label="holdout_2023",
            time_split="train|test",
            failure_reason="leakage",
        )
        fid = registry.add_failure(rec)
        fetched = registry.get_failure(fid)
        assert fetched is not None
        assert fetched.failure_reason == "leakage"

    def test_export_jsonl(self, tmp_path):
        registry = FailureRegistry()
        rec = ResearchFailureRecord(
            strategy_version="S001_v1",
            dataset_label="test",
            time_split="split",
            failure_reason="reason",
        )
        registry.add_failure(rec)
        path = tmp_path / "failures.jsonl"
        registry.export_jsonl(str(path))
        content = path.read_text()
        assert "S001_v1" in content
        assert "FL-" in content
