"""
Tests for Validation Compiler (§21 mapping rules).
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.research.validation_compiler import (
    compile_claim_from_validation,
    compile_claims_batch,
    VALIDATION_TO_CLAIM_STATUS,
)


class TestValidationCompiler:
    """Test: Validation status maps to correct claim status."""

    def test_pipeline_verified_maps_to_observed(self):
        claim = compile_claim_from_validation(
            validation_result={"status": "pipeline_verified", "strategy_id": "S001", "total_events": 50},
            strategy_id="S001",
            event_family="cpi",
            subject="cpi_surprise",
            predicate="associated_with",
            object="btc_reaction",
        )
        assert claim.claim_status == "observed"

    def test_holdout_failed_maps_to_contradicted(self):
        claim = compile_claim_from_validation(
            validation_result={"status": "holdout_failed", "strategy_id": "S002", "total_events": 30,
                                "holdout_result": "failed"},
            strategy_id="S002",
            event_family="employment",
            subject="nfp_surprise",
            predicate="associated_with",
            object="btc_reaction",
        )
        assert claim.claim_status == "contradicted"
        assert any("holdout" in lim for lim in claim.limitations)

    def test_historical_only_adds_limitations(self):
        claim = compile_claim_from_validation(
            validation_result={"status": "historical_in_sample_only", "strategy_id": "S003", "total_events": 20},
            strategy_id="S003",
            event_family="cpi",
            subject="cpi_surprise",
            predicate="associated_with",
            object="btc_reaction",
        )
        assert claim.claim_status == "insufficient_evidence"
        assert len(claim.limitations) > 0

    def test_walkforward_mixed_maps_to_contested(self):
        claim = compile_claim_from_validation(
            validation_result={"status": "historical_walkforward_mixed", "strategy_id": "S004", "total_events": 100},
            strategy_id="S004",
            event_family="cpi",
            subject="cpi_surprise",
            predicate="associated_with",
            object="eth_reaction",
        )
        assert claim.claim_status == "contested"

    def test_walkforward_supported_maps_to_supported(self):
        claim = compile_claim_from_validation(
            validation_result={"status": "historical_walkforward_supported", "strategy_id": "S005", "total_events": 200},
            strategy_id="S005",
            event_family="fomc",
            subject="fed_dovish",
            predicate="associated_with",
            object="btc_up",
        )
        assert claim.claim_status == "supported"

    def test_leakage_blocked_maps_to_rejected(self):
        claim = compile_claim_from_validation(
            validation_result={"status": "leakage_blocked", "strategy_id": "S006", "total_events": 10},
            strategy_id="S006",
            event_family="cpi",
            subject="cpi_surprise",
            predicate="associated_with",
            object="btc_reaction",
        )
        assert claim.claim_status == "rejected"
        assert any("leakage" in lim for lim in claim.limitations)

    def test_batch_compilation(self):
        results = [
            {"status": "pipeline_verified", "strategy_id": "S001", "total_events": 50},
            {"status": "holdout_failed", "strategy_id": "S002", "total_events": 30,
             "holdout_result": "failed"},
        ]
        strategy_map = {
            "S001": {"subject": "cpi", "predicate": "associated_with", "object": "btc", "event_family": "cpi"},
            "S002": {"subject": "nfp", "predicate": "associated_with", "object": "btc", "event_family": "employment"},
        }
        claims = compile_claims_batch(results, strategy_map)
        assert len(claims) == 2
        assert claims[0].claim_status == "observed"
        assert claims[1].claim_status == "contradicted"
