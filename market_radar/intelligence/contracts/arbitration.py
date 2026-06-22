"""Arbitration contracts — structured conflict resolution between strategies.

Fixes over original:
- EligibilityDecision replaces mixed list[str|object] ineligible_reasons
- HypothesisArbitrationContext for full evidence/regime state
- SupportCluster for origin folding
- Quality dimensions with explicit levels
- Rule IDs for all verdict decisions
"""
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


class QualityLevel(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


class ArbitrationStatus(str, Enum):
    """Global arbitration status across all horizons.
    Not a single direction — expresses system-level state.
    """
    ALL_HORIZONS_INSUFFICIENT = "all_horizons_insufficient"
    SOME_HORIZONS_DIRECTIONAL = "some_horizons_directional"
    MULTI_HORIZON_MIXED = "multi_horizon_mixed"
    CONFLICT_PRESENT = "conflict_present"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"


# ── Eligibility ────────────────────────────────────────────────────────────

class EligibilityReasonCode(str, Enum):
    CONTRACT_VALID = "E01_contract_valid"
    ASSET_SCOPE_MISMATCH = "E02_asset_scope_mismatch"
    HORIZON_UNRECOGNIZED = "E03_horizon_unrecognized"
    STRATEGY_STATE_INELIGIBLE = "E04_strategy_state_ineligible"
    REQUIRED_INPUTS_MISSING = "E05_required_inputs_missing"
    EVIDENCE_MINIMUM_NOT_MET = "E06_evidence_minimum_not_met"
    EVIDENCE_CONFLICTING = "E07_evidence_conflicting"
    REGIME_INVALID = "E08_regime_invalid"
    HYPOTHESIS_EXPIRED = "E09_hypothesis_expired"
    INVALIDATION_TRIGGERED = "E10_invalidation_triggered"
    CONFIDENCE_INVALID = "E11_confidence_invalid"
    TRANSMISSION_INVALID = "E12_transmission_invalid"


@dataclass
class EligibilityDecision:
    """Structured eligibility decision for a single hypothesis."""
    hypothesis_id: str = ""
    eligible: bool = False
    reason_codes: list[EligibilityReasonCode] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    evidence_status: str = ""
    regime_status: str = ""
    strategy_status: str = ""
    trace: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.reason_codes:
            self.reason_codes = [
                EligibilityReasonCode(r) if isinstance(r, str) else r
                for r in self.reason_codes
            ]


@dataclass
class EligibleHypothesis:
    """An eligible hypothesis with full context for arbitration."""
    hypothesis_id: str = ""
    strategy_instance_id: str = ""
    strategy_id: str = ""
    strategy_origin_group: str = ""
    asset: str = ""
    sector: str = ""
    time_horizon: str = ""
    strategy_state: str = ""
    required_inputs: list[str] = field(default_factory=list)
    available_inputs: list[str] = field(default_factory=list)
    evidence_bundle_verdict: str = ""
    evidence_independence_count: int = 0
    evidence_independence_groups: list[str] = field(default_factory=list)
    valid_regimes: list[str] = field(default_factory=list)
    invalid_regimes: list[str] = field(default_factory=list)
    current_regime_matches: bool = False
    regime_quality: str = ""
    market_confirmation: str = ""
    transmission_signature: str = ""
    transmission_coherence: str = ""
    expected_effect: str = ""
    alternative_explanations: list[str] = field(default_factory=list)
    invalidation_conditions: list[str] = field(default_factory=list)
    confidence_type: str = ""
    confidence_value: str = ""
    calibration_artifact_ref: str = ""


@dataclass
class IneligibleHypothesis:
    """An ineligible hypothesis with structured reason."""
    hypothesis_id: str = ""
    decisions: list[EligibilityDecision] = field(default_factory=list)

    def all_reason_codes(self) -> list[str]:
        codes = []
        for d in self.decisions:
            codes.extend(d.reason_codes)
        return codes


# ── Support Clustering ────────────────────────────────────────────────────

@dataclass
class HypothesisSupportCluster:
    """A cluster of related hypotheses sharing origin or evidence."""
    hypotheses: list[str] = field(default_factory=list)
    origin_groups: list[str] = field(default_factory=list)
    evidence_independence_groups: list[str] = field(default_factory=list)
    transmission_signatures: set[str] = field(default_factory=set)
    quality: QualityLevel = QualityLevel.INSUFFICIENT
    direction: str = ""


# ── Quality dimensions ────────────────────────────────────────────────────

@dataclass
class QualityDimensions:
    evidence_quality: QualityLevel = QualityLevel.INSUFFICIENT
    strategy_state_quality: QualityLevel = QualityLevel.INSUFFICIENT
    regime_fit: QualityLevel = QualityLevel.INSUFFICIENT
    market_confirmation_quality: QualityLevel = QualityLevel.INSUFFICIENT
    transmission_coherence: QualityLevel = QualityLevel.INSUFFICIENT
    calibration_quality: QualityLevel = QualityLevel.INSUFFICIENT
    input_completeness: QualityLevel = QualityLevel.INSUFFICIENT


# ── Decision Trace ─────────────────────────────────────────────────────────

@dataclass
class HorizonDecisionTrace:
    """Detailed trace for a single horizon's verdict."""
    horizon: str = ""
    eligible_hypotheses: list[str] = field(default_factory=list)
    ineligible_hypotheses: list[IneligibleHypothesis] = field(default_factory=list)
    support_clusters: list[HypothesisSupportCluster] = field(default_factory=list)
    opposing_clusters: list[HypothesisSupportCluster] = field(default_factory=list)
    rule_ids_evaluated: list[str] = field(default_factory=list)
    rule_id_selected: str = ""
    evidence_summary: str = ""
    regime_summary: str = ""
    confirmation_summary: str = ""
    transmission_conflicts: list[str] = field(default_factory=list)
    final_verdict: VerdictState = VerdictState.INSUFFICIENT_EVIDENCE
    direction: str = "neutral"
    limitations: list[str] = field(default_factory=list)


# ── Horizon Assessment ─────────────────────────────────────────────────────

@dataclass
class HorizonAssessment(ContractBase):
    """Assessment for a single time horizon."""
    contract_name: str = "HorizonAssessment"
    schema_version: str = "1.0.0"

    horizon: str = ""
    direction: str = "neutral"
    direction_basis: str = ""  # Which rule produced the direction
    supporting_hypotheses: list[str] = field(default_factory=list)
    opposing_hypotheses: list[str] = field(default_factory=list)
    alternative_hypotheses: list[str] = field(default_factory=list)
    unresolved_conflicts: list[str] = field(default_factory=list)
    missing_confirmations: list[str] = field(default_factory=list)

    verdict: VerdictState = VerdictState.INSUFFICIENT_EVIDENCE
    notes: str = ""
    decision_trace: HorizonDecisionTrace = field(default_factory=HorizonDecisionTrace)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.verdict, str):
            self.verdict = VerdictState(self.verdict)
        if isinstance(self.decision_trace, dict):
            self.decision_trace = HorizonDecisionTrace(**self.decision_trace)


# ── Input / Output ─────────────────────────────────────────────────────────

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
    arbitration_status: ArbitrationStatus = ArbitrationStatus.ALL_HORIZONS_INSUFFICIENT
    eligible_hypotheses: list[EligibleHypothesis] = field(default_factory=list)
    ineligible_hypotheses: list[IneligibleHypothesis] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.global_verdict, str):
            self.global_verdict = VerdictState(self.global_verdict)
        if isinstance(self.arbitration_status, str):
            self.arbitration_status = ArbitrationStatus(self.arbitration_status)
        if self.horizon_assessments:
            converted = []
            for h in self.horizon_assessments:
                if isinstance(h, dict):
                    converted.append(HorizonAssessment(**h))
                else:
                    converted.append(h)
            self.horizon_assessments = converted
        if self.ineligible_hypotheses:
            converted = []
            for h in self.ineligible_hypotheses:
                if isinstance(h, dict):
                    converted.append(IneligibleHypothesis(**h))
                else:
                    converted.append(h)
            self.ineligible_hypotheses = converted
