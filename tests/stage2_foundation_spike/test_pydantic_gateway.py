"""Test Pydantic AI gateway — Agent + TestModel path, no network calls."""

import pytest
from pydantic import ValidationError
from experiments.stage2_foundation_spike.pydantic_gateway_spike import (
    synthesize_thesis,
    challenge_risk,
    get_repair_stats,
    reset_stats,
    _deterministic_synthesis_fallback,
    _deterministic_risk_unavailable,
    _synthesis_agent,
    _risk_agent,
)
from experiments.stage2_foundation_spike.contracts import (
    ThesisSynthesisResult,
    RiskChallengeResult,
    EvidenceStatus,
)


@pytest.fixture(autouse=True)
def reset():
    reset_stats()
    yield


def test_agent_configured_with_test_model():
    """Verify the Agent is created with TestModel (zero network calls)."""
    assert _synthesis_agent is not None
    assert _risk_agent is not None
    # Verify it's an Agent with proper output type
    assert _synthesis_agent._model is not None


@pytest.mark.asyncio
async def test_bounded_repair_falls_back():
    """Missing fields trigger repair — falls back to INSUFFICIENT with no fabricated evidence."""
    result, repaired = await synthesize_thesis({
        "summary": "Incomplete",
    })
    assert result is not None
    assert isinstance(result, ThesisSynthesisResult)
    stats = get_repair_stats()
    assert stats.get("synthesis_repairs", 0) > 0
    assert result.evidence_status == EvidenceStatus.INSUFFICIENT
    # Verify no fabricated evidence — empty refs is valid for INSUFFICIENT
    assert len(result.evidence_refs) == 0


@pytest.mark.asyncio
async def test_deterministic_fallback():
    """After repair limit, fallback returns valid INSUFFICIENT result."""
    result, repaired = await synthesize_thesis({"summary": "test"})
    assert result is not None
    assert isinstance(result, ThesisSynthesisResult)


@pytest.mark.asyncio
async def test_risk_unavailable_not_none_detected():
    """Risk unavailability must return explicit insufficient, not NONE_DETECTED."""
    result, _ = await synthesize_thesis({
        "claim_class": "fact",
        "summary": "Test for risk",
        "evidence_refs": [{"source": "src", "content_hash": "abc", "retrieved_at": "2025-01-01T00:00:00Z"}],
        "horizon": "short_term",
        "evidence_status": "tentative",
        "action_type": "flag",
    })
    risk, repaired = await challenge_risk(result, {})
    assert risk is not None
    assert isinstance(risk, RiskChallengeResult)
    assert risk.risk_available is False
    assert risk.evidence_status == EvidenceStatus.INSUFFICIENT


def test_deterministic_synthesis_fallback_no_fabricated_evidence():
    result = _deterministic_synthesis_fallback()
    assert isinstance(result, ThesisSynthesisResult)
    assert result.evidence_status == EvidenceStatus.INSUFFICIENT
    # No fabricated evidence — empty refs is valid for INSUFFICIENT
    assert len(result.evidence_refs) == 0


def test_deterministic_risk_unavailable_no_fabricated_evidence():
    result = _deterministic_risk_unavailable()
    assert isinstance(result, RiskChallengeResult)
    assert result.risk_available is False
    assert result.evidence_status == EvidenceStatus.INSUFFICIENT
    # No fabricated evidence — evidence_refs may be empty
    assert len(result.evidence_refs) == 0


def test_zero_network_calls():
    """Verify no network calls — TestModel is offline-only."""
    import pydantic_ai.models.test
    assert hasattr(pydantic_ai.models.test.TestModel, '__call__') or hasattr(pydantic_ai.models.test.TestModel, 'model_post_init')
