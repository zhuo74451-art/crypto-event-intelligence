"""
Intelligence Kernel Stub — Adapter-level proposals for the macro strategy.

These dataclasses define the contract between the macro-scheduled strategy
and the intelligence kernel system.  Each is marked with traits that
indicate it is a temporary integration stub awaiting production wiring.

Contracts:
    - temporary_integration_stub = True  (will be replaced by real kernel client)
    - production_contract_owner = "intelligence_kernel"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Metadata markers (applied to every class in this module)
# ---------------------------------------------------------------------------
_TEMPORARY_STUB: bool = True
_PRODUCTION_OWNER: str = "intelligence_kernel"


@dataclass
class MacroStrategyHypothesisProposal:
    """A hypothesis formed by the macro strategy for kernel consumption.

    Attributes:
        hypothesis_id:       Unique identifier for this hypothesis.
        release_event_id:    The macro release event that triggered it.
        direction:           "bullish" | "bearish" | "neutral".
        confidence:          Decimal between 0 and 1.
        triggered_at:        Time the hypothesis was formed.
        supporting_facts:    Structured data that backs the hypothesis.
        temporary_integration_stub: Always True for this adapter stub.
        production_contract_owner:  Always "intelligence_kernel".
    """

    hypothesis_id: str
    release_event_id: str
    direction: str  # "bullish" | "bearish" | "neutral"
    confidence: Decimal
    triggered_at: datetime
    supporting_facts: dict[str, Any] = field(default_factory=dict)

    # --- stub / contract markers ---
    temporary_integration_stub: bool = _TEMPORARY_STUB
    production_contract_owner: str = _PRODUCTION_OWNER


@dataclass
class MacroAssessmentProposal:
    """An assessment (adapter version) produced by the macro strategy.

    This is the adapter-level analogue of a kernel Assessment; it carries
    the same semantic fields but is *not* yet a first-class kernel object.
    Once the kernel client is wired, instances will be converted to true
    kernel Assessment records.

    Attributes:
        assessment_id:      Unique identifier.
        hypothesis_id:      Link to the parent hypothesis.
        assessed_at:        When the assessment was performed.
        score:              Numeric score (e.g. 0-100).
        rationale:          Free-text justification.
        temporary_integration_stub: Always True.
        production_contract_owner:  Always "intelligence_kernel".
    """

    assessment_id: str
    hypothesis_id: str
    assessed_at: datetime
    score: float
    rationale: str = ""

    # --- stub / contract markers ---
    temporary_integration_stub: bool = _TEMPORARY_STUB
    production_contract_owner: str = _PRODUCTION_OWNER


@dataclass
class MacroTransmissionProposal:
    """A transmission proposal ready to be sent to the intelligence kernel.

    After assessment, a TransmissionProposal wraps the hypothesis +
    assessment + any trade signal into a single payload that the kernel
    can ingest.

    Attributes:
        transmission_id:    Unique identifier.
        hypothesis:         The originating hypothesis.
        assessment:         The corresponding assessment.
        signal:             Optional trade-side signal.
        transmitted_at:     Timestamp of transmission.
        temporary_integration_stub: Always True.
        production_contract_owner:  Always "intelligence_kernel".
    """

    transmission_id: str
    hypothesis: MacroStrategyHypothesisProposal
    assessment: MacroAssessmentProposal
    signal: Optional[str] = None  # "long" | "short" | "flat" | None
    transmitted_at: Optional[datetime] = None

    # --- stub / contract markers ---
    temporary_integration_stub: bool = _TEMPORARY_STUB
    production_contract_owner: str = _PRODUCTION_OWNER
