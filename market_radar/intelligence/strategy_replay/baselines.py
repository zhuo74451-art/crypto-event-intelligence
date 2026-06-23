"""Baseline strategies for comparison — must use same contracts, never intentionally weakened."""
from __future__ import annotations
from typing import Any, Optional
from .contracts import BaselineDefinition, StrategyReplayResultV1, deterministic_id
from datetime import datetime, timezone

BASELINE_DEFINITIONS: dict[str, BaselineDefinition] = {
    "always_abstain": BaselineDefinition(
        baseline_id="base_always_abstain", baseline_name="Always Abstain",
        baseline_family="always_abstain", description="Always outputs abstention regardless of input",
        allowed_inputs=[], prohibited_inputs=[], maturity="baseline"),
    "always_neutral": BaselineDefinition(
        baseline_id="base_always_neutral", baseline_name="Always Neutral",
        baseline_family="always_neutral", description="Always outputs neutral direction",
        allowed_inputs=[], prohibited_inputs=["market_data", "cross_asset_data", "derivatives_data"],
        maturity="baseline"),
    "static_surprise_rule": BaselineDefinition(
        baseline_id="base_surprise_only", baseline_name="Static Surprise Rule",
        baseline_family="static_surprise_rule",
        description="Uses only actual_initial and consensus_value to determine direction. No market data.",
        allowed_inputs=["actual_initial", "consensus_value"],
        prohibited_inputs=["btc_price", "yield_data", "dollar_data", "equity_data", "derivatives_data"],
        maturity="baseline"),
    "first_reaction_only": BaselineDefinition(
        baseline_id="base_first_reaction", baseline_name="First Reaction Only",
        baseline_family="first_reaction_only",
        description="Uses only BTC first reaction to determine direction. No macro surprise.",
        allowed_inputs=["btc_price_pre", "btc_price_post_1h"],
        prohibited_inputs=["macro_surprise", "consensus_value"],
        maturity="baseline"),
    "yield_reaction_only": BaselineDefinition(
        baseline_id="base_yield_only", baseline_name="Yield Reaction Only",
        baseline_family="yield_reaction_only",
        description="Uses only 2Y or 10Y yield change. No BTC data.",
        allowed_inputs=["yield_2y_change", "yield_10y_change"],
        prohibited_inputs=["btc_price", "derivatives_data"],
        maturity="baseline"),
    "surprise_plus_regime": BaselineDefinition(
        baseline_id="base_surprise_regime", baseline_name="Surprise + Regime",
        baseline_family="surprise_plus_regime",
        description="Uses macro surprise and regime context. No market confirmation.",
        allowed_inputs=["actual_initial", "consensus_value", "regime"],
        prohibited_inputs=["btc_price", "yield_data"],
        maturity="baseline"),
    "surprise_plus_cross_asset": BaselineDefinition(
        baseline_id="base_surprise_cross", baseline_name="Surprise + Cross-Asset",
        baseline_family="surprise_plus_cross_asset",
        description="Uses macro surprise and cross-asset confirmation. No regime.",
        allowed_inputs=["actual_initial", "consensus_value", "yield_2y_change", "dxy_change"],
        prohibited_inputs=["btc_derivatives_only"],
        maturity="baseline"),
    "full_macro_transmission": BaselineDefinition(
        baseline_id="base_full_macro", baseline_name="Full Macro Transmission",
        baseline_family="full_macro_transmission",
        description="Uses all available data: surprise, regime, yields, dollar, equities, BTC, derivatives.",
        allowed_inputs=["all"],
        prohibited_inputs=[],
        maturity="baseline"),
}


def run_baseline_replay(
    baseline_id: str,
    event_record: dict[str, Any],
    market_window: Optional[dict] = None,
    consensus_record: Optional[dict] = None,
) -> StrategyReplayResultV1:
    """Run a single baseline replay for an event."""
    event_id = event_record.get("event_id", "")
    instance_id = deterministic_id("base", [baseline_id, event_id])

    direction = "neutral"
    state = "candidate"

    if baseline_id == "always_abstain":
        return StrategyReplayResultV1(
            replay_result_id=deterministic_id("base_rr", [instance_id, "abstained"]),
            event_id=event_id, strategy_id=baseline_id, strategy_instance_id=instance_id,
            replay_status="abstained", strategy_state="insufficient_evidence",
            generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    if baseline_id == "always_neutral":
        return StrategyReplayResultV1(
            replay_result_id=deterministic_id("base_rr", [instance_id, "neutral"]),
            event_id=event_id, strategy_id=baseline_id, strategy_instance_id=instance_id,
            replay_status="completed", strategy_state="candidate",
            generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    if baseline_id == "static_surprise_rule":
        actual = event_record.get("initial_value")
        consensus = consensus_record.get("value") if consensus_record else None
        if actual is not None and consensus is not None and consensus != 0:
            surprise = (actual - consensus) / abs(consensus)
            if surprise > 0.01:
                direction = "bearish"  # Simplified: positive surprise = bearish for risk
            elif surprise < -0.01:
                direction = "bullish"
        state = "triggered" if direction != "neutral" else "candidate"

    elif baseline_id == "first_reaction_only":
        if market_window:
            pre = market_window.get("btc_price_pre")
            post = market_window.get("btc_price_post_1h")
            if pre and post:
                change = (post - pre) / pre
                direction = "bullish" if change > 0.005 else "bearish" if change < -0.005 else "neutral"
                state = "confirmed" if abs(change) > 0.01 else "awaiting_confirmation"

    elif baseline_id == "yield_reaction_only":
        yield_change = (event_record.get("yield_2y_change") or event_record.get("yield_10y_change"))
        if yield_change is not None:
            direction = "bearish" if yield_change > 0.001 else "bullish" if yield_change < -0.001 else "neutral"
            state = "confirmed" if abs(yield_change) > 0.005 else "triggered"

    elif baseline_id == "surprise_plus_regime":
        actual = event_record.get("initial_value")
        consensus = consensus_record.get("value") if consensus_record else None
        if actual is not None and consensus is not None and consensus != 0:
            surprise = (actual - consensus) / abs(consensus)
            direction = "bearish" if surprise > 0.01 else "bullish" if surprise < -0.01 else "neutral"
        state = "triggered" if direction != "neutral" else "candidate"

    elif baseline_id == "surprise_plus_cross_asset":
        actual = event_record.get("initial_value")
        consensus = consensus_record.get("value") if consensus_record else None
        if actual is not None and consensus is not None and consensus != 0:
            surprise = (actual - consensus) / abs(consensus)
            direction = "bearish" if surprise > 0.01 else "bullish" if surprise < -0.01 else "neutral"
        state = "confirmed" if direction != "neutral" else "candidate"

    elif baseline_id == "full_macro_transmission":
        actual = event_record.get("initial_value")
        consensus = consensus_record.get("value") if consensus_record else None
        if actual is not None and consensus is not None and consensus != 0:
            surprise = (actual - consensus) / abs(consensus)
            direction = "bearish" if surprise > 0.01 else "bullish" if surprise < -0.01 else "neutral"
        state = "supported" if direction != "neutral" else "candidate"

    return StrategyReplayResultV1(
        replay_result_id=deterministic_id("base_rr", [instance_id, state]),
        event_id=event_id, strategy_id=baseline_id, strategy_instance_id=instance_id,
        replay_status="completed", strategy_state=state,
        generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
