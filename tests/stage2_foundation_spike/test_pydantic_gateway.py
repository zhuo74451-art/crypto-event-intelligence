"""Test Pydantic AI gateway — synchronous versions (no async dependency)."""

import pytest
from pydantic import ValidationError
from experiments.stage2_foundation_spike.pydantic_gateway_spike import (
    synthesize_thesis,
    challenge_risk,
    get_repair_stats,
    reset_stats,
    _deterministic_synthesis_fallback,
    _deterministic_risk_unavailable,
)
from experiments.stage2_foundation_spike.contracts import (
    ThesisSynthesisResult,
    RiskChallengeResult,
    EvidenceStatus,
)
from experiments.stage2_foundation_spike.pydantic_gateway_spike import _repair_stats
import json


@pytest.fixture(autouse=True)
def reset():
    reset_stats()
    yield


@pytest.mark.asyncio
async def test_valid_synthesis():
    result, repaired = await synthesize_thesis({
        "claim_class": "fact",
        "summary": "Valid test",
        "evidence_refs": [{"source": "src", "content_hash": "abc", "retrieved_at": "2025-01-01T00:00:00Z"}],
        "horizon": "short_term",
        "evidence_status": "supported",
        "action_type": "log",
    })
    assert result is not None
    assert isinstance(result, ThesisSynthesisResult)
    assert not repaired


@pytest.mark.asyncio
async def test_missing_evidence_rejected():
    result, repaired = await synthesize_thesis({
        "claim_class": "fact",
        "summary": "No evidence",
        "evidence_refs": [],
        "horizon": "short_term",
        "evidence_status": "supported",
        "action_type": "log",
    })
    # Should trigger repair/fallback, not crash
    assert result is not None


@pytest.mark.asyncio
async def test_bounded_repair():
    result, repaired = await synthesize_thesis({
        "summary": "Incomplete",
    })
    assert result is not None
    stats = get_repair_stats()
    assert stats.get("synthesis_repairs", 0) > 0


@pytest.mark.asyncio
async def test_deterministic_fallback():
    await synthesize_thesis({"summary": "test"})
    result, repaired = await synthesize_thesis({"summary": "test"})
    assert result is not None
    assert isinstance(result, ThesisSynthesisResult)


@pytest.mark.asyncio
async def test_risk_unavailable_not_none_detected():
    valid_result, _ = await synthesize_thesis({
        "claim_class": "fact",
        "summary": "Test for risk",
        "evidence_refs": [{"source": "src", "content_hash": "abc", "retrieved_at": "2025-01-01T00:00:00Z"}],
        "horizon": "short_term",
        "evidence_status": "tentative",
        "action_type": "flag",
    })
    risk, repaired = await challenge_risk(valid_result, {})
    assert risk is not None
    assert isinstance(risk, RiskChallengeResult)
    assert risk.risk_available is False
    assert risk.evidence_status == EvidenceStatus.INSUFFICIENT


def test_deterministic_synthesis_fallback_returns_valid():
    from datetime import datetime, timezone
    from experiments.stage2_foundation_spike.contracts import EvidenceRef
    result = _deterministic_synthesis_fallback({})
    assert isinstance(result, ThesisSynthesisResult)
    assert result.evidence_status == EvidenceStatus.INSUFFICIENT


def test_deterministic_risk_unavailable_returns_valid():
    from datetime import datetime, timezone
    from experiments.stage2_foundation_spike.contracts import EvidenceRef
    thesis = ThesisSynthesisResult(
        claim_class="fact",
        summary="Test",
        evidence_refs=[EvidenceRef(source="src", content_hash="abc", retrieved_at=datetime.now(timezone.utc))],
        horizon="short_term",
        evidence_status="tentative",
        action_type="flag",
    )
    result = _deterministic_risk_unavailable(thesis)
    assert isinstance(result, RiskChallengeResult)
    assert result.risk_available is False
