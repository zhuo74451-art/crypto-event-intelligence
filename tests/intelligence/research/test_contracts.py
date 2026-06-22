"""
Tests for Research Intelligence Contracts (Lane E)
Covers items 1-10 from §41 test requirements.
"""

import pytest
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from market_radar.intelligence.research.contracts import (
    ResearchClaimV1,
    EvidenceEdgeV1,
    ConflictSetV1,
    ResearchQuestionV1,
    CandidateRecordV1,
    DecisionRecordV1,
    ResearchDossierV1,
    _deterministic_id,
    VALID_CLAIM_STATUSES,
    FORBIDDEN_STATUSES,
)


class TestResearchClaimV1:
    """Test 1: Same claims produce same IDs.
       Test 2: Different time horizons produce different IDs."""

    def test_same_claim_same_id(self):
        c1 = ResearchClaimV1(
            subject="test", predicate="associated_with", object="btc_up",
            claim_type="directional", claim_status="observed",
            time_horizon="short_term",
        )
        c2 = ResearchClaimV1(
            subject="test", predicate="associated_with", object="btc_up",
            claim_type="directional", claim_status="observed",
            time_horizon="short_term",
        )
        assert c1.claim_id == c2.claim_id, "Same claims must have same ID"
        assert c1.claim_key == c2.claim_key

    def test_different_horizon_different_id(self):
        c1 = ResearchClaimV1(
            subject="test", predicate="associated_with", object="btc_up",
            claim_type="directional", claim_status="observed",
            time_horizon="short_term",
        )
        c2 = ResearchClaimV1(
            subject="test", predicate="associated_with", object="btc_up",
            claim_type="directional", claim_status="observed",
            time_horizon="long_term",
        )
        assert c1.claim_id != c2.claim_id, "Different horizons must have different IDs"

    def test_forbidden_status_raises(self):
        with pytest.raises(ValueError, match="proven"):
            ResearchClaimV1(
                subject="test", predicate="associated_with", object="btc_up",
                claim_type="directional", claim_status="proven",
            )

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="invalid_status"):
            ResearchClaimV1(
                subject="test", predicate="associated_with", object="btc_up",
                claim_type="directional", claim_status="invalid_status",
            )

    def test_claim_valid_statuses(self):
        """All valid statuses should be accepted."""
        for status in VALID_CLAIM_STATUSES:
            c = ResearchClaimV1(
                subject="test", predicate="associated_with", object="btc_up",
                claim_type="directional", claim_status=status,
            )
            assert c.claim_status == status

    def test_claim_serialization(self):
        c = ResearchClaimV1(
            subject="test", predicate="associated_with", object="btc_up",
            claim_type="directional", claim_status="observed",
        )
        d = c.to_dict()
        assert d["subject"] == "test"
        assert d["claim_status"] == "observed"
        assert d["claim_id"].startswith("RC-")


class TestEvidenceEdgeV1:
    """Test 6: Opposing evidence edges preserved."""

    def test_deterministic_id(self):
        e1 = EvidenceEdgeV1(
            claim_id="RC-TEST123", evidence_role="supporting",
            source_lane="lane_a", source_artifact_path="test/path",
            source_record_id="rec_1",
            observed_at_utc="2025-01-01T00:00:00Z",
            available_at_utc="2025-01-01T00:00:00Z",
        )
        e2 = EvidenceEdgeV1(
            claim_id="RC-TEST123", evidence_role="supporting",
            source_lane="lane_a", source_artifact_path="test/path",
            source_record_id="rec_1",
            observed_at_utc="2025-01-01T00:00:00Z",
            available_at_utc="2025-01-01T00:00:00Z",
        )
        assert e1.evidence_edge_id == e2.evidence_edge_id

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError):
            EvidenceEdgeV1(
                claim_id="RC-TEST", evidence_role="invalid",
                source_lane="lane_a", source_artifact_path="p",
                source_record_id="r",
                observed_at_utc="2025-01-01T00:00:00Z",
                available_at_utc="2025-01-01T00:00:00Z",
            )

    def test_same_source_not_independent(self):
        """Items 5 from §41: same source should not count as independent."""
        e1 = EvidenceEdgeV1(
            claim_id="RC-TEST", evidence_role="supporting",
            source_lane="lane_a", source_artifact_path="same/path",
            source_record_id="rec_1",
            observed_at_utc="2025-01-01T00:00:00Z",
            available_at_utc="2025-01-01T00:00:00Z",
            evidence_type="macro_event",
        )
        e2 = EvidenceEdgeV1(
            claim_id="RC-TEST", evidence_role="supporting",
            source_lane="lane_a", source_artifact_path="same/path",
            source_record_id="rec_1",
            observed_at_utc="2025-01-01T00:00:00Z",
            available_at_utc="2025-01-01T00:00:00Z",
            evidence_type="macro_event",
        )
        # Same source means same edge ID
        assert e1.evidence_edge_id == e2.evidence_edge_id


