"""S02: Executable strategy evaluators -- rules as code, not strings."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from market_radar.cognition.strategy_components import StrategySpec
from market_radar.cognition.strategy_library import get_all_strategy_specs


@dataclass
class StrategyEvaluation:
    strategy_id: str = ""
    version: str = "1.0"
    status: str = "rejected"
    trigger_result: bool = False
    trigger_reason: str = ""
    confirmation_result: bool = False
    confirmation_reason: str = ""
    disqualifier_result: bool = False
    disqualifier_reason: str = ""
    regime_fit: bool = False
    priced_in_compatibility: bool = False
    required_variables: list = field(default_factory=list)
    missing_variables: list = field(default_factory=list)
    supporting_evidence: list = field(default_factory=list)
    contradicting_evidence: list = field(default_factory=list)
    research_claim_status: str = ""
    expiry: str = ""
    invalidation: str = ""
    reason_codes: list = field(default_factory=list)


# 1. Event Surprise Momentum
def eval_surprise_momentum(vars_):
    e = StrategyEvaluation(strategy_id="event_surprise_momentum_v1")
    s = vars_.get("signed_surprise")
    pr = vars_.get("price_return")
    if s is None or pr is None:
        e.status = "abstained"
        e.missing_variables = [v for v in ["signed_surprise", "price_return"] if vars_.get(v) is None]
        e.reason_codes.append("missing_inputs")
        return e
    e.trigger_result = abs(s) > 2.0
    e.trigger_reason = f"surprise={s}"
    if not e.trigger_result:
        e.status = "rejected"
        e.reason_codes.append("trigger_not_met")
        return e
    e.status = "eligible"
    e.confirmation_result = pr is not None and abs(pr) > 1.0
    e.expiry = "price_reversal_within_24h"
    e.invalidation = "surprise_fully_reversed_within_48h"
    e.reason_codes.append("trigger_met")
    return e


# 2. Post-Event Underreaction
def eval_underreaction(vars_):
    e = StrategyEvaluation(strategy_id="post_event_underreaction_v1")
    s = vars_.get("signed_surprise")
    pr = vars_.get("price_return")
    if s is None or pr is None:
        e.status = "abstained"
        e.missing_variables = ["signed_surprise", "price_return"]
        e.reason_codes.append("missing_inputs")
        return e
    ratio = abs(pr) / abs(s) if s != 0 else 0
    e.trigger_result = abs(s) > 3.0 and ratio < 0.5
    e.trigger_reason = f"surprise={s}, price_return={pr}, ratio={ratio:.2f}"
    if not e.trigger_result:
        e.status = "rejected"
        e.reason_codes.append("trigger_not_met")
        return e
    e.status = "eligible"
    e.expiry = "price_reaches_full_surprise"
    e.invalidation = "opposite_price_move"
    e.reason_codes.append("underreaction_detected")
    return e


# 3. Overreaction / Reversal
def eval_overreaction(vars_):
    e = StrategyEvaluation(strategy_id="overreaction_reversal_v1")
    pr = vars_.get("price_return")
    vol = vars_.get("volume_24h")
    if pr is None:
        e.status = "abstained"
        e.missing_variables = ["price_return"]
        e.reason_codes.append("missing_inputs")
        return e
    vol_ok = vol is not None and vol > 0
    e.trigger_result = abs(pr) > 5.0 and vol_ok
    e.trigger_reason = f"price_return={pr}, volume_24h={vol}"
    if not e.trigger_result:
        e.status = "rejected"
        e.reason_codes.append("trigger_not_met")
        return e
    e.status = "eligible"
    e.expiry = "no_reversal_within_48h"
    e.invalidation = "price_extends_beyond_initial_move"
    e.reason_codes.append("overreaction_detected")
    return e


# 4. Cross-Asset Relative Strength
def eval_cross_asset(vars_):
    e = StrategyEvaluation(strategy_id="cross_asset_relative_strength_v1")
    btc = vars_.get("btc_return_24h")
    eth = vars_.get("eth_return_24h")
    if btc is None or eth is None:
        e.status = "abstained"
        e.missing_variables = [v for v in ["btc_return_24h", "eth_return_24h"] if vars_.get(v) is None]
        e.reason_codes.append("missing_inputs")
        return e
    e.trigger_result = abs(btc - eth) > 3.0
    e.trigger_reason = f"btc={btc}, eth={eth}, diff={abs(btc-eth):.1f}"
    if not e.trigger_result:
        e.status = "rejected"
        e.reason_codes.append("trigger_not_met")
        return e
    e.status = "eligible"
    e.expiry = "divergence_reverts"
    e.invalidation = "correlation_breaks_down"
    e.reason_codes.append("divergence_detected")
    return e


# 5. Liquidation / Leverage Dislocation
def eval_leverage(vars_):
    e = StrategyEvaluation(strategy_id="liquidation_leverage_dislocation_v1")
    fr = vars_.get("funding_rate")
    if fr is None:
        e.status = "abstained"
        e.missing_variables = ["funding_rate"]
        e.reason_codes.append("missing_inputs")
        return e
    e.trigger_result = abs(fr) > 0.001
    e.trigger_reason = f"funding_rate={fr}"
    if not e.trigger_result:
        e.status = "rejected"
        e.reason_codes.append("trigger_not_met")
        return e
    e.status = "eligible"
    e.expiry = "no_funding_normalization"
    e.invalidation = "funding_stays_extreme"
    e.reason_codes.append("leverage_dislocation_detected")
    return e


# 6. On-Chain Flow Confirmation
def eval_onchain(vars_):
    e = StrategyEvaluation(strategy_id="onchain_flow_confirmation_v1")
    nf = vars_.get("exchange_netflow")
    sl = vars_.get("stablecoin_liquidity")
    if nf is None or sl is None:
        e.status = "abstained"
        e.missing_variables = [v for v in ["exchange_netflow", "stablecoin_liquidity"] if vars_.get(v) is None]
        e.reason_codes.append("missing_inputs")
        return e
    e.trigger_result = nf > 0 and sl > 0
    e.trigger_reason = f"netflow={nf}, stablecoin_liquidity={sl}"
    if not e.trigger_result:
        e.status = "rejected"
        e.reason_codes.append("trigger_not_met")
        return e
    e.status = "eligible"
    e.expiry = "flow_reverses"
    e.invalidation = "price_diverges_from_flow"
    e.reason_codes.append("flow_confirmation_detected")
    return e


# 7. Supply / Unlock Pressure
def eval_supply_unlock(vars_):
    e = StrategyEvaluation(strategy_id="supply_unlock_pressure_v1")
    unlock = vars_.get("unlock_amount")
    supply = vars_.get("circulating_supply")
    if unlock is None or supply is None or supply == 0:
        e.status = "abstained"
        e.missing_variables = [v for v in ["unlock_amount", "circulating_supply"] if vars_.get(v) is None]
        e.reason_codes.append("missing_inputs")
        return e
    e.trigger_result = unlock / supply > 0.01
    e.trigger_reason = f"unlock/supply={unlock}/{supply}={unlock/supply:.4f}"
    if not e.trigger_result:
        e.status = "rejected"
        e.reason_codes.append("trigger_not_met")
        return e
    e.status = "eligible"
    e.expiry = "no_price_impact_within_14d"
    e.invalidation = "price_increases_after_unlock"
    e.reason_codes.append("unlock_pressure_detected")
    return e


# 8. Security / Protocol Contagion
def eval_contagion(vars_):
    e = StrategyEvaluation(strategy_id="security_protocol_contagion_v1")
    sev = vars_.get("incident_severity")
    tvl = vars_.get("affected_tvl")
    if sev is None or tvl is None:
        e.status = "abstained"
        e.missing_variables = [v for v in ["incident_severity", "affected_tvl"] if vars_.get(v) is None]
        e.reason_codes.append("missing_inputs")
        return e
    e.trigger_result = sev == "critical" and tvl > 10_000_000
    e.trigger_reason = f"severity={sev}, tvl={tvl}"
    if not e.trigger_result:
        e.status = "rejected"
        e.reason_codes.append("trigger_not_met")
        return e
    e.status = "eligible"
    e.expiry = "containment_within_24h"
    e.invalidation = "contagion_spreads_beyond_crypto"
    e.reason_codes.append("contagion_detected")
    return e


_EVALUATORS = {
    "event_surprise_momentum_v1": eval_surprise_momentum,
    "post_event_underreaction_v1": eval_underreaction,
    "overreaction_reversal_v1": eval_overreaction,
    "cross_asset_relative_strength_v1": eval_cross_asset,
    "liquidation_leverage_dislocation_v1": eval_leverage,
    "onchain_flow_confirmation_v1": eval_onchain,
    "supply_unlock_pressure_v1": eval_supply_unlock,
    "security_protocol_contagion_v1": eval_contagion,
}


def evaluate_all(vars_) -> list:
    results = []
    for sid, fn in _EVALUATORS.items():
        try:
            results.append(fn(vars_))
        except Exception as ex:
            from market_radar.cognition.strategy_evaluators import StrategyEvaluation
            results.append(StrategyEvaluation(
                strategy_id=sid, status="rejected",
                reason_codes=[f"evaluation_error: {ex}"]))
    return results


def get_evaluator_ids() -> list:
    return list(_EVALUATORS.keys())
