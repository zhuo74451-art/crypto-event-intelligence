from __future__ import annotations
from typing import Dict, List, Optional
from market_radar.domains.macro.contracts.market_context import (
    GrowthInflationRegime, PolicyExpectationRegime,
    LiquidityCondition, RiskAppetite, VolatilityCondition,
)
from market_radar.strategies.macro_scheduled.contracts.regime_context import RegimeContext, RegimeQuality


class MacroRegimeAdapter:
    @staticmethod
    def classify_growth_inflation(growth_trend: Optional[str], inflation_trend: Optional[str]) -> GrowthInflationRegime:
        if growth_trend is None or inflation_trend is None:
            return GrowthInflationRegime.UNKNOWN
        g_up = "up" in growth_trend.lower()
        g_down = "down" in growth_trend.lower()
        i_up = "up" in inflation_trend.lower()
        i_down = "down" in inflation_trend.lower()
        if g_up and i_up:
            return GrowthInflationRegime.GROWTH_UP_INFLATION_UP
        if g_up and i_down:
            return GrowthInflationRegime.GROWTH_UP_INFLATION_DOWN
        if g_down and i_up:
            return GrowthInflationRegime.GROWTH_DOWN_INFLATION_UP
        if g_down and i_down:
            return GrowthInflationRegime.GROWTH_DOWN_INFLATION_DOWN
        return GrowthInflationRegime.TRANSITION

    @staticmethod
    def classify_policy_expectation(rates_trend: Optional[str],
                                     forward_guidance: Optional[str]) -> PolicyExpectationRegime:
        if rates_trend is None:
            return PolicyExpectationRegime.POLICY_UNCERTAIN
        if "tightening" in rates_trend.lower() or "hike" in rates_trend.lower():
            return PolicyExpectationRegime.HAWKISH_TIGHTENING
        if "hold" in rates_trend.lower() or "higher_for_longer" in rates_trend.lower():
            return PolicyExpectationRegime.HIGHER_FOR_LONGER
        if "cut" in rates_trend.lower() or "easing" in rates_trend.lower():
            return PolicyExpectationRegime.ACTIVE_EASING
        if "expected" in rates_trend.lower() or "priced" in rates_trend.lower():
            return PolicyExpectationRegime.EASING_EXPECTED
        return PolicyExpectationRegime.NEUTRAL

    @staticmethod
    def build_regime_context(growth_trend: Optional[str] = None,
                              inflation_trend: Optional[str] = None,
                              rates_trend: Optional[str] = None,
                              liquidity: Optional[str] = None,
                              risk: Optional[str] = None,
                              volatility: Optional[str] = None,
                              quality: RegimeQuality = RegimeQuality.INSUFFICIENT) -> RegimeContext:
        gi = MacroRegimeAdapter.classify_growth_inflation(growth_trend, inflation_trend)
        pe = PolicyExpectationRegime.POLICY_UNCERTAIN
        if rates_trend:
            pe = MacroRegimeAdapter.classify_policy_expectation(rates_trend, None)
        liq = LiquidityCondition.UNKNOWN
        if liquidity:
            try:
                liq = LiquidityCondition(liquidity)
            except ValueError:
                pass
        rap = RiskAppetite.UNKNOWN
        if risk:
            try:
                rap = RiskAppetite(risk)
            except ValueError:
                pass
        vol = VolatilityCondition.UNKNOWN
        if volatility:
            try:
                vol = VolatilityCondition(volatility)
            except ValueError:
                pass
        input_count = sum(1 for x in [growth_trend, inflation_trend, rates_trend] if x is not None)
        if input_count < 2:
            quality = RegimeQuality.INSUFFICIENT
        elif input_count == 2:
            quality = max(quality, RegimeQuality.WEAK) if quality else RegimeQuality.WEAK
        else:
            quality = max(quality, RegimeQuality.MODERATE) if quality else RegimeQuality.MODERATE
        return RegimeContext(
            growth_inflation=gi,
            policy_expectation=pe,
            liquidity=liq,
            risk_appetite=rap,
            volatility=vol,
            quality=quality,
        )
