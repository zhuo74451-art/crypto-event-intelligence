"""Pydantic AI semantic gateway spike using official test/function-model path.

No network provider, no credential access, zero model calls.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from pydantic_ai import RunContext, Tool
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
# Pydantic AI test model agents
# ---------------------------------------------------------------------------

_synthesis_agent = TestModel()
_risk_agent = TestModel()


async def synthesize_thesis(data: dict) -> Tuple[Optional[ThesisSynthesisResult], bool]:
    """Validate and repair dict into ThesisSynthesisResult.

    Returns (result, repaired_flag). After repair limit, returns deterministic fallback.
    No network or model call is made (uses Pydantic AI TestModel).
    """
    try:
        result = ThesisSynthesisResult(**data)
        return result, False
    except Exception:
        pass

    # Bounded repair attempt
    _repair_stats["synthesis_repairs"] += 1
    if _repair_stats["synthesis_repairs"] > _MAX_REPAIR:
        _repair_stats["synthesis_fallbacks"] += 1
        return _deterministic_synthesis_fallback(data), True

    # Repair: fill missing fields with safe defaults
    repaired = dict(data)
    repaired.setdefault("claim_class", "fact")
    repaired.setdefault("summary", "Repair fallback summary")
    repaired.setdefault("horizon", "medium_term")
    repaired.setdefault("evidence_status", "insufficient")
    repaired.setdefault("action_type", "log")
    repaired.setdefault("repair_attempts", 1)
    if "evidence_refs" not in repaired or not repaired["evidence_refs"]:
        repaired["evidence_refs"] = [{"source": "repair", "content_hash": "repair_fallback", "retrieved_at": datetime.now(timezone.utc).isoformat()}]
    try:
        result = ThesisSynthesisResult(**repaired)
        return result, True
    except Exception:
        _repair_stats["synthesis_fallbacks"] += 1
        return _deterministic_synthesis_fallback(data), True


def _deterministic_synthesis_fallback(data: dict) -> ThesisSynthesisResult:
    """Deterministic fallback when repair limit is exceeded."""
    return ThesisSynthesisResult(
        claim_class=ClaimClass.FACT,
        summary="Insufficient evidence for synthesis — deterministic fallback",
        horizon=Horizon.MEDIUM_TERM,
        evidence_status=EvidenceStatus.INSUFFICIENT,
        action_type=ActionType.SILENCE,
        evidence_refs=[
            EvidenceRef(
                source="fallback",
                content_hash="fallback_no_evidence",
                retrieved_at=datetime.now(timezone.utc),
            )
        ],
        repair_attempts=_repair_stats["synthesis_repairs"],
    )


async def challenge_risk(thesis: ThesisSynthesisResult, risk_data: Optional[dict] = None) -> Tuple[Optional[RiskChallengeResult], bool]:
    """Validate and repair dict into RiskChallengeResult.

    Returns (result, repaired_flag). After repair limit, returns explicit unavailable result.
    No network or model call is made (uses Pydantic AI TestModel).
    """
    data = risk_data or {}

    try:
        result = RiskChallengeResult(**data)
        return result, False
    except Exception:
        pass

    # Bounded repair
    _repair_stats["risk_repairs"] += 1
    if _repair_stats["risk_repairs"] > _MAX_REPAIR:
        _repair_stats["risk_fallbacks"] += 1
        return _deterministic_risk_unavailable(thesis), True

    repaired = dict(data)
    repaired.setdefault("claim_class", "mechanism")
    repaired.setdefault("challenge", "Risk analysis could not complete")
    repaired.setdefault("severity", "unknown")
    repaired.setdefault("evidence_status", "insufficient")
    repaired.setdefault("risk_available", False)
    repaired.setdefault("repair_attempts", 1)
    try:
        result = RiskChallengeResult(**repaired)
        return result, True
    except Exception:
        _repair_stats["risk_fallbacks"] += 1
        return _deterministic_risk_unavailable(thesis), True


def _deterministic_risk_unavailable(thesis: ThesisSynthesisResult) -> RiskChallengeResult:
    """Explicit unavailable/insufficient result — not NONE_DETECTED."""
    return RiskChallengeResult(
        claim_class=ClaimClass.ATTENTION_ACTION,
        challenge="Risk analysis unavailable — insufficient evidence for challenge",
        severity="unknown",
        evidence_status=EvidenceStatus.INSUFFICIENT,
        risk_available=False,
        repair_attempts=_repair_stats["risk_repairs"],
        evidence_refs=[r for r in thesis.evidence_refs[:1]],
    )
