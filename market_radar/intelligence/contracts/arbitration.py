"""Arbitration contracts — structured conflict resolution between strategies."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .common import ContractBase


class VerdictState(str, Enum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    WAIT_FOR_CONFIRMATION = "wait_for_confirmation"
    DIRECTIONAL_AVAILABLE = "directional_available"
    CONFLICT_UNRESOLVED = "conflict_unresolved"
    ABSTAIN = "abstain"


class HorizonBucket(str, Enum):
    INTRADAY = "intraday"
    SHORT_TERM = "short_term"
    SWING = "swing"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


@dataclass
class HorizonAssessment(ContractBase):
    """Assessment for a single time horizon."""
    contract_name: str = "HorizonAssessment"
    schema_version: str = "1.0.0"

    horizon: str = ""
    direction: str = "neutral"
    supporting_hypotheses: list[str] = field(default_factory=list)
    opposing_hypotheses: list[str] = field(default_factory=list)
    alternative_hypotheses: list[str] = field(default_factory=list)
    unresolved_conflicts: list[str] = field(default_factory=list)
    missing_confirmations: list[str] = field(default_factory=list)

    verdict: VerdictState = VerdictState.INSUFFICIENT_EVIDENCE
    notes: str = ""

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.verdict, str):
            self.verdict = VerdictState(self.verdict)


@dataclass
class ArbitrationInput(ContractBase):
    """Input to the arbitration engine."""
    contract_name: str = "ArbitrationInput"
    schema_version: str = "1.0.0"

    asset: str = ""
    sector: str = ""
    hypotheses: list[dict] = field(default_factory=list)
    evidence_state: dict = field(default_factory=dict)
    regime_state: dict = field(default_factory=dict)


@dataclass
class ArbitrationOutput(ContractBase):
    """Output from the arbitration engine."""
    contract_name: str = "ArbitrationOutput"
    schema_version: str = "1.0.0"

    arbitration_id: str = ""
    asset: str = ""
    sector: str = ""
    horizon_assessments: list[HorizonAssessment] = field(default_factory=list)
    global_verdict: VerdictState = VerdictState.INSUFFICIENT_EVIDENCE
    eligible_count: int = 0
    ineligible_count: int = 0
    ineligible_reasons: list[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.global_verdict, str):
            self.global_verdict = VerdictState(self.global_verdict)
        if self.horizon_assessments:
            converted = []
            for h in self.horizon_assessments:
                if isinstance(h, dict):
                    converted.append(HorizonAssessment(**h))
                else:
                    converted.append(h)
            self.horizon_assessments = converted
