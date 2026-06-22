from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from market_radar.domains.macro.contracts.market_context import (
    GrowthInflationRegime, PolicyExpectationRegime,
    LiquidityCondition, RiskAppetite, VolatilityCondition,
)


class RegimeQuality(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class RegimeContext:
    growth_inflation: GrowthInflationRegime = GrowthInflationRegime.UNKNOWN
    policy_expectation: PolicyExpectationRegime = PolicyExpectationRegime.POLICY_UNCERTAIN
    liquidity: LiquidityCondition = LiquidityCondition.UNKNOWN
    risk_appetite: RiskAppetite = RiskAppetite.UNKNOWN
    volatility: VolatilityCondition = VolatilityCondition.UNKNOWN
    quality: RegimeQuality = RegimeQuality.INSUFFICIENT
    limitations: List[str] = field(default_factory=list)
