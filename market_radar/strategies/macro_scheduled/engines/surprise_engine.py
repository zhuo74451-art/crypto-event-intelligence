from __future__ import annotations
import math
from typing import Dict, List, Optional
from market_radar.strategies.macro_scheduled.contracts.surprise import (
    ComponentSurprise, CompositeSurpriseContext, DirectionalInterpretation,
    StandardizationStatus,
)
from market_radar.domains.macro.contracts.common import UnitType
from market_radar.domains.macro.contracts.market_context import GrowthInflationRegime
from market_radar.domains.macro.taxonomy.event_types import EventFamily


class SurpriseEngine:
    @staticmethod
    def compute_raw_gap(actual: Optional[float], expected: Optional[float]) -> Optional[float]:
        if actual is None or expected is None:
            return None
        return actual - expected

    @staticmethod
    def compute_relative_gap(actual: Optional[float], expected: Optional[float]) -> Optional[float]:
        if actual is None or expected is None or expected == 0:
            return None
        return (actual - expected) / abs(expected)

    @staticmethod
    def compute_standardized_gap(actual: Optional[float], expected: Optional[float],
                                  std_dev: Optional[float], sample_count: Optional[int]) -> Optional[float]:
        if actual is None or expected is None or std_dev is None or std_dev == 0:
            return None
        if sample_count is not None and sample_count < 10:
            return None
        return (actual - expected) / std_dev

    @staticmethod
    def compute_component_surprise(component_id: str, actual: Optional[float],
                                    expected: Optional[float],
                                    std_dev: Optional[float] = None,
                                    sample_count: Optional[int] = None) -> ComponentSurprise:
        raw = SurpriseEngine.compute_raw_gap(actual, expected)
        rel = SurpriseEngine.compute_relative_gap(actual, expected)
        std = SurpriseEngine.compute_standardized_gap(actual, expected, std_dev, sample_count)
        std_status = StandardizationStatus.AVAILABLE if std is not None else (
            StandardizationStatus.INSUFFICIENT_SAMPLE if (sample_count is not None and sample_count < 10) else StandardizationStatus.UNAVAILABLE
        )
        sign = None
        if raw is not None:
            sign = "above" if raw > 0 else ("below" if raw < 0 else "inline")
        return ComponentSurprise(
            component_id=component_id,
            actual_value=actual,
            expected_value=expected,
            raw_gap=raw,
            relative_gap=rel,
            standardized_gap=std,
            standardization_status=std_status,
            sign=sign,
        )

    @staticmethod
    def compute_composite_surprise(components: List[ComponentSurprise]) -> CompositeSurpriseContext:
        comps: Dict[str, ComponentSurprise] = {}
        has_conflict = False
        directions = set()

        for c in components:
            comps[c.component_id] = c
            if c.sign == "above":
                directions.add("above")
            elif c.sign == "below":
                directions.add("below")

        if len(directions) >= 2:
            has_conflict = True

        # Determine primary direction
        primary = None
        if "below" in directions and "above" not in directions:
            primary = DirectionalInterpretation.BULLISH
        elif "above" in directions and "below" not in directions:
            primary = DirectionalInterpretation.BEARISH
        elif has_conflict:
            primary = DirectionalInterpretation.AMBIGUOUS

        return CompositeSurpriseContext(
            components=comps,
            has_conflict=has_conflict,
            primary_direction=primary,
        )

    @staticmethod
    def determine_direction(component_surprise: ComponentSurprise,
                             event_family: EventFamily,
                             regime: Optional[GrowthInflationRegime] = None) -> DirectionalInterpretation:
        """Determine directional interpretation based on event type and regime."""
        if component_surprise.sign == "inline" or component_surprise.sign is None:
            return DirectionalInterpretation.NEUTRAL

        is_below = component_surprise.sign == "below"
        is_above = component_surprise.sign == "above"

        # CPI: below consensus is typically bullish for risk (lower rates)
        if event_family in (EventFamily.CPI_HEADLINE, EventFamily.CPI_CORE, EventFamily.CORE_PCE):
            if is_below:
                if regime == GrowthInflationRegime.GROWTH_DOWN_INFLATION_DOWN:
                    return DirectionalInterpretation.AMBIGUOUS  # deflation concern
                return DirectionalInterpretation.BULLISH
            if is_above:
                if regime == GrowthInflationRegime.GROWTH_UP_INFLATION_UP:
                    return DirectionalInterpretation.BEARISH
                return DirectionalInterpretation.BEARISH

        # NFP: strong growth can be bullish (growth channel) or bearish (rates channel)
        if event_family == EventFamily.NONFARM_PAYROLLS:
            if is_above:
                if regime == GrowthInflationRegime.GROWTH_UP_INFLATION_UP:
                    return DirectionalInterpretation.AMBIGUOUS  # competing channels
                return DirectionalInterpretation.BULLISH  # growth channel
            if is_below:
                if regime == GrowthInflationRegime.GROWTH_DOWN_INFLATION_DOWN:
                    return DirectionalInterpretation.BEARISH  # recession fear
                return DirectionalInterpretation.BEARISH

        # FOMC
        if event_family in (EventFamily.FOMC_RATE_DECISION, EventFamily.FOMC_STATEMENT):
            if is_below:  # Dovish surprise (lower rates)
                return DirectionalInterpretation.BULLISH
            if is_above:  # Hawkish surprise (higher rates)
                return DirectionalInterpretation.BEARISH

        return DirectionalInterpretation.EVENT_SPECIFIC
