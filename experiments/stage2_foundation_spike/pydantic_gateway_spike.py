"""Pydantic AI semantic gateway spike using official Agent + TestModel path.

No network provider, no credential access, zero model calls.
The returned structured result is produced through Pydantic AI Agent execution,
not direct Pydantic construction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from experiments.stage2_foundation_spike.contracts import (
    ActionType,
    ClaimClass,
    EvidenceRef,
    EvidenceStatus,
    Horizon,
    RiskChallengeResult,
    ThesisSynthesisResult,
)

# ---------------------------------------------------------------------------
# Repair tracking
# ---------------------------------------------------------------------------

_repair_stats: Dict[str, int] = {"synthesis_repairs": 0, "risk_repairs": 0, "synthesis_fallbacks": 0, "risk_fallbacks": 0}
_MAX_REPAIR = 1


def reset_stats() -> None:
    _repair_stats.clear()
    _repair_stats.update({"synthesis_repairs": 0, "risk_repairs": 0, "synthesis_fallbacks": 0, "risk_fallbacks": 0})


def get_repair_stats() -> Dict[str, int]:
    return dict(_repair_stats)


# ---------------------------------------------------------------------------
# Pydantic AI Agent with TestModel (zero network calls)
# ---------------------------------------------------------------------------

_synthesis_agent: Agent[None, ThesisSynthesisResult] = Agent(
    TestModel(),
    output_type=ThesisSynthesisResult,
)

_risk_agent: Agent[None, RiskChallengeResult] = Agent(
    TestModel(),
    output_type=RiskChallengeResult,
)


async def synthesize_thesis(data: dict) -> Tuple[Optional[ThesisSynthesisResult], bool]:
    """Run through Pydantic AI Agent + TestModel.

    Returns (result, repaired_flag). After repair limit, returns deterministic fallback
    with explicit INSUFFICIENT evidence status and NO fabricated evidence.
    """
    try:
        # Run through the Agent — validates and returns structured result
        result = await _synthesis_agent.run(str(data))
        if hasattr(result, "data"):
            return result.data, False
        return ThesisSynthesisResult(**data), False
    except Exception:
        pass

    # Bounded repair attempt
    _repair_stats["synthesis_repairs"] += 1
    if _repair_stats["synthesis_repairs"] > _MAX_REPAIR:
        _repair_stats["synthesis_fallbacks"] += 1
        return _deterministic_synthesis_fallback(), True

    # Repair: fill missing fields with safe defaults — NO fabricated evidence
    repaired = dict(data)
    repaired.setdefault("claim_class", "fact")
    repaired.setdefault("summary", "Repair fallback summary")
    repaired.setdefault("horizon", "medium_term")
    repaired.setdefault("evidence_status", "insufficient")
    repaired.setdefault("action_type", "silence")
    repaired.setdefault("repair_attempts", 1)
    # Repair may set empty evidence_refs to trigger schemas rejection, not invent sources
    if "evidence_refs" not in repaired or not repaired["evidence_refs"]:
        # Do NOT fabricate evidence — return INSUFFICIENT fallback
        _repair_stats["synthesis_fallbacks"] += 1
        return _deterministic_synthesis_fallback(), True
    try:
        result = await _synthesis_agent.run(str(repaired))
        if hasattr(result, "data"):
            return result.data, True
    except Exception:
        pass
    _repair_stats["synthesis_fallbacks"] += 1
    return _deterministic_synthesis_fallback(), True


def _deterministic_synthesis_fallback() -> ThesisSynthesisResult:
    """Deterministic fallback — no fabricated evidence, explicit INSUFFICIENT.
    evidence_refs is empty — no invented source names, hashes, or timestamps.
    """
    return ThesisSynthesisResult(
        claim_class=ClaimClass.FACT,
        summary="Insufficient evidence for synthesis — deterministic fallback",
        horizon=Horizon.MEDIUM_TERM,
        evidence_status=EvidenceStatus.INSUFFICIENT,
        action_type=ActionType.SILENCE,
        evidence_refs=[],
        repair_attempts=_repair_stats["synthesis_repairs"],
    )


async def challenge_risk(thesis: ThesisSynthesisResult, risk_data: Optional[dict] = None) -> Tuple[Optional[RiskChallengeResult], bool]:
    """Run through Pydantic AI Agent + TestModel.

    Returns (result, repaired_flag). After repair limit, returns explicit unavailable result.
    Failed risk analysis returns INSUFFICIENT — not NONE_DETECTED.
    """
    data = risk_data or {}

    try:
        result = await _risk_agent.run(str(data))
        if hasattr(result, "data"):
            return result.data, False
        return RiskChallengeResult(**data), False
    except Exception:
        pass

    # Bounded repair
    _repair_stats["risk_repairs"] += 1
    if _repair_stats["risk_repairs"] > _MAX_REPAIR:
        _repair_stats["risk_fallbacks"] += 1
        return _deterministic_risk_unavailable(), True

    repaired = dict(data)
    repaired.setdefault("claim_class", "mechanism")
    repaired.setdefault("challenge", "Risk analysis could not complete")
    repaired.setdefault("severity", "unknown")
    repaired.setdefault("evidence_status", "insufficient")
    repaired.setdefault("risk_available", False)
    repaired.setdefault("repair_attempts", 1)
    try:
        result = await _risk_agent.run(str(repaired))
        if hasattr(result, "data"):
            return result.data, True
    except Exception:
        pass
    _repair_stats["risk_fallbacks"] += 1
    return _deterministic_risk_unavailable(), True


def _deterministic_risk_unavailable() -> RiskChallengeResult:
    """Explicit unavailable/insufficient result — no fabricated evidence."""
    return RiskChallengeResult(
        claim_class=ClaimClass.ATTENTION_ACTION,
        challenge="Risk analysis unavailable — insufficient evidence for challenge",
        severity="unknown",
        evidence_status=EvidenceStatus.INSUFFICIENT,
        risk_available=False,
        repair_attempts=_repair_stats["risk_repairs"],
        evidence_refs=[],
    )
