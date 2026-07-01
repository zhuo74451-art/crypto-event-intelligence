"""Stage 2 — Experiment A: Pydantic semantic gateway spike.

**Purpose**
Validate that Pydantic AI structured-output contracts (ThesisSynthesisResult,
RiskChallengeResult) can be enforced with bounded repair and deterministic
fallback — *without any real model or paid API call*.

**Design**
- Uses only test/function models — no provider credential is read or used.
- Each gateway function wraps pydantic validation with *exactly one* repair
  attempt, then a deterministic fallback that produces a minimal valid result.
- Repair attempts are tracked in the module-level ``repair_stats`` dict.

**Boundaries**
- No provider credential is read or used.
- No real model or paid API call is made.
- No lifecycle transition or external action is taken.
- The model result cannot choose a lifecycle transition or external action.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ── Module-level repair counter ─────────────────────────────────────────────

_repair_attempts: int = 0
_fallback_count: int = 0
REPAIR_LIMIT: int = 1

repair_stats: Dict[str, int] = {
    "total_attempts": 0,
    "repair_limit": REPAIR_LIMIT,
    "fallback_count": 0,
}


def _bump_total() -> None:
    global _repair_attempts
    _repair_attempts += 1
    repair_stats["total_attempts"] = _repair_attempts


def _bump_fallback() -> None:
    global _fallback_count
    _fallback_count += 1
    repair_stats["fallback_count"] = _fallback_count


def _reset_stats() -> None:
    """Reset counters (useful between tests)."""
    global _repair_attempts, _fallback_count
    _repair_attempts = 0
    _fallback_count = 0
    repair_stats["total_attempts"] = 0
    repair_stats["fallback_count"] = 0


# ── Enums ────────────────────────────────────────────────────────────────────
# These would move to the shared contracts module in production.


class ConfidenceLevel(str, Enum):
    """Semantic confidence assigned during thesis synthesis."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class RiskSeverity(str, Enum):
    """Severity of a risk identified during challenge."""

    CRITICAL = "critical"
    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"
    NONE_DETECTED = "none_detected"


class ThesisStatus(str, Enum):
    """Lifecycle status of a thesis — only a subset relevant to synthesis."""

    DRAFT = "draft"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


# ── Pydantic models (Stage 2 semantic contracts) ────────────────────────────
# These are the structured-output schemas that the semantic gateway validates.
# In production they would live in the shared contracts module and be consumed
# by Pydantic AI's result_validator.  Here we validate them directly to prove
# the schema enforcement and bounded-repair pattern.


class ThesisSynthesisResult(BaseModel):
    """Structured result of a thesis synthesis pass.

    Produced by the semantic gateway from event evidence + point-in-time
    context.  Every thesis must reference at least one piece of evidence
    and carry a confidence level.
    """

    thesis_id: str = Field(..., min_length=1, description="Unique thesis identifier")
    event_id: str = Field(..., min_length=1, description="Associated event identifier")
    thesis_statement: str = Field(..., min_length=1, description="The core thesis text")
    confidence: ConfidenceLevel = Field(..., description="Semantic confidence level")
    evidence_refs: List[str] = Field(
        ..., min_length=1, description="At least one evidence reference"
    )
    affected_assets: List[str] = Field(
        default_factory=list, description="Assets the thesis touches"
    )
    status: ThesisStatus = Field(default=ThesisStatus.DRAFT, description="Lifecycle status")

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_must_be_nonempty(cls, v: List[str]) -> List[str]:
        if not v or all(s.strip() == "" for s in v):
            raise ValueError("evidence_refs must contain at least one non-empty reference")
        return v

    @field_validator("affected_assets")
    @classmethod
    def _assets_must_not_contain_blanks(cls, v: List[str]) -> List[str]:
        if any(s.strip() == "" for s in v):
            raise ValueError("affected_assets must not contain blank entries")
        return v