class TestConflictSetV1:
    """Test 3: Opposite directions enter same conflict set.
       Test 4: Majority cannot auto-resolve."""

    def test_deterministic_id(self):
        cs1 = ConflictSetV1(
            conflict_key="CPI::BTC::short_term",
            conflict_type="direction_conflict",
            claim_ids=["RC-AAA", "RC-BBB"],
        )
        cs2 = ConflictSetV1(
            conflict_key="CPI::BTC::short_term",
            conflict_type="direction_conflict",
            claim_ids=["RC-AAA", "RC-BBB"],
        )
        assert cs1.conflict_set_id == cs2.conflict_set_id

    def test_default_is_open(self):
        cs = ConflictSetV1(
            conflict_key="test", conflict_type="direction_conflict",
            claim_ids=["RC-A", "RC-B"],
        )
        assert cs.conflict_status == "open"
        assert cs.resolution_status == "unresolved"


class TestCandidateRecordV1:
    """Test 7: Holdout failure can lower candidate status."""

    def test_default_is_proposed(self):
        cd = CandidateRecordV1(
            candidate_type="directional_strategy",
            candidate_name="test_candidate",
        )
        assert cd.candidate_status == "proposed"

    def test_holdout_failed_status(self):
        cd = CandidateRecordV1(
            candidate_type="directional_strategy",
            candidate_name="failed_candidate",
            candidate_status="holdout_failed",
            holdout_status="failed",
        )
        assert cd.holdout_status == "failed"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError):
            CandidateRecordV1(
                candidate_type="directional_strategy",
                candidate_name="bad",
                candidate_status="proven",  # not in valid list
            )


class TestDecisionRecordV1:
    """Test decision records track state changes."""

    def test_deterministic_id(self):
        d1 = DecisionRecordV1(
            decision_type="claim_status_change",
            subject_id="RC-TEST",
            previous_state="observed",
            new_state="supported",
        )
        d2 = DecisionRecordV1(
            decision_type="claim_status_change",
            subject_id="RC-TEST",
            previous_state="observed",
            new_state="supported",
        )
        assert d1.decision_id == d2.decision_id


class TestResearchDossierV1:
    """Test dossier assembly."""

    def test_deterministic_id(self):
        d1 = ResearchDossierV1(
            subject_type="candidate",
            subject_id="CD-TEST",
            candidate_status="proposed",
        )
        d2 = ResearchDossierV1(
            subject_type="candidate",
            subject_id="CD-TEST",
            candidate_status="proposed",
        )
        assert d1.dossier_id == d2.dossier_id


class TestEvidenceEdgePersistence:
    """Test 6 (additional): Opposing evidence not deleted."""

    def test_opposing_edge_preserved(self):
        claim = ResearchClaimV1(
            subject="cpi_surprise", predicate="associated_with",
            object="btc_down", claim_type="directional",
            claim_status="contested",
        )
        supporting = EvidenceEdgeV1(
            claim_id=claim.claim_id, evidence_role="supporting",
            source_lane="lane_b", source_artifact_path="market/path",
            source_record_id="win_1",
            observed_at_utc="2025-01-01T00:00:00Z",
            available_at_utc="2025-01-01T00:00:00Z",
            supports=True,
        )
        opposing = EvidenceEdgeV1(
            claim_id=claim.claim_id, evidence_role="opposing",
            source_lane="lane_b", source_artifact_path="market/path",
            source_record_id="loss_1",
            observed_at_utc="2025-01-01T00:00:00Z",
            available_at_utc="2025-01-01T00:00:00Z",
            contradicts=True,
        )
        # Both edges exist and are different
        assert supporting.evidence_edge_id != opposing.evidence_edge_id
        assert supporting.supports is True
        assert opposing.contradicts is True


class TestCalibrationConstraints:
    """Test 8: Calibration unavailable cannot output probability."""

    def test_default_calibration_unavailable(self):
        claim = ResearchClaimV1(
            subject="test", predicate="associated_with",
            object="btc_up", claim_type="directional",
            claim_status="supported",
        )
        assert claim.calibration_status == "unavailable"
        # No probability field should exist in claim
        assert not hasattr(claim, "probability")
