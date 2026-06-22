"""
Tests for Conflict Engine (§41 items 3, 4, 19).
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.research.conflict_engine import ConflictEngine
from market_radar.intelligence.research.contracts import ResearchClaimV1


class TestConflictEngine:
    """Test 3: Opposite directions enter same conflict set.
       Test 4: Majority cannot auto-resolve."""

    def test_opposite_directions_same_conflict(self):
        engine = ConflictEngine()
        c1 = ResearchClaimV1(
            subject="cpi_surprise", predicate="associated_with",
            object="btc_up", claim_type="directional",
            claim_status="observed", time_horizon="short_term",
        )
        c2 = ResearchClaimV1(
            subject="cpi_surprise", predicate="not_associated_with",
            object="btc_up", claim_type="directional",
            claim_status="observed", time_horizon="short_term",
        )
        conflicts = engine.process_claims([c1, c2])
        assert len(conflicts) >= 1
        # Both claim IDs should be in the same conflict set
        conflict = conflicts[0]
        assert c1.claim_id in conflict.claim_ids
        assert c2.claim_id in conflict.claim_ids

    def test_same_direction_no_conflict(self):
        engine = ConflictEngine()
        c1 = ResearchClaimV1(
            subject="cpi_surprise", predicate="associated_with",
            object="btc_up", claim_type="directional",
            claim_status="observed", time_horizon="short_term",
        )
        c2 = ResearchClaimV1(
            subject="cpi_surprise", predicate="associated_with",
            object="btc_up", claim_type="directional",
            claim_status="supported", time_horizon="short_term",
        )
        conflicts = engine.process_claims([c1, c2])
        # Same direction should not create a direction conflict (but may create horizon conflict if horizons differ)
        direction_conflicts = [c for c in conflicts if c.conflict_type == "direction_conflict"]
        assert len(direction_conflicts) == 0

    def test_open_conflict_default(self):
        engine = ConflictEngine()
        c1 = ResearchClaimV1(
            subject="a", predicate="goes_with",
            object="b", claim_type="directional",
            claim_status="observed",
        )
        c2 = ResearchClaimV1(
            subject="a", predicate="goes_against",
            object="b", claim_type="directional",
            claim_status="observed",
        )
        conflicts = engine.process_claims([c1, c2])
        assert conflicts[0].conflict_status == "open"
        assert conflicts[0].resolution_status == "unresolved"

    def test_get_open_conflicts(self):
        engine = ConflictEngine()
        c1 = ResearchClaimV1(
            subject="a", predicate="goes_with",
            object="b", claim_type="directional",
            claim_status="observed",
        )
        c2 = ResearchClaimV1(
            subject="a", predicate="goes_against",
            object="b", claim_type="directional",
            claim_status="observed",
        )
        engine.process_claims([c1, c2])
        open_conflicts = engine.get_open_conflicts()
        assert len(open_conflicts) == 1

    def test_horizon_conflict_detected(self):
        """Test 19: Multi-time-scale conflicts preserved."""
        engine = ConflictEngine()
        c1 = ResearchClaimV1(
            subject="cpi_surprise", predicate="associated_with",
            object="btc_up", claim_type="directional",
            claim_status="observed", time_horizon="short_term",
        )
        c2 = ResearchClaimV1(
            subject="cpi_surprise", predicate="associated_with",
            object="btc_up", claim_type="directional",
            claim_status="observed", time_horizon="long_term",
        )
        conflicts = engine.process_claims([c1, c2])
        horizon_conflicts = [c for c in conflicts if c.conflict_type == "horizon_conflict"]
        assert len(horizon_conflicts) >= 1

    def test_idempotent_processing(self):
        """Same claims produce same conflict sets."""
        engine = ConflictEngine()
        claims = [
            ResearchClaimV1(
                subject="x", predicate="pred_a",
                object="y", claim_type="directional",
                claim_status="observed",
            ),
            ResearchClaimV1(
                subject="x", predicate="pred_b",
                object="y", claim_type="directional",
                claim_status="observed",
            ),
        ]
        c1 = engine.process_claims(claims)
        c2 = engine.process_claims(claims)
        assert len(c1) == len(c2)
        for cs1, cs2 in zip(c1, c2):
            assert cs1.conflict_set_id == cs2.conflict_set_id
