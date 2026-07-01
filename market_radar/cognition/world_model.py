"""P07-P08: Market World Model V1 and regime/priced-in classifiers.

Point-in-time domain states for at least 11 market domains.
Aggregate MarketWorldState never hides unavailable domains.
Regime and priced-in classifiers are deterministic, versioned hypotheses.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "world-model-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RegimeLabel(str, Enum):
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    MIXED = "mixed"
    UNCLEAR = "unclear"


class LiquidityLabel(str, Enum):
    EXPANDING = "expanding"
    CONTRACTING = "contracting"
    UNCLEAR = "unclear"


class TrendLabel(str, Enum):
    TREND = "trend"
    RANGE = "range"
    DISLOCATION = "dislocation"
    UNCLEAR = "unclear"


class LeverageLabel(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    CROWDED = "crowded"
    STRESSED = "stressed"


class NarrativeLabel(str, Enum):
    EMERGING = "emerging"
    BROADENING = "broadening"
    CROWDED = "crowded"
    DECAYING = "decaying"
    ABSENT = "absent"


class PricedInLabel(str, Enum):
    UNPRICED = "unpriced"
    PARTIALLY_PRICED = "partially_priced"
    MOSTLY_PRICED = "mostly_priced"
    INDETERMINATE = "indeterminate"



@dataclass
class DomainState:
    """Base fields for every market domain state."""
    domain: str = ""
    as_of: str = ""
    observed_variables: List[str] = field(default_factory=list)
    unavailable_variables: List[str] = field(default_factory=list)
    state_classification: str = "unknown"
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    confidence_components: Dict[str, float] = field(default_factory=dict)
    overall_confidence: float = 0.0
    freshness_hours: Optional[float] = None
    stale: bool = False
    regime_implications: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DomainState:
        return cls(**data)



@dataclass
class MacroLiquidityState(DomainState):
    """Macroeconomic and liquidity conditions."""
    domain: str = "macro_and_liquidity"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class RegulatoryGeoState(DomainState):
    """Regulatory and geopolitical risk."""
    domain: str = "regulatory_and_geopolitical"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class SpotCrossAssetState(DomainState):
    """Spot price and cross-asset behavior."""
    domain: str = "spot_and_cross_asset"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class DerivativesPositioningState(DomainState):
    """Derivatives and positioning."""
    domain: str = "derivatives_and_positioning"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class StablecoinLiquidityState(DomainState):
    """Stablecoin liquidity flows."""
    domain: str = "stablecoin_liquidity"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class OnChainWhaleState(DomainState):
    """On-chain and whale activity."""
    domain: str = "onchain_and_whales"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class DefiProtocolState(DomainState):
    """DeFi and protocol health."""
    domain: str = "defi_and_protocol"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class TokenSupplyState(DomainState):
    """Token supply and unlock pressure."""
    domain: str = "token_supply_and_unlocks"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class SecurityOperationalState(DomainState):
    """Security and operational risk."""
    domain: str = "security_and_operational"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class AttentionNarrativeState(DomainState):
    """Attention and narrative dynamics."""
    domain: str = "attention_and_narrative"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class DataQualityState(DomainState):
    """Data quality and source health."""
    domain: str = "data_quality_and_health"

    # Domain-specific observed variables
    rate_decisions: List[Dict[str, Any]] = field(default_factory=list)
    key_metrics: Dict[str, Optional[float]] = field(default_factory=dict)
    signal_flags: List[str] = field(default_factory=list)
    anomaly_detected: bool = False



@dataclass
class MarketWorldState:
    """Aggregate point-in-time state across all domains.

    Never hides unavailable domains -- each domain is either populated
    or has unavailable_variables explaining why.
    """
    schema_version: str = SCHEMA_VERSION
    as_of: str = ""
    domains: Dict[str, DomainState] = field(default_factory=dict)
    unavailable_domains: List[str] = field(default_factory=list)

    macro_and_liquidity: Optional[MacroLiquidityState] = None
    regulatory_and_geopolitical: Optional[RegulatoryGeoState] = None
    spot_and_cross_asset: Optional[SpotCrossAssetState] = None
    derivatives_and_positioning: Optional[DerivativesPositioningState] = None
    stablecoin_liquidity: Optional[StablecoinLiquidityState] = None
    onchain_and_whales: Optional[OnChainWhaleState] = None
    defi_and_protocol: Optional[DefiProtocolState] = None
    token_supply_and_unlocks: Optional[TokenSupplyState] = None
    security_and_operational: Optional[SecurityOperationalState] = None
    attention_and_narrative: Optional[AttentionNarrativeState] = None
    data_quality_and_health: Optional[DataQualityState] = None

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MarketWorldState:
        return cls(**data)

    def available_domains(self) -> List[str]:
        return [k for k, v in self.domains.items() if v is not None]



@dataclass
class RegimeClassification:
    """Deterministic V1 regime classification result."""
    schema_version: str = SCHEMA_VERSION
    as_of: str = ""
    risk_label: str = RegimeLabel.UNCLEAR.value
    liquidity_label: str = LiquidityLabel.UNCLEAR.value
    trend_label: str = TrendLabel.UNCLEAR.value
    leverage_label: str = LeverageLabel.NORMAL.value
    narrative_label: str = NarrativeLabel.ABSENT.value

    # Reasoning
    inputs: Dict[str, Any] = field(default_factory=dict)
    thresholds: Dict[str, float] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    uncertainty: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RegimeClassification:
        return cls(**data)


@dataclass
class PricedInAssessment:
    """Event-specific priced-in assessment."""
    schema_version: str = SCHEMA_VERSION
    event_id: str = ""
    priced_in_label: str = PricedInLabel.INDETERMINATE.value
    pre_event_price_movement: Optional[float] = None
    surprise_gap: Optional[float] = None
    volume_anomaly: bool = False
    option_skew_change: Optional[float] = None
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PricedInAssessment:
        return cls(**data)