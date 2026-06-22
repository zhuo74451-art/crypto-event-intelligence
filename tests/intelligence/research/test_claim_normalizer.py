"""
Tests for Claim Normalizer (§41 items 1-4).
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.research.claim_normalizer import (
    build_claim_key,
    build_conflict_key,
    create_claim,
    claims_are_opposing,
    claims_share_different_horizon,
    validate_claim_semantics,
)
from market_radar.intelligence.research.contracts import ResearchClaimV1


class TestBuildClaimKey:
    """Test 1: Same claims => same key."""

    def test_same_inputs_same_key(self):
        k1 = build_claim_key("cpi", "associated_with", "btc_up", asset="BTC", time_horizon="short_term")
        k2 = build_claim_key("cpi", "associated_with", "btc_up", asset="BTC", time_horizon="short_term")
        assert k1 == k2

    def test_different_horizon_different_key(self):
        k1 = build_claim_key("cpi", "associated_with", "btc_up", time_horizon="short_term")
        k2 = build_claim_key("cpi", "associated_with", "btc_up", time_horizon="long_term")
        assert k1 != k2

    def test_key_includes_all_parts(self):
        k = build_claim_key("cpi_surprise", "associated_with", "btc_negative_1h", time_horizon="short_term", regime="inflation")
        # The key should contain all parts
        assert "cpi_surprise" in k
        assert "associated_with" in k
        assert "btc_negative_1h" in k
        assert "short_term" in k
        assert "inflation" in k


class TestBuildConflictKey:
    """Test 3: Opposite directions map to same conflict key."""

    def test_opposite_directions_same_conflict_key(self):
        k1 = build_conflict_key("cpi_surprise", "btc_reaction", time_horizon="short_term")
        k2 = build_conflict_key("cpi_surprise", "btc_reaction", time_horizon="short_term")
        assert k1 == k2

    def test_different_horizon_different_conflict_key(self):
        k1 = build_conflict_key("cpi_surprise", "btc_reaction", time_horizon="short_term")
        k2 = build_conflict_key("cpi_surprise", "btc_reaction", time_horizon="long_term")
        assert k1 != k2


class TestClaimsAreOpposing:
    """Test 3: Same subject/object, different predicate => opposing."""

    def test_opposing_predicates(self):
        c1 = ResearchClaimV1(subject="cpi", predicate="associated_with", object="btc_up",
                             claim_type="directional", claim_status="observed")
        c2 = ResearchClaimV1(subject="cpi", predicate="not_associated_with", object="btc_up",
                             claim_type="directional", claim_status="observed")
        assert claims_are_opposing(c1, c2)

    def test_same_predicate_not_opposing(self):
        c1 = ResearchClaimV1(subject="cpi", predicate="associated_with", object="btc_up",
                             claim_type="directional", claim_status="observed")
        c2 = ResearchClaimV1(subject="cpi", predicate="associated_with", object="btc_up",
                             claim_type="directional", claim_status="supported")
        assert not claims_are_opposing(c1, c2)

    def test_different_subject_not_opposing(self):
        c1 = ResearchClaimV1(subject="cpi", predicate="associated_with", object="btc_up",
                             claim_type="directional", claim_status="observed")
        c2 = ResearchClaimV1(subject="nfp", predicate="not_associated_with", object="btc_up",
                             claim_type="directional", claim_status="observed")
        assert not claims_are_opposing(c1, c2)


class TestClaimsShareDifferentHorizon:
    """Test 2: Same subject/predicate/object, different horizon."""

    def test_different_horizon(self):
        c1 = ResearchClaimV1(subject="cpi", predicate="associated_with", object="btc_up",
                             claim_type="directional", claim_status="observed",
                             time_horizon="short_term")
        c2 = ResearchClaimV1(subject="cpi", predicate="associated_with", object="btc_up",
                             claim_type="directional", claim_status="observed",
                             time_horizon="long_term")
        assert claims_share_different_horizon(c1, c2)

    def test_same_horizon(self):
        c1 = ResearchClaimV1(subject="cpi", predicate="associated_with", object="btc_up",
                             claim_type="directional", claim_status="observed",
                             time_horizon="short_term")
        c2 = ResearchClaimV1(subject="cpi", predicate="associated_with", object="btc_up",
                             claim_type="directional", claim_status="observed",
                             time_horizon="short_term")
        assert not claims_share_different_horizon(c1, c2)


class TestValidateClaimSemantics:

    def test_no_warnings_for_valid(self):
        c = ResearchClaimV1(subject="test", predicate="associated_with", object="btc_up",
                            claim_type="directional", claim_status="observed")
        warnings = validate_claim_semantics(c)
        assert len(warnings) == 0

    def test_warning_for_forbidden_status(self):
        with pytest.raises(ValueError, match="Forbidden"):
            create_claim("test", "associated_with", "btc_up", "directional", "proven")


class TestCreateClaim:

    def test_create_claim_sets_ids(self):
        c = create_claim("cpi_surprise", "associated_with", "btc_down",
                         "directional", "observed",
                         time_horizon="short_term", regime="inflation")
        assert c.claim_id is not None
        assert c.claim_id.startswith("RC-")
        assert c.claim_key is not None
