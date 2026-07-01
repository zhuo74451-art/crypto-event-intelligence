"""P10-P13: StrategySpec, Registry, Arbitration, MarketDecisionPacket."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "strategy-v1"

class StrategyStatus(str, Enum):
    EXPERIMENTAL = "experimental"
    HISTORICAL_SUPPORTED = "historical_supported"
    SHADOW_SUPPORTED = "shadow_supported"
    REJECTED = "rejected"
    STALE = "stale"

class ArbitrationOutcome(str, Enum):
    ACTIONABLE_WATCH = "actionable_watch"
    MONITOR = "monitor"
    ABSTAIN = "abstain"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class StrategySpec:
    """Structured strategy component."""
    schema_version: str = SCHEMA_VERSION
    strategy_id: str = ""
    version: str = "1.0"
    name: str = ""
    thesis: str = ""
    applicable_domains: List[str] = field(default_factory=list)
    applicable_regimes: List[str] = field(default_factory=list)
    required_variables: List[str] = field(default_factory=list)
    trigger: str = ""
    confirmation: str = ""
    disqualifiers: List[str] = field(default_factory=list)
    time_horizon: str = "medium"
    expiry_condition: str = ""
    invalidation_condition: str = ""
    supporting_research_claims: List[str] = field(default_factory=list)
    historical_evidence_status: str = ""
    shadow_evidence_status: str = ""
    abstention_conditions: List[str] = field(default_factory=list)
    max_confidence: float = 1.0
    not_trading_instruction: bool = True

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)


@dataclass
class RegisteredComponent:
    schema_version: str = SCHEMA_VERSION
    spec: Optional[StrategySpec] = None
    status: str = StrategyStatus.EXPERIMENTAL.value
    registered_at: str = ""
    updated_at: str = ""
    conflict_ids: List[str] = field(default_factory=list)
    notes: str = ""
    def to_dict(self): from dataclasses import asdict; return asdict(self)


@dataclass
class StrategyRegistry:
    """Versioned registry of strategy components."""
    schema_version: str = SCHEMA_VERSION
    components: Dict[str, RegisteredComponent] = field(default_factory=dict)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    registry_version: str = "1.0"

    def register(self, spec: StrategySpec) -> Optional[str]:
        required = ["strategy_id", "thesis", "trigger"]
        for f in required:
            if not getattr(spec, f, ""): return f"missing: {f}"
        if spec.strategy_id in self.components:
            return f"duplicate: {spec.strategy_id}"
        import datetime
        self.components[spec.strategy_id] = RegisteredComponent(
            spec=spec, status=StrategyStatus.EXPERIMENTAL.value,
            registered_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        return None

    def get_by_domain(self, domain: str) -> List[StrategySpec]:
        return [c.spec for c in self.components.values() if c.spec and domain in c.spec.applicable_domains]

    def get_by_regime(self, regime: str) -> List[StrategySpec]:
        return [c.spec for c in self.components.values() if c.spec and regime in c.spec.applicable_regimes]

    def to_dict(self): from dataclasses import asdict; return asdict(self)


@dataclass
class ArbitrationResult:
    """Output of strategy arbitration."""
    schema_version: str = SCHEMA_VERSION
    event_id: str = ""
    arbitration_id: str = ""
    as_of: str = ""
    eligible_strategies: List[str] = field(default_factory=list)
    rejected_strategies: Dict[str, str] = field(default_factory=dict)
    support_reasons: Dict[str, List[str]] = field(default_factory=dict)
    contradiction_reasons: Dict[str, List[str]] = field(default_factory=dict)
    missing_inputs: Dict[str, List[str]] = field(default_factory=dict)
    outcome: str = ArbitrationOutcome.INSUFFICIENT_EVIDENCE.value
    selected_observation_stance: str = ""
    confidence_decomposition: Dict[str, float] = field(default_factory=dict)
    overall_confidence: float = 0.0
    expiry: str = ""
    invalidation_conditions: List[str] = field(default_factory=list)
    follow_up_requests: List[str] = field(default_factory=list)
    not_trading_instruction: bool = True
    def to_dict(self): from dataclasses import asdict; return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)


@dataclass
class MarketDecisionPacket:
    """Canonical final output."""
    schema_version: str = SCHEMA_VERSION
    packet_id: str = ""
    event_id: str = ""
    as_of: str = ""
    event_title: str = ""
    event_status: str = ""
    evidence_status: str = ""
    world_model_summary: str = ""
    available_domains: List[str] = field(default_factory=list)
    unavailable_domains: List[str] = field(default_factory=list)
    expectation_baseline: str = ""
    expectation_gap: Optional[float] = None
    affected_assets: List[str] = field(default_factory=list)
    time_horizons: List[str] = field(default_factory=list)
    transmission_paths: List[str] = field(default_factory=list)
    confirmation_verdict: str = ""
    priced_in_state: str = ""
    crowding_state: str = ""
    eligible_strategies: List[str] = field(default_factory=list)
    arbitration_outcome: str = ArbitrationOutcome.INSUFFICIENT_EVIDENCE.value
    observation_stance: str = ArbitrationOutcome.ABSTAIN.value
    trigger_conditions: List[str] = field(default_factory=list)
    confirmation_conditions: List[str] = field(default_factory=list)
    expiry: str = ""
    invalidation: List[str] = field(default_factory=list)
    supporting_evidence: List[str] = field(default_factory=list)
    opposing_evidence: List[str] = field(default_factory=list)
    known_unknowns: List[str] = field(default_factory=list)
    confidence_components: Dict[str, float] = field(default_factory=dict)
    overall_confidence: float = 0.0
    follow_up_checks: List[str] = field(default_factory=list)
    not_trading_instruction: bool = True

    def to_dict(self): from dataclasses import asdict; return asdict(self)
    @classmethod
    def from_dict(cls, data): return cls(**data)

    def to_markdown(self) -> str:
        lines = ["# Market Decision Packet: " + self.packet_id, ""]
        lines.append("**Event:** " + self.event_title + " (" + self.event_id + ")")
        lines.append("**As of:** " + self.as_of)
        lines.append("**Status:** " + self.event_status)
        lines.append("")
        lines.append("## Arbitration")
        lines.append("**Stance:** " + self.observation_stance)
        lines.append("**Outcome:** " + self.arbitration_outcome)
        lines.append("**Confidence:** " + str(self.overall_confidence))
        lines.append("")
        lines.append("## Expectation")
        lines.append("**Baseline:** " + self.expectation_baseline)
        lines.append("**Gap:** " + str(self.expectation_gap))
        lines.append("")
        lines.append("## Strategies")
        lines.append("**Eligible:** " + str(len(self.eligible_strategies)))
        lines.append("**Confirmation:** " + self.confirmation_verdict)
        lines.append("")
        lines.append("## Evidence")
        lines.append("**Supporting:** " + str(len(self.supporting_evidence)) + " items")
        lines.append("**Opposing:** " + str(len(self.opposing_evidence)) + " items")
        lines.append("")
        lines.append("---")
        if self.not_trading_instruction:
            lines.append("*Not a trading instruction.*")
        return chr(10).join(lines)