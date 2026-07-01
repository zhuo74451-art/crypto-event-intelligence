"""Test contracts module with correct API."""

import pytest
from experiments.stage2_foundation_spike.contracts import (
    ThesisSynthesisResult,
    RiskChallengeResult,
    EvidenceRef,
    EvidenceSource,
    ClaimClass,
    Horizon,
    ActionType,
    OriginAuthority,
)


@pytest.fixture
def valid_evidence_ref():
    return EvidenceRef(
        source=EvidenceSource(authority="trusted"),
        content_hash="abc123",
        retrieved_at="2025-01-01T00:00:00Z",
    )


class TestThesisSynthesisResult:
    def test_valid_minimal(self, valid_evidence_ref):
        result = ThesisSynthesisResult(
            claim_class="materiality",
            summary="Test summary",
            evidence_refs=[valid_evidence_ref],
            horizon="short_term",
            confidence_band=0.7,
        )
        assert result.claim_class == ClaimClass.MATERIALITY

    def test_empty_evidence_rejected(self):
        with pytest.raises(Exception):
            ThesisSynthesisResult(
                claim_class="materiality",
                summary="Test",
                evidence_refs=[],
                horizon="short_term",
                confidence_band=0.5,
            )


class TestRiskChallengeResult:
    def test_valid_minimal(self, valid_evidence_ref):
        result = RiskChallengeResult(
            claim_class="counter_evidence",
            challenge="Counter argument",
            severity="medium",
            evidence_refs=[valid_evidence_ref],
        )
        assert result.claim_class == ClaimClass.COUNTER_EVIDENCE

    def test_invalid_claim_class_rejected(self, valid_evidence_ref):
        with pytest.raises(Exception):
            RiskChallengeResult(
                claim_class="invalid_class_name",
                challenge="Test",
                severity="low",
                evidence_refs=[valid_evidence_ref],
            )


class TestActionType:
    def test_valid_members(self):
        assert ActionType.LOG.value == "log"
        assert ActionType.FLAG.value == "flag"
        assert ActionType.REVIEW.value == "review"
        assert ActionType.ESCALATE.value == "escalate"
        assert ActionType.SILENCE.value == "silence"

    def test_no_dangerous_actions(self):
        dangerous = {"trade", "publish", "execute", "wallet", "send", "notify", "transition"}
        for member in ActionType:
            assert member.value not in dangerous

    def test_invalid_string_rejected(self):
        with pytest.raises(Exception):
            ActionType("trade")


class TestEvidenceRef:
    def test_missing_evidence_rejected(self, valid_evidence_ref):
        with pytest.raises(Exception):
            ThesisSynthesisResult(
                claim_class="materiality",
                summary="Test",
                evidence_refs=[],
                horizon="short_term",
                confidence_band=0.5,
            )
