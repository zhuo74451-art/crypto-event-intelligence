"""Market hypothesis contracts — the system's smallest judgment unit."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .common import ContractBase
from .calibration import ConfidenceStatement


class HypothesisStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class MarketHypothesis(ContractBase):
    """The system's smallest judgment unit.

    Each hypothesis links an event, a strategy instance, and affected assets
    with supporting/contradicting evidence and a confidence statement.
    Multiple hypotheses may exist for the same event (different assets,
    directions, time scales, or strategies).
    """
    contract_name: str = "MarketHypothesis"
    schema_version: str = "1.0.0"

    hypothesis_id: str = ""
    event_id: str = ""
    strategy_instance_id: str = ""

    affected_assets: list[str] = field(default_factory=list)
    affected_sectors: list[str] = field(default_factory=list)
    time_horizon: str = ""

    regime_context: str = ""
    causal_thesis: str = ""
    transmission_graph_ref: str = ""

    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)

    expected_effect: str = ""
    alternative_explanations: list[str] = field(default_factory=list)
    invalidation_conditions: list[str] = field(default_factory=list)

    status: HypothesisStatus = HypothesisStatus.CANDIDATE
    confidence_statement: Optional[ConfidenceStatement] = None
    expires_at: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.status, str):
            self.status = HypothesisStatus(self.status)
        if isinstance(self.confidence_statement, dict):
            self.confidence_statement = ConfidenceStatement(**self.confidence_statement)
