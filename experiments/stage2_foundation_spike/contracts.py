"""Pydantic v2 models for the stage-2 foundation spike.

Enums, value objects, and aggregate result types that define the
boundary between evidence ingestion and thesis/risk decision-making.
"""

from datetime import datetime
from enum import Enum
from typing import FrozenSet, List

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────
#  Enums
# ──────────────────────────────────────────────


class OriginAuthority(str, Enum):
    """Trustworthiness of the evidence origin."""

    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


class EvidenceBand(str, Enum):
    """Temporal band in which evidence is expected or arrives."""

    PRE_TRADE = "pre_trade"
    DURING_TRADE = "during_trade"
    POST_TRADE = "post_trade"
    LONG_TERM = "long_term"


class ClaimClass(str, Enum):
    """All recognised claim classes that can appear in a thesis or risk."""

    MATERIALITY = "materiality"
    MECHANISM = "mechanism"
    EXPOSURE = "exposure"
    HORIZON = "horizon"
    EXPECTATION = "expectation"
    PRICED_IN = "priced_in"
    NEXT_EVIDENCE = "next_evidence"
    INVALIDATION = "invalidation"
    COUNTER_EVIDENCE = "counter_evidence"
    HIDDEN_ASSUMPTION = "hidden_assumption"
    ALTERNATIVE = "alternative"


class Horizon(str, Enum):
    """Temporal horizon of a thesis or risk."""

    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class ActionType(str, Enum):
    """Analyst-action types that DO NOT directly perform a transition,
    notification, publication, wallet, or trade action — they are pure
    advisory/enum signals for downstream consumers.
    """

    LOG = "log"
    FLAG = "flag"
    REVIEW = "review"
    ESCALATE = "escalate"
    SILENCE = "silence"


# ──────────────────────────────────────────────
#  Value objects
# ──────────────────────────────────────────────


class EvidenceSource(BaseModel):
    """Origin metadata for a piece of evidence."""

    authority: OriginAuthority


class EvidenceRef(BaseModel):
    """A reference to a specific piece of evidence."""

    source: EvidenceSource
    content_hash: str
    retrieved_at: datetime


# ──────────────────────────────────────────────
#  Aggregate results
# ──────────────────────────────────────────────


class ThesisSynthesisResult(BaseModel):
    """Output of a thesis-synthesis step for a single claim class."""

    claim_class: ClaimClass
    summary: str
    evidence_refs: List[EvidenceRef]
    horizon: Horizon
    confidence_band: float = Field(..., ge=0.0, le=1.0)

    @field_validator("evidence_refs")
    @classmethod
    def evidence_refs_must_not_be_empty(
        cls, v: List[EvidenceRef]
    ) -> List[EvidenceRef]:
        if not v:
            raise ValueError("evidence_refs must not be empty")
        return v


# Frozen set of ClaimClass values that are valid for a risk challenge.
# Using a module-level frozenset so the constraint is immutable and
# trivially inspectable.
RISK_CHALLENGE_CLAIM_CLASSES: FrozenSet[ClaimClass] = frozenset(
    {
        ClaimClass.MATERIALITY,
        ClaimClass.MECHANISM,
        ClaimClass.EXPOSURE,
        ClaimClass.INVALIDATION,
        ClaimClass.COUNTER_EVIDENCE,
        ClaimClass.HIDDEN_ASSUMPTION,
        ClaimClass.ALTERNATIVE,
    }
)


class RiskChallengeResult(BaseModel):
    """Output of a risk-challenge step that questions a thesis claim.

    The ``claim_class`` is restricted to the subset of ``ClaimClass``
    values that represent challenges rather than affirmative assertions.
    """

    claim_class: ClaimClass
    challenge: str
    severity: str
    evidence_refs: List[EvidenceRef]

    @field_validator("claim_class")
    @classmethod
    def claim_class_must_be_valid_risk_challenge(
        cls, v: ClaimClass
    ) -> ClaimClass:
        if v not in RISK_CHALLENGE_CLAIM_CLASSES:
            raise ValueError(
                f"claim_class must be one of "
                f"{sorted(c.value for c in RISK_CHALLENGE_CLAIM_CLASSES)}, "
                f"got {v.value!r}"
            )
        return v


class ReviewIntent(BaseModel):
    """A scheduled or requested review for a thesis."""

    review_id: str
    thesis_id: str
    due_at: datetime
    idempotency_key: str
    status: str
