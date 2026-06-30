"""F05: Eight executable strategy components.

Each has deterministic eligibility, trigger, confirmation,
disqualifiers, horizon, expiry, invalidation, abstention.
Missing required inputs -> reject or abstain.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from market_radar.cognition.strategy_components import StrategySpec, StrategyStatus



def event_surprise_momentum_v1_spec() -> StrategySpec:
    return StrategySpec(
        strategy_id="event_surprise_momentum_v1",
        name="Event Surprise Momentum",
        thesis="Unexpected events drive momentum in the direction of the surprise.",
        applicable_domains=['macro_and_liquidity', 'regulatory_and_geopolitical', 'security_and_operational'],
        applicable_regimes=['risk_on', 'risk_off', 'mixed'],
        required_variables=['signed_surprise', 'price_return'],
        trigger="abs(signed_surprise) > 2.0 AND price_movement_direction == surprise_direction",
        confirmation="volume_expansion_ratio > 1.5",
        disqualifiers=['no_defensible_expectation', 'stale_baseline'],
        time_horizon="short",
        expiry_condition="price_reversal_within_24h",
        invalidation_condition="surprise_fully_reversed_within_48h",
    )



def post_event_underreaction_v1_spec() -> StrategySpec:
    return StrategySpec(
        strategy_id="post_event_underreaction_v1",
        name="Post-Event Underreaction",
        thesis="Markets underreact to significant events, creating drift opportunity.",
        applicable_domains=['macro_and_liquidity', 'regulatory_and_geopolitical'],
        applicable_regimes=['risk_on', 'risk_off'],
        required_variables=['signed_surprise', 'price_return', 'volume_24h'],
        trigger="abs(signed_surprise) > 3.0 AND abs(price_return_1h) < abs(signed_surprise) * 0.5",
        confirmation="volume_24h > baseline_volume * 1.2 AND price_continues_same_direction",
        disqualifiers=['full_immediate_reaction', 'liquidity_crisis'],
        time_horizon="medium",
        expiry_condition="price_reaches_full_surprise",
        invalidation_condition="opposite_price_move",
        abstention_conditions=["missing_required_inputs"],
    )



def overreaction_reversal_v1_spec() -> StrategySpec:
    return StrategySpec(
        strategy_id="overreaction_reversal_v1",
        name="Overreaction / Reversal",
        thesis="Extreme initial moves reverse as the market corrects overreaction.",
        applicable_domains=['macro_and_liquidity', 'spot_and_cross_asset'],
        applicable_regimes=['risk_on', 'risk_off'],
        required_variables=['price_return', 'volume_24h'],
        trigger="abs(price_return_1h) > 5.0 AND volume_24h > baseline_volume * 2.0",
        confirmation="price_retraces > 50% of initial_move within 24h",
        disqualifiers=['trend_following_regime', 'structural_break'],
        time_horizon="short",
        expiry_condition="no_reversal_within_48h",
        invalidation_condition="price_extends_beyond_initial_move",
        abstention_conditions=["missing_required_inputs"],
    )



def cross_asset_relative_strength_v1_spec() -> StrategySpec:
    return StrategySpec(
        strategy_id="cross_asset_relative_strength_v1",
        name="Cross-Asset Relative Strength",
        thesis="Relative performance between BTC and ETH signals rotation.",
        applicable_domains=['spot_and_cross_asset'],
        applicable_regimes=['risk_on', 'mixed'],
        required_variables=['btc_return_24h', 'eth_return_24h'],
        trigger="abs(btc_return_24h - eth_return_24h) > 3.0",
        confirmation="divergence_persists_for_6h",
        disqualifiers=['correlated_market', 'low_volume_regime'],
        time_horizon="medium",
        expiry_condition="divergence_reverts",
        invalidation_condition="correlation_breaks_down",
        abstention_conditions=["missing_required_inputs"],
    )



def liquidation_leverage_dislocation_v1_spec() -> StrategySpec:
    return StrategySpec(
        strategy_id="liquidation_leverage_dislocation_v1",
        name="Liquidation / Leverage Dislocation",
        thesis="Extreme funding rates signal crowded positioning and mean reversion.",
        applicable_domains=['derivatives_and_positioning'],
        applicable_regimes=['risk_on', 'risk_off'],
        required_variables=['funding_rate', 'open_interest'],
        trigger="abs(funding_rate) > 0.001",
        confirmation="funding_rate_returns_toward_zero",
        disqualifiers=['structural_regime_change'],
        time_horizon="short",
        expiry_condition="no_funding_normalization",
        invalidation_condition="funding_stays_extreme",
        abstention_conditions=["missing_required_inputs"],
    )



def onchain_flow_confirmation_v1_spec() -> StrategySpec:
    return StrategySpec(
        strategy_id="onchain_flow_confirmation_v1",
        name="On-Chain / Stablecoin Flow Confirmation",
        thesis="Exchange netflows and stablecoin supply confirm price direction.",
        applicable_domains=['onchain_and_whales', 'stablecoin_liquidity'],
        applicable_regimes=['risk_on', 'risk_off', 'mixed'],
        required_variables=['exchange_netflow', 'stablecoin_liquidity'],
        trigger="exchange_netflow > 0 AND stablecoin_liquidity > 0",
        confirmation="price_direction_matches_flow",
        disqualifiers=['no_onchain_data'],
        time_horizon="medium",
        expiry_condition="flow_reverses",
        invalidation_condition="price_diverges_from_flow",
        abstention_conditions=["missing_required_inputs"],
    )



def supply_unlock_pressure_v1_spec() -> StrategySpec:
    return StrategySpec(
        strategy_id="supply_unlock_pressure_v1",
        name="Supply / Unlock Pressure",
        thesis="Token unlocks and supply increases create predictable selling pressure.",
        applicable_domains=['token_supply_and_unlocks'],
        applicable_regimes=['mixed', 'risk_off'],
        required_variables=['unlock_amount', 'circulating_supply'],
        trigger="unlock_amount / circulating_supply > 0.01",
        confirmation="price_declines_within_7d_of_unlock",
        disqualifiers=['no_unlock_schedule'],
        time_horizon="medium",
        expiry_condition="no_price_impact_within_14d",
        invalidation_condition="price_increases_after_unlock",
        abstention_conditions=["missing_required_inputs"],
    )



def security_protocol_contagion_v1_spec() -> StrategySpec:
    return StrategySpec(
        strategy_id="security_protocol_contagion_v1",
        name="Security / Protocol Contagion",
        thesis="Security incidents cause localized selling that may spread.",
        applicable_domains=['security_and_operational'],
        applicable_regimes=['risk_off'],
        required_variables=['incident_severity', 'affected_tvl'],
        trigger="incident_severity == 'critical' AND affected_tvl > 10M",
        confirmation="price_drops_across_related_protocols",
        disqualifiers=['patched_before_exploitation', 'no_ecosystem_exposure'],
        time_horizon="short",
        expiry_condition="containment_within_24h",
        invalidation_condition="contagion_spreads_beyond_crypto",
        abstention_conditions=["missing_required_inputs"],
    )


def get_all_strategy_specs() -> List[StrategySpec]:
    return [
        event_surprise_momentum_v1_spec(),
        post_event_underreaction_v1_spec(),
        overreaction_reversal_v1_spec(),
        cross_asset_relative_strength_v1_spec(),
        liquidation_leverage_dislocation_v1_spec(),
        onchain_flow_confirmation_v1_spec(),
        supply_unlock_pressure_v1_spec(),
        security_protocol_contagion_v1_spec(),
    ]


def evaluate_strategy_eligibility(spec: StrategySpec,
        available_variables: Dict[str, Any]) -> Tuple[bool, str]:
    """Check if a strategy has all required inputs available."""
    missing = [v for v in spec.required_variables
               if v not in available_variables
               or available_variables.get(v) is None]
    if missing:
        return False, f"missing_inputs: {missing}"
    return True, ""
