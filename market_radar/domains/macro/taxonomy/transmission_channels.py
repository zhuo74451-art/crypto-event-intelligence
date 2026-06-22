from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from market_radar.domains.macro.contracts.market_context import GrowthInflationRegime, PolicyExpectationRegime
from market_radar.domains.macro.taxonomy.event_types import EventFamily


class TransmissionChannel(str, Enum):
    RATES_CHANNEL = "rates_channel"
    DOLLAR_CHANNEL = "dollar_channel"
    EQUITY_CHANNEL = "equity_channel"
    RISK_APPETITE_CHANNEL = "risk_appetite_channel"
    CREDIT_CHANNEL = "credit_channel"
    COMMODITY_CHANNEL = "commodity_channel"
    BTC_SPOT = "btc_spot"
    ETH_SPOT = "eth_spot"
    DERIVATIVES = "derivatives"


class TransmissionSign(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class TransmissionEdge:
    source: str
    target: str
    sign: TransmissionSign
    lag: str
    conditions: List[str] = field(default_factory=list)
    regime: Optional[str] = None
    confirmation: Optional[str] = None
    invalidation: Optional[str] = None


# Inflation surprise lower templates
LOWER_INFLATION_PATH = [
    TransmissionEdge("lower_inflation_surprise", "lower_expected_policy_path", TransmissionSign.POSITIVE, "immediate",
                     conditions=["inflation_driven_by_demand"]),
    TransmissionEdge("lower_expected_policy_path", "lower_real_yields", TransmissionSign.POSITIVE, "minutes",
                     confirmation="2Y yield decline"),
    TransmissionEdge("lower_real_yields", "weaker_dollar", TransmissionSign.NEGATIVE, "minutes_to_hours",
                     confirmation="DXY decline"),
    TransmissionEdge("lower_real_yields", "higher_duration_assets", TransmissionSign.POSITIVE, "minutes_to_hours"),
    TransmissionEdge("weaker_dollar", "improved_risk_appetite", TransmissionSign.POSITIVE, "minutes_to_hours"),
    TransmissionEdge("improved_risk_appetite", "btc_eth_support", TransmissionSign.POSITIVE, "minutes_to_hours"),
]

# Inflation surprise higher templates
HIGHER_INFLATION_PATH = [
    TransmissionEdge("higher_inflation_surprise", "higher_expected_policy_path", TransmissionSign.NEGATIVE, "immediate"),
    TransmissionEdge("higher_expected_policy_path", "higher_yields", TransmissionSign.NEGATIVE, "minutes"),
    TransmissionEdge("higher_yields", "stronger_dollar", TransmissionSign.POSITIVE, "minutes_to_hours"),
    TransmissionEdge("higher_yields", "risk_assets_pressure", TransmissionSign.NEGATIVE, "minutes_to_hours"),
    TransmissionEdge("stronger_dollar", "btc_eth_pressure", TransmissionSign.NEGATIVE, "minutes_to_hours"),
]

# NFP strong templates
NFP_STRONG_PATH_GROWTH = [
    TransmissionEdge("strong_growth_surprise", "risk_appetite_up", TransmissionSign.POSITIVE, "immediate"),
    TransmissionEdge("risk_appetite_up", "crypto_support", TransmissionSign.POSITIVE, "minutes_to_hours"),
]

NFP_STRONG_PATH_RATES = [
    TransmissionEdge("strong_growth_surprise", "higher_rates_for_longer", TransmissionSign.NEGATIVE, "minutes"),
    TransmissionEdge("higher_rates_for_longer", "yields_and_dollar_up", TransmissionSign.NEGATIVE, "minutes_to_hours"),
    TransmissionEdge("yields_and_dollar_up", "crypto_pressure", TransmissionSign.NEGATIVE, "hours"),
]


def get_default_transmission_paths(family: EventFamily, direction: str) -> List[TransmissionEdge]:
    if family in (EventFamily.CPI_HEADLINE, EventFamily.CPI_CORE, EventFamily.CORE_PCE):
        if direction == "below_consensus":
            return LOWER_INFLATION_PATH
        elif direction == "above_consensus":
            return HIGHER_INFLATION_PATH
    elif family in (EventFamily.NONFARM_PAYROLLS, EventFamily.UNEMPLOYMENT_RATE):
        if direction == "above_consensus":
            return NFP_STRONG_PATH_GROWTH
        elif direction == "below_consensus":
            return NFP_STRONG_PATH_RATES
    return []
