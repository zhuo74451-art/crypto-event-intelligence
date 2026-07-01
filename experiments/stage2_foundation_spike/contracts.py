"""Canonical contracts for Stage 2 foundation spike.

Evidence status bands from RISK_ABSTENTION_CONSTITUTION.md:
BLOCKED, INSUFFICIENT, TENTATIVE, SUPPORTED, STRONG
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class EvidenceStatus(str, Enum):
    BLOCKED = "blocked"
    INSUFFICIENT = "insufficient"
    TENTATIVE = "tentative"
    SUPPORTED = "supported"
    STRONG = "strong"


class EvidenceBand(str, Enum):
    PRE_TRADE = "pre_trade"
    DURING_TRADE = "during_trade"
    POST_TRADE = "post_trade"
    LONG_TERM = "long_term"


class Horizon(str, Enum):
    IMMEDIATE = "immediate"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class ActionType(str, Enum):
    """Safe audit actions only — no transition, notification, publication, wallet, or trade."""
    LOG = "log"
    FLAG = "flag"
    REVIEW = "review"
    ESCALATE = "escalate"
    SILENCE = "silence"


class ClaimClass(str, Enum):
    """Canonical claim classes from RISK_ABSTENTION_CONSTITUTION.md"""
    FACT = "fact"
    EVENT_STATE = "event_state"
    MECHANISM = "mechanism"
    EXPOSURE = "exposure"
    DIRECTION = "direction"
    PRICED_IN = "priced_in"
    ATTENTION_ACTION = "attention_action"


class EvidenceRef(BaseModel):
    source: str = Field(..., min_length=1)
    content_hash: str = Field(..., min_length=1)
    retrieved_at: datetime


class ThesisSynthesisResult(BaseModel):
    """Result of semantic pass A: thesis synthesis.

    Uses evidence-status bands (not numeric confidence).
    Cannot contain or choose lifecycle state, notification, or trade action.
    evidence_refs may be empty when evidence_status is BLOCKED or INSUFFICIENT.
    """
    claim_class: ClaimClass
    summary: str = Field(..., min_length=1)
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    horizon: Horizon
    evidence_status: EvidenceStatus  # not numeric confidence
    action_type: ActionType  # only safe audit actions
    repair_attempts: int = 0

    @model_validator(mode="after")
    def evidence_required_when_supported(self) -> "ThesisSynthesisResult":
        """evidence_refs may be empty when status is BLOCKED or INSUFFICIENT."""
        if self.evidence_status in (EvidenceStatus.SUPPORTED, EvidenceStatus.STRONG) and not self.evidence_refs:
            raise ValueError("Supported/STRONG results require at least one evidence reference")
        return self

    @field_validator("action_type")
    @classmethod
    def no_dangerous_action(cls, v: ActionType) -> ActionType:
        dangerous = {"transition", "notify", "publish", "trade", "wallet", "execute", "send"}
        if v.value in dangerous:
            raise ValueError(f"ActionType {v.value} is not allowed — may only contain safe audit actions")
        return v

    @field_validator("claim_class")
    @classmethod
    def synthesis_claim_classes(cls, v: ClaimClass) -> ClaimClass:
        allowed = {"fact", "event_state", "mechanism", "exposure", "direction", "priced_in"}
        if v.value not in allowed:
            raise ValueError(f"ClaimClass {v.value} not allowed in synthesis")
        return v


class RiskChallengeResult(BaseModel):
    """Result of semantic pass B: risk challenge.

    Failed risk analysis must return an explicit unavailable/insufficient result,
    not NONE_DETECTED.
    """
    claim_class: ClaimClass
    challenge: str = Field(..., min_length=1)
    severity: str = Field(default="unknown")  # low, medium, high, unknown
    evidence_refs: List[EvidenceRef] = Field(default_factory=list)
    risk_available: bool = True  # False if risk analysis did not complete
    evidence_status: EvidenceStatus
    repair_attempts: int = 0

    @field_validator("claim_class")
    @classmethod
    def risk_claim_classes(cls, v: ClaimClass) -> ClaimClass:
        allowed = {"mechanism", "exposure", "direction", "priced_in", "attention_action"}
        if v.value not in allowed:
            raise ValueError(f"ClaimClass {v.value} not allowed in risk challenge")
        return v

    @field_validator("risk_available", mode="before")
    @classmethod
    def no_false_none_detected(cls, v: bool, info) -> bool:
        """Risk unavailability must not fall back to NONE_DETECTED."""
        return v
