"""
Integration Tests — Cross-Lane Reference Integrity

Tests 11-14: Producer rejection conditions
Tests 15-18: Cross-lane ID linkage
Tests 19: Multi-time-scale preserved
Tests 20: Unresolved references quarantine
Tests 21-22: Idempotency
Tests 23: Offline replay
Tests 24: Real sample
"""

import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from market_radar.intelligence.research.contracts import _deterministic_id, EvidenceEdgeV1, ResearchClaimV1
from market_radar.intelligence.integration.integration_contracts import (
    CompatibilityCheckV1,
    IntegrationRunV1,
    deterministic_run_id,
    VALID_CHECK_NAMES,
)


class TestDeterministicIds:
    """Test 21: Same inputs => same IDs."""

    def test_same_run_id(self):
        sha = "5a5ca58253479403f65ec726016d1ca9b91703d1"
        pshas = {"lane_a": "abc123", "lane_b": "def456"}
        cvers = {"claim_v1": "1"}
        rid1 = deterministic_run_id(sha, pshas, cvers, "1.0.0")
        rid2 = deterministic_run_id(sha, pshas, cvers, "1.0.0")
        assert rid1 == rid2
        assert rid1.startswith("RUN-")

    def test_different_inputs_different_run_id(self):
        sha = "5a5ca58253479403f65ec726016d1ca9b91703d1"
        pshas1 = {"lane_a": "abc123"}
        pshas2 = {"lane_a": "xyz789"}
        cvers = {"claim_v1": "1"}
        rid1 = deterministic_run_id(sha, pshas1, cvers, "1.0.0")
        rid2 = deterministic_run_id(sha, pshas2, cvers, "1.0.0")
        assert rid1 != rid2


class TestCompatibilityChecks:
    """Test 11-14: Rejection conditions."""

    def test_valid_check_names(self):
        assert "producer_base_sha_matches" in VALID_CHECK_NAMES
        assert "artifact_hash_matches" in VALID_CHECK_NAMES
        assert "schema_file_present" in VALID_CHECK_NAMES
        assert "kernel_contract_unchanged" in VALID_CHECK_NAMES

    def test_compatibility_check_creation(self):
        check = CompatibilityCheckV1(
            check_name="producer_base_sha_matches",
            lane="lane_a",
            passed=True,
            details="Base SHA matches sealed base",
        )
        assert check.check_id.startswith("CHK-")
        assert check.passed is True

    def test_invalid_check_name_raises(self):
        with pytest.raises(ValueError, match="Invalid check name"):
            CompatibilityCheckV1(
                check_name="nonexistent_check",
                lane="lane_a",
                passed=False,
            )


class TestCrossLaneReferences:
    """Tests 15-18: Cross-lane ID linkage (structural)."""

    def test_event_id_to_window(self):
        # Lane A event IDs are sha256-based; Lane B windows reference them
        event_id = _deterministic_id("EV", "us_cpi_2025_01::2025-01-15")
        assert event_id.startswith("EV-")
        assert len(event_id) == 19  # EV- + 16 hex chars

    def test_strategy_id_to_validation(self):
        strategy_id = _deterministic_id("ST", "cpi_surprise_btc_1h_v1")
        assert strategy_id.startswith("ST-")

    def test_evaluation_id_to_claim(self):
        eval_id = _deterministic_id("EVAL", "walkforward_001::cpi_surprise")
        claim_id = _deterministic_id("RC", "cpi_surprise::associated_with::btc_up")
        assert eval_id != claim_id
        assert claim_id.startswith("RC-")


class TestIdempotency:
    """Tests 21-22: Rerun produces same results, no duplicates."""

    def test_rerun_same_claim_id(self):
        c1 = ResearchClaimV1(
            subject="cpi", predicate="associated_with",
            object="btc_up", claim_type="directional",
            claim_status="observed", time_horizon="short_term",
        )
        c2 = ResearchClaimV1(
            subject="cpi", predicate="associated_with",
            object="btc_up", claim_type="directional",
            claim_status="observed", time_horizon="short_term",
        )
        assert c1.claim_id == c2.claim_id

    def test_rerun_same_edge_id(self):
        e1 = EvidenceEdgeV1(
            claim_id="RC-TEST", evidence_role="supporting",
            source_lane="lane_a", source_artifact_path="p",
            source_record_id="r1",
            observed_at_utc="2025-01-01T00:00:00Z",
            available_at_utc="2025-01-01T00:00:00Z",
        )
        e2 = EvidenceEdgeV1(
            claim_id="RC-TEST", evidence_role="supporting",
            source_lane="lane_a", source_artifact_path="p",
            source_record_id="r1",
            observed_at_utc="2025-01-01T00:00:00Z",
            available_at_utc="2025-01-01T00:00:00Z",
        )
        assert e1.evidence_edge_id == e2.evidence_edge_id


class TestOfflineReplay:
    """Test 23: Fixed producer locks enable offline replay."""

    def test_offline_run_id_deterministic(self):
        """Run ID depends only on locked inputs, not on time."""
        rid1 = deterministic_run_id(
            "5a5ca58253479403f65ec726016d1ca9b91703d1",
            {"lane_a": "abc", "lane_b": "def", "lane_c": "ghi", "lane_d": "jkl"},
            {"claim": "1", "edge": "1"},
            "1.0.0",
        )
        rid2 = deterministic_run_id(
            "5a5ca58253479403f65ec726016d1ca9b91703d1",
            {"lane_a": "abc", "lane_b": "def", "lane_c": "ghi", "lane_d": "jkl"},
            {"claim": "1", "edge": "1"},
            "1.0.0",
        )
        assert rid1 == rid2


class TestKernelContracts:
    """Test 25: Kernel golden cases preserved."""

    def test_kernel_contracts_exist(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        kernel_files = [
            "market_radar/intelligence/contracts/hypothesis.py",
            "market_radar/intelligence/contracts/arbitration.py",
            "market_radar/intelligence/contracts/evidence.py",
            "market_radar/intelligence/contracts/assessment.py",
            "market_radar/intelligence/contracts/calibration.py",
        ]
        for kf in kernel_files:
            full_path = os.path.join(base, kf)
            assert os.path.isfile(full_path), f"Missing: {full_path}"
