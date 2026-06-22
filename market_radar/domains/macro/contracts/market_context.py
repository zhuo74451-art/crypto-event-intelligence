from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from .common import MacroEnum


class LiquidityCondition(MacroEnum):
    """Prevailing liquidity conditions in the market."""
    VERY_LIQUID = "very_liquid"
    LIQUID = "liquid"
    NORMAL = "normal"
    ILLIQUID = "illiquid"
    STRESSED = "stressed"
    UNKNOWN = "unknown"


class RiskAppetite(MacroEnum):
    """Market risk appetite / sentiment regime."""
    RISK_ON = "risk_on"
    CAUTIOUS = "cautious"
    NEUTRAL = "neutral"
    RISK_OFF = "risk_off"
    FLIGHT_TO_SAFETY = "flight_to_safety"
    UNKNOWN = "unknown"


class VolatilityCondition(MacroEnum):
    """Observed or implied volatility regime."""
    EXTREMELY_LOW = "extremely_low"
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"
    UNKNOWN = "unknown"


class TrendCondition(MacroEnum):
    """Dominant trend direction / structure."""
    STRONG_UPTREND = "strong_uptrend"
    UPTREND = "uptrend"
    SIDEWAYS = "sideways"
    DOWNTREND = "downtrend"
    STRONG_DOWNTREND = "strong_downtrend"
    CHOPPY = "choppy"
    UNKNOWN = "unknown"


class LeverageCondition(MacroEnum):
    """Estimated leverage / positioning intensity."""
    VERY_OVERLEVERAGED = "very_overleveraged"
    OVERLEVERAGED = "overleveraged"
    NEUTRAL = "neutral"
    UNDERLEVERAGED = "underleveraged"
    VERY_UNDERLEVERAGED = "very_underleveraged"
    UNKNOWN = "unknown"


class GrowthInflationRegime(MacroEnum):
    """Macro regime based on the interaction of growth and inflation."""
    GROWTH_UP_INFLATION_UP = "growth_up_inflation_up"
    GROWTH_UP_INFLATION_DOWN = "growth_up_inflation_down"
    GROWTH_DOWN_INFLATION_UP = "growth_down_inflation_up"
    GROWTH_DOWN_INFLATION_DOWN = "growth_down_inflation_down"
    TRANSITION = "transition"
    UNKNOWN = "unknown"


class PolicyExpectationRegime(MacroEnum):
    """Market-implied expectation of central bank policy trajectory."""
    HAWKISH_TIGHTENING = "hawkish_tightening"
    HIGHER_FOR_LONGER = "higher_for_longer"
    NEUTRAL = "neutral"
    EASING_EXPECTED = "easing_expected"
    ACTIVE_EASING = "active_easing"
    POLICY_UNCERTAIN = "policy_uncertain"