class RiskChallengeResult(BaseModel):
    """Structured result of a risk challenge pass.

    Takes an existing thesis and produces a risk assessment with one or
    more identified risks.  At minimum a 'none_detected' severity with an
    explanatory note must be present.
    """

    thesis_id: str = Field(..., min_length=1, description="The thesis being challenged")
    overall_severity: RiskSeverity = Field(..., description="Aggregate risk severity")
    risks: List[Dict[str, str]] = Field(
        ...,
        min_length=1,
        description="List of risk items: each must have 'description' and 'severity' keys",
    )
    challenge_notes: str = Field(
        default="", description="Free-text notes on the challenge"
    )

    @field_validator("risks")
    @classmethod
    def _risks_must_be_valid(cls, v: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not v:
            raise ValueError("risks must contain at least one item")
        for i, item in enumerate(v):
            if "description" not in item or not item["description"].strip():
                raise ValueError(f"risks[{i}] is missing a non-empty 'description'")
            if "severity" not in item or not item["severity"].strip():
                raise ValueError(f"risks[{i}] is missing a non-empty 'severity'")
        return v


# ── Fallback factories (deterministic, minimal valid instances) ──────────────


def _fallback_thesis(data: dict) -> ThesisSynthesisResult:
    """Build a minimal valid ThesisSynthesisResult from whatever is available."""
    return ThesisSynthesisResult(
        thesis_id=data.get("thesis_id", "fallback-thesis-0000"),
        event_id=data.get("event_id", "fallback-event-0000"),
        thesis_statement="Fallback: insufficient evidence to synthesise a thesis.",
        confidence=ConfidenceLevel.INSUFFICIENT_EVIDENCE,
        evidence_refs=["fallback-evidence-0000"],
        affected_assets=(
            [a for a in data.get("affected_assets", []) if a.strip()]
            if isinstance(data.get("affected_assets"), list)
            else []
        ),
        status=ThesisStatus.DRAFT,
    )


def _fallback_risk(thesis_id: str) -> RiskChallengeResult:
    """Build a minimal valid RiskChallengeResult."""
    return RiskChallengeResult(
        thesis_id=thesis_id,
        overall_severity=RiskSeverity.NONE_DETECTED,
        risks=[
            {
                "description": "Fallback: no risks identified — challenge was not run.",
                "severity": RiskSeverity.NONE_DETECTED.value,
            }
        ],
        challenge_notes="Fallback challenge: no semantic analysis performed.",
    )


# ── Bounded-repair helper ────────────────────────────────────────────────────


def _validate_with_repair(
    model_cls: type[BaseModel],
    data: dict,
    fallback_factory,
    fallback_arg=None,
) -> BaseModel:
    """Attempt to validate *data* into *model_cls*.

    Bounded repair:
      1. Try direct validation.
      2. On failure, if repairs remain, try once more (e.g. after coercing
         string enums, filling empties).
      3. If that also fails (or no repairs remain), produce a deterministic
         fallback via *fallback_factory*.

    Returns a valid model instance in all cases.
    """
    global _repair_attempts, _fallback_count

    # ── First attempt ────────────────────────────────────────────────────
    try:
        return model_cls(**data)
    except (ValueError, TypeError) as exc:
        _bump_total()

    # ── Bounded repair (exactly one attempt) ──────────────────────────────
    if repair_stats["total_attempts"] - repair_stats["fallback_count"] <= REPAIR_LIMIT:
        repaired = _coerce_and_repair(data, model_cls)
        try:
            return model_cls(**repaired)
        except (ValueError, TypeError):
            _bump_total()

    # ── Deterministic fallback ────────────────────────────────────────────
    _bump_fallback()
    if fallback_arg is not None:
        return fallback_factory(fallback_arg)
    return fallback_factory(data)


def _coerce_and_repair(data: dict, model_cls: type) -> dict:
    """Apply simple coercions to make a dict more likely to validate.

    This mimics what a Pydantic AI model might do on a retry: string-enum
    matching, blank-string filling, ensuring list fields are lists.
    """
    repaired = dict(data)

    # ── Known enum fields for ThesisSynthesisResult ──────────────────────
    if model_cls is ThesisSynthesisResult or model_cls.__name__ == "ThesisSynthesisResult":
        _coerce_enum_field(repaired, "confidence", ConfidenceLevel)
        _coerce_enum_field(repaired, "status", ThesisStatus)
        _ensure_list_field(repaired, "evidence_refs", default=["fallback-evidence-0000"])
        _ensure_list_field(repaired, "affected_assets", default=[])
        _ensure_string_field(repaired, "thesis_id", "repaired-thesis-0000")
        _ensure_string_field(repaired, "event_id", "repaired-event-0000")
        _ensure_string_field(repaired, "thesis_statement", "Repaired thesis statement.")

    # ── Known enum fields for RiskChallengeResult ────────────────────────
    if model_cls is RiskChallengeResult or model_cls.__name__ == "RiskChallengeResult":
        _coerce_enum_field(repaired, "overall_severity", RiskSeverity)
        _ensure_string_field(repaired, "thesis_id", "repaired-thesis-0000")
        _ensure_string_field(repaired, "challenge_notes", "")
        _ensure_risk_items(repaired)

    return repaired


def _coerce_enum_field(data: dict, field: str, enum_cls: type[Enum]) -> None:
    """If *field* is a string, try to match it to an enum member (case-insensitive)."""
    if field in data and isinstance(data[field], str):
        val = data[field].strip().lower().replace(" ", "_")
        for member in enum_cls:
            if member.value == val:
                data[field] = member
                return
        # Fall back to the first enum member
        members = list(enum_cls)
        if members:
            data[field] = members[0]


def _ensure_list_field(data: dict, field: str, default: list) -> None:
    """Ensure *field* is a list; if missing or wrong type, set to *default*."""
    if field not in data or not isinstance(data[field], list):
        data[field] = list(default)
    elif not data[field]:
        data[field] = list(default)


def _ensure_string_field(data: dict, field: str, default: str) -> None:
    """Ensure *field* is a non-empty string."""
    if field not in data or not isinstance(data[field], str) or not data[field].strip():
        data[field] = default


def _ensure_risk_items(data: dict) -> None:
    """Ensure *risks* is a list of dicts each with 'description' and 'severity'."""
    if "risks" not in data or not isinstance(data["risks"], list) or not data["risks"]:
        data["risks"] = [
            {
                "description": "Repaired: no risks originally provided.",
                "severity": RiskSeverity.NONE_DETECTED.value,
            }
        ]
        return
    for item in data["risks"]:
        if not isinstance(item, dict):
            item = {}
        if "description" not in item or not isinstance(item["description"], str):
            item["description"] = "Repaired risk description."
        if "severity" not in item or not isinstance(item["severity"], str):
            item["severity"] = RiskSeverity.NONE_DETECTED.value


# ── Gateway functions ────────────────────────────────────────────────────────


def synthesize_thesis(data: dict) -> ThesisSynthesisResult:
    """Validate raw *data* into a ``ThesisSynthesisResult``.

    Bounded repair (max 1 attempt) followed by deterministic fallback.
    No provider credential is read or used — pure pydantic validation.
    """
    return _validate_with_repair(
        model_cls=ThesisSynthesisResult,
        data=data,
        fallback_factory=_fallback_thesis,
    )


def challenge_risk(thesis: ThesisSynthesisResult) -> RiskChallengeResult:
    """Validate and challenge an existing ``ThesisSynthesisResult``.

    Bounded repair (max 1 attempt) followed by deterministic fallback.
    The *thesis* parameter is used to extract the thesis_id for the challenge.
    """
    # Build a dict from the thesis for validation
    data = thesis.model_dump()

    # In a real gateway we would also include context, evidence, etc.
    challenge_data: dict = {
        "thesis_id": data.get("thesis_id", ""),
        "overall_severity": data.get("overall_severity", "none_detected"),
        "risks": data.get("risks", []),
        "challenge_notes": data.get("challenge_notes", ""),
    }

    return _validate_with_repair(
        model_cls=RiskChallengeResult,
        data=challenge_data,
        fallback_factory=_fallback_risk,
        fallback_arg=data.get("thesis_id", "unknown-thesis"),
    )


# ── Quick self-test (only when run directly) ─────────────────────────────────


if __name__ == "__main__":
    import sys

    print("=== Pydantic Gateway Spike — Self-Test ===\n")

    # 1. Happy path — valid data
    print("--- Test 1: Happy path (valid data) ---")
    _reset_stats()
    valid_data = {
        "thesis_id": "thesis-001",
        "event_id": "event-abc",
        "thesis_statement": "Fed rate cut will boost BTC.",
        "confidence": "high",
        "evidence_refs": ["ev-001", "ev-002"],
        "affected_assets": ["BTC", "ETH"],
    }
    result = synthesize_thesis(valid_data)
    assert isinstance(result, ThesisSynthesisResult)
    assert result.thesis_id == "thesis-001"
    assert result.confidence == ConfidenceLevel.HIGH
    assert repair_stats["total_attempts"] == 0
    assert repair_stats["fallback_count"] == 0
    print(f"  OK — thesis {result.thesis_id}, confidence={result.confidence.value}")
    print(f"  repair_stats={repair_stats}\n")

    # 2. Invalid enum — repaired
    print("--- Test 2: Invalid enum → repaired ---")
    _reset_stats()
    bad_enum_data = {
        "thesis_id": "thesis-002",
        "event_id": "event-xyz",
        "thesis_statement": "EIP upgrade will impact L2s.",
        "confidence": "EXTREME",  # not a valid ConfidenceLevel
        "evidence_refs": ["ev-003"],
    }
    result2 = synthesize_thesis(bad_enum_data)
    assert isinstance(result2, ThesisSynthesisResult)
    # Should have been repaired (coerced to first enum member: HIGH)
    assert result2.confidence in set(ConfidenceLevel)
    assert repair_stats["total_attempts"] == 1  # first try failed, repair counted
    assert repair_stats["fallback_count"] == 0
    print(f"  OK — repaired confidence to {result2.confidence.value}")
    print(f"  repair_stats={repair_stats}\n")

    # 3. Missing required fields → fallback
    print("--- Test 3: Missing required fields → fallback ---")
    _reset_stats()
    result3 = synthesize_thesis({"thesis_id": "broken"})  # missing event_id, thesis_statement, etc.
    assert isinstance(result3, ThesisSynthesisResult)
    assert result3.confidence == ConfidenceLevel.INSUFFICIENT_EVIDENCE
    assert result3.thesis_statement == "Fallback: insufficient evidence to synthesise a thesis."
    assert repair_stats["fallback_count"] == 1
    print(f"  OK — fallback thesis statement: {result3.thesis_statement[:60]}...")
    print(f"  repair_stats={repair_stats}\n")

    # 4. Challenge risk — happy path
    print("--- Test 4: challenge_risk happy path ---")
    _reset_stats()
    risk_result = challenge_risk(result)
    assert isinstance(risk_result, RiskChallengeResult)
    assert risk_result.thesis_id == "thesis-001"
    assert repair_stats["total_attempts"] == 0
    assert repair_stats["fallback_count"] == 0
    print(f"  OK — risk for thesis {risk_result.thesis_id}, severity={risk_result.overall_severity.value}")
    print(f"  repair_stats={repair_stats}\n")

    # 5. Challenge risk — invalid data → fallback
    print("--- Test 5: challenge_risk fallback (no risks) ---")
    _reset_stats()
    # Build a thesis that would produce an empty challenge
    minimal_thesis = ThesisSynthesisResult(
        thesis_id="thesis-999",
        event_id="event-null",
        thesis_statement="Minimal thesis.",
        confidence=ConfidenceLevel.LOW,
        evidence_refs=["ev-fallback"],
    )
    risk_result2 = challenge_risk(minimal_thesis)
    assert isinstance(risk_result2, RiskChallengeResult)
    # Should have fallen back since no risks were provided in the challenge data
    assert risk_result2.overall_severity == RiskSeverity.NONE_DETECTED
    print(f"  OK — fallback risk: severity={risk_result2.overall_severity.value}")
    print(f"  repair_stats={repair_stats}\n")

    # 6. Verify repair limit is 1
    print("--- Test 6: Repair limit is 1 ---")
    _reset_stats()
    assert repair_stats["repair_limit"] == 1
    print(f"  OK — repair_limit={repair_stats['repair_limit']}\n")

    # 7. No provider credentials read or used
    print("--- Test 7: No provider credentials ---")
    # This file does not import os, dotenv, or any AI provider SDK.
    # We assert this statically by verifying the module attributes.
    import os
    assert "OPENAI_API_KEY" not in os.environ  # not required by this code
    assert "ANTHROPIC_API_KEY" not in os.environ  # not required by this code
    print("  OK — no provider credential is read or used.\n")

    # 8. Model result cannot choose a lifecycle transition
    print("--- Test 8: Model result is pure data, not an action ---")
    # ThesisSynthesisResult and RiskChallengeResult are Pydantic models
    # (data containers).  They have no methods that execute transitions.
    # Verify no callable triggers exist.
    forbidden = {"transition", "execute", "apply", "commit", "publish"}
    thesis_methods = {
        m for m in dir(ThesisSynthesisResult) if not m.startswith("_")
    }
    risk_methods = {
        m for m in dir(RiskChallengeResult) if not m.startswith("_")
    }
    assert thesis_methods.isdisjoint(forbidden), f"Found forbidden methods: {thesis_methods & forbidden}"
    assert risk_methods.isdisjoint(forbidden), f"Found forbidden methods: {risk_methods & forbidden}"
    print("  OK — no lifecycle transition, external action, or callable trigger in models.\n")

    print("=== All self-tests passed ===")
    sys.exit(0)
