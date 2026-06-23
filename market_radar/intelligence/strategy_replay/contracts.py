"""Typed contracts for the strategy replay system — Lane C canonical types.

These contracts are the local representation of strategy replay data.
They are converted to kernel contracts by the kernel_adapter.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# Enums


class StrategyState(str, Enum):
    CANDIDATE = "candidate"
    TRIGGERED = "triggered"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    SUPPORTED = "supported"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ReplayStatus(str, Enum):
    COMPLETED = "completed"
    ABSTAINED = "abstained"
    SKIPPED = "skipped"
    ERROR = "error"


class MarketConfirmation(str, Enum):
    SPOT_CROSS_ASSET_CONFIRMED = "spot_cross_asset_confirmed"
    SPOT_CONFIRMED = "spot_confirmed"
    CROSS_ASSET_CONFIRMED = "cross_asset_confirmed"
    PARTIAL = "partial"
    DERIVATIVES_ONLY = "derivatives_only"
    CONTRADICTING = "contradicting"
    AWAITING = "awaiting"
    MISSING = "missing"


class TransmissionCoherence(str, Enum):
    COHERENT = "coherent"
    CONFLICTING = "conflicting"
    MISSING = "missing"
    INVALID = "invalid"


class ConfidenceType(str, Enum):
    DIRECTIONAL = "directional"
    CONDITIONAL = "conditional"
    EXPLORATORY = "exploratory"
    INSUFFICIENT = "insufficient"


class RegimeLabel(str, Enum):
    INFLATION_DOMINANT = "inflation_dominant"
    GROWTH_DOMINANT = "growth_dominant"
    LIQUIDITY_DOMINANT = "liquidity_dominant"
    RISK_OFF_STRESS = "risk_off_stress"
    RISK_ON_EXPANSION = "risk_on_expansion"
    MIXED_UNCERTAIN = "mixed_uncertain"


class DataQualityGrade(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNUSABLE = "unusable"


def deterministic_id(prefix: str, components: list[str]) -> str:
    """Generate a deterministic ID from sorted components."""
    raw = "|".join(sorted(components))
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{h}"


@dataclass
class StrategyDefinitionV1:
    strategy_id: str = ""
    strategy_version: str = "1.0.0"
    strategy_family: str = ""
    strategy_name: str = ""
    supported_event_families: list[str] = field(default_factory=list)
    supported_assets: list[str] = field(default_factory=list)
    supported_horizons: list[str] = field(default_factory=list)
    required_macro_fields: list[str] = field(default_factory=list)
    required_market_fields: list[str] = field(default_factory=list)
    required_regime_fields: list[str] = field(default_factory=list)
    required_confirmation_fields: list[str] = field(default_factory=list)
    valid_regimes: list[str] = field(default_factory=list)
    invalid_regimes: list[str] = field(default_factory=list)
    trigger_rules: dict[str, str] = field(default_factory=dict)
    confirmation_rules: dict[str, str] = field(default_factory=dict)
    invalidation_rules: dict[str, str] = field(default_factory=dict)
    expiration_rules: dict[str, str] = field(default_factory=dict)
    abstention_rules: list[str] = field(default_factory=list)
    transmission_paths: list[str] = field(default_factory=list)
    alternative_explanations: list[str] = field(default_factory=list)
    known_failure_modes: list[str] = field(default_factory=list)
    confidence_representation: str = "directional"
    calibration_required_for_probability: bool = True

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "strategy_family": self.strategy_family,
            "strategy_name": self.strategy_name,
            "supported_event_families": list(self.supported_event_families),
            "supported_assets": list(self.supported_assets),
            "supported_horizons": list(self.supported_horizons),
            "required_macro_fields": list(self.required_macro_fields),
            "required_market_fields": list(self.required_market_fields),
            "required_regime_fields": list(self.required_regime_fields),
            "required_confirmation_fields": list(self.required_confirmation_fields),
            "valid_regimes": list(self.valid_regimes),
            "invalid_regimes": list(self.invalid_regimes),
            "trigger_rules": dict(self.trigger_rules),
            "confirmation_rules": dict(self.confirmation_rules),
            "invalidation_rules": dict(self.invalidation_rules),
            "expiration_rules": dict(self.expiration_rules),
            "abstention_rules": list(self.abstention_rules),
            "transmission_paths": list(self.transmission_paths),
            "alternative_explanations": list(self.alternative_explanations),
            "known_failure_modes": list(self.known_failure_modes),
            "confidence_representation": self.confidence_representation,
            "calibration_required_for_probability": self.calibration_required_for_probability,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StrategyDefinitionV1":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class StrategyReplayInputV1:
    replay_input_id: str = ""
    event_id: str = ""
    event_family: str = ""
    event_time_utc: str = ""
    available_information_cutoff_utc: str = ""
    macro_release_record: Optional[dict] = None
    macro_consensus_record: Optional[dict] = None
    macro_revision_state_as_of_cutoff: Optional[dict] = None
    market_window_as_of_cutoff: Optional[dict] = None
    cross_asset_state_as_of_cutoff: Optional[dict] = None
    derivatives_state_as_of_cutoff: Optional[dict] = None
    regime_state_as_of_cutoff: Optional[dict] = None
    data_quality: str = "medium"
    point_in_time_quality: str = "medium"
    missing_fields: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass
class StrategyObservationV1:
    observation_id: str = ""
    strategy_id: str = ""
    event_id: str = ""
    observed_at_utc: str = ""
    information_cutoff_utc: str = ""
    macro_surprise: str = ""
    macro_surprise_quality: str = ""
    prior_revision_context: Optional[dict] = None
    pre_event_market_state: Optional[dict] = None
    first_reaction_state: Optional[dict] = None
    cross_asset_confirmation: Optional[dict] = None
    derivatives_confirmation: Optional[dict] = None
    regime_state: Optional[dict] = None
    available_inputs: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)


@dataclass
class StrategyHypothesisV1:
    hypothesis_id: str = ""
    strategy_id: str = ""
    strategy_instance_id: str = ""
    event_id: str = ""
    asset: str = ""
    sector: str = ""
    time_horizon: str = ""
    expected_effect: str = ""
    supporting_evidence_refs: list[str] = field(default_factory=list)
    opposing_evidence_refs: list[str] = field(default_factory=list)
    alternative_explanations: list[str] = field(default_factory=list)
    invalidation_conditions: list[str] = field(default_factory=list)
    expiration_at_utc: Optional[str] = None
    strategy_state: str = "candidate"
    market_confirmation: str = "missing"
    transmission_signature: str = ""
    transmission_coherence: str = "missing"
    transmission_conflicts: list[str] = field(default_factory=list)
    confidence_type: str = "directional"
    calibration_artifact_ref: str = ""
    limitations: list[str] = field(default_factory=list)
    release_unit_id: str = ""
    constituent_event_ids: list[str] = field(default_factory=list)
    event_families: list[str] = field(default_factory=list)
    decision_unit_id: str = ""
    decision_cutoff_utc: str = ""
    signal_window_id: str = ""
    signal_direction: str = ""
    signal_return_pct: Optional[float] = None
    signal_endpoint_time_utc: str = ""
    signal_endpoint_price: Optional[float] = None
    precision_class: str = ""


@dataclass
class StrategyReplayResultV1:
    replay_result_id: str = ""
    event_id: str = ""
    strategy_id: str = ""
    strategy_instance_id: str = ""
    replay_status: str = "completed"
    strategy_state: str = "candidate"
    hypotheses: list[str] = field(default_factory=list)
    abstention_record_id: str = ""
    kernel_package_id: str = ""
    available_information_cutoff_utc: str = ""
    generated_at_utc: str = ""
    warnings: list[str] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)
    provenance_refs: list[str] = field(default_factory=list)
    decision_unit_id: str = ""
    release_unit_id: str = ""
    constituent_event_ids: list[str] = field(default_factory=list)
    asset: str = ""
    hypothesis_ids: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass
class AbstentionRecordV1:
    abstention_id: str = ""
    event_id: str = ""
    strategy_id: str = ""
    strategy_instance_id: str = ""
    reason_codes: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    conflicting_inputs: list[str] = field(default_factory=list)
    point_in_time_quality: str = ""
    market_data_quality: str = ""
    consensus_quality: str = ""
    regime_quality: str = ""
    transmission_quality: str = ""
    information_cutoff_utc: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    resume_conditions: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)


@dataclass
class KernelInputPackageV1:
    kernel_package_id: str = ""
    event_id: str = ""
    asset: str = ""
    sector: str = ""
    hypotheses: list[dict] = field(default_factory=list)
    hypothesis_contexts: dict[str, Any] = field(default_factory=dict)
    evidence_state: dict[str, Any] = field(default_factory=dict)
    regime_state: dict[str, Any] = field(default_factory=dict)
    source_strategy_ids: list[str] = field(default_factory=list)
    source_replay_result_ids: list[str] = field(default_factory=list)
    information_cutoff_utc: str = ""
    contract_versions: dict[str, str] = field(default_factory=dict)
    quality_flags: list[str] = field(default_factory=list)


@dataclass
class RegimeClassificationResult:
    regime: str = ""
    rule_id: str = ""
    inputs_used: list[str] = field(default_factory=list)
    inputs_missing: list[str] = field(default_factory=list)
    information_cutoff_utc: str = ""
    quality: str = "medium"
    alternative_regimes: list[dict] = field(default_factory=list)


@dataclass
class BaselineDefinition:
    baseline_id: str = ""
    baseline_name: str = ""
    baseline_family: str = ""
    description: str = ""
    allowed_inputs: list[str] = field(default_factory=list)
    prohibited_inputs: list[str] = field(default_factory=list)
    maturity: str = "baseline"
