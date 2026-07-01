"""Test contracts with exact exception types."""

import pytest
from pydantic import ValidationError
from experiments.stage2_foundation_spike.contracts import (
    ThesisSynthesisResult,
    RiskChallengeResult,
    EvidenceRef,
    EvidenceStatus,
    ClaimClass,
    Horizon,
    ActionType,
)


@pytest.fixture
def valid_evidence():
    return EvidenceRef(source="test_source", content_hash="abc123", retrieved_at="2025-01-01T00:00:00Z")


class TestThesisSynthesisResult:
    def test_valid_minimal(self, valid_evidence):
        r = ThesisSynthesisResult(
            claim_class="fact",
            summary="Valid synthesis",
            evidence_refs=[valid_evidence],
            horizon="short_term",
            evidence_status="supported",
            action_type="log",
        )
        assert r.claim_class == ClaimClass.FACT
        assert r.evidence_status == EvidenceStatus.SUPPORTED

    def test_empty_evidence_rejected(self):
        with pytest.raises(ValidationError):
            ThesisSynthesisResult(
                claim_class="fact",
                summary="No evidence",
                evidence_refs=[],
                horizon="medium_term",
                evidence_status="insufficient",
                action_type="silence",
            )

    def test_invalid_horizon_rejected(self, valid_evidence):
        with pytest.raises(ValidationError):
            ThesisSynthesisResult(
                claim_class="fact",
                summary="Bad horizon",
                evidence_refs=[valid_evidence],
                horizon="INVALID",
                evidence_status="tentative",
                action_type="flag",
            )

    def test_no_lifecycle_state_field(self):
        """Synthesis result must not contain lifecycle state."""
        fields = ThesisSynthesisResult.model_fields
        assert "lifecycle_state" not in fields
        assert "status" not in fields
        assert "transition" not in fields

    def test_action_type_safe_only(self, valid_evidence):
        for safe_action in ["log", "flag", "review", "escalate", "silence"]:
            r = ThesisSynthesisResult(
                claim_class="fact",
                summary=f"action {safe_action}",
                evidence_refs=[valid_evidence],
                horizon="long_term",
                evidence_status="tentative",
                action_type=safe_action,
            )
            assert r.action_type.value == safe_action

    def test_dangerous_action_rejected(self, valid_evidence):
        for bad in ["trade", "publish", "execute", "wallet", "send", "notify", "transition"]:
            with pytest.raises(ValidationError):
                ThesisSynthesisResult(
                    claim_class="fact",
                    summary="bad",
                    evidence_refs=[valid_evidence],
                    horizon="short_term",
                    evidence_status="blocked",
                    action_type=bad,
                )


class TestRiskChallengeResult:
    def test_valid_minimal(self, valid_evidence):
        r = RiskChallengeResult(
            claim_class="mechanism",
            challenge="Test challenge",
            evidence_refs=[valid_evidence],
            evidence_status="tentative",
        )
        assert r.claim_class == ClaimClass.MECHANISM

    def test_invalid_claim_class_rejected(self, valid_evidence):
        with pytest.raises(ValidationError):
            RiskChallengeResult(
                claim_class="fact",
                challenge="Should fail",
                evidence_refs=[valid_evidence],
                evidence_status="insufficient",
            )

    def test_failed_risk_not_none_detected(self, valid_evidence):
        """Failed risk analysis must not fall back to NONE_DETECTED."""
        r = RiskChallengeResult(
            claim_class="attention_action",
            challenge="Risk unavailable",
            evidence_status="insufficient",
            risk_available=False,
        )
        assert r.risk_available is False
        assert r.severity == "unknown"

    def test_no_dangerous_field(self):
        fields = RiskChallengeResult.model_fields
        assert "trade_action" not in fields
        assert "publish" not in fields
        assert "wallet" not in fields


class TestEvidenceStatus:
    def test_all_bands_valid(self, valid_evidence):
        for status in ["blocked", "insufficient", "tentative", "supported", "strong"]:
            r = ThesisSynthesisResult(
                claim_class="fact",
                summary=f"status {status}",
                evidence_refs=[valid_evidence],
                horizon="immediate",
                evidence_status=status,
                action_type="log",
            )
            assert r.evidence_status.value == status

    def test_no_numeric_confidence(self, valid_evidence):
        r = ThesisSynthesisResult(
            claim_class="fact",
            summary="no numeric",
            evidence_refs=[valid_evidence],
            horizon="immediate",
            evidence_status="insufficient",
            action_type="log",
        )
        assert not hasattr(r, "confidence")
        assert not hasattr(r, "confidence_band")


class TestActionType:
    def test_only_safe_actions(self):
        values = {m.value for m in ActionType}
        assert values == {"log", "flag", "review", "escalate", "silence"}
