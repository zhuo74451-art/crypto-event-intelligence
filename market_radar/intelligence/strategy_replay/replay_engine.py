"""Replay engine — deterministic batch replay of macro events through strategies."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any, Optional

from .contracts import (
    StrategyDefinitionV1, StrategyReplayResultV1, StrategyHypothesisV1,
    KernelInputPackageV1, MarketConfirmation, deterministic_id,
)
from .state_machine import compute_next_state
from .replay_clock import ReplayCutoffs, build_default_cutoffs, is_post_event_consensus
from .abstention import should_abstain, build_abstention_record
from .market_confirmation import evaluate_spot_confirmation, evaluate_cross_asset_confirmation, evaluate_derivatives_confirmation
from .kernel_adapter import build_arbitration_context, compute_kernel_package_id


def run_event_replay(
    event_record: dict[str, Any],
    consensus_record: Optional[dict[str, Any]] = None,
    market_window: Optional[dict[str, Any]] = None,
    cross_asset_state: Optional[dict[str, Any]] = None,
    derivative_state: Optional[dict[str, Any]] = None,
    strategy_definitions: Optional[list[StrategyDefinitionV1]] = None,
    regime_result: Optional[dict[str, Any]] = None,
    replay_cutoffs: Optional[ReplayCutoffs] = None,
) -> dict[str, Any]:
    """Run replay for a single event through all applicable strategies."""
    if strategy_definitions is None:
        strategy_definitions = []
    event_id = event_record.get("event_id", "")
    event_family = event_record.get("event_family", "")
    event_time_utc = event_record.get("release_time_utc", event_record.get("event_time_utc", ""))
    if not event_id or not event_family:
        return {"error": "Missing event_id or event_family", "event_id": event_id}
    if not replay_cutoffs:
        replay_cutoffs = build_default_cutoffs(event_time_utc)

    applicable = [s for s in strategy_definitions if event_family in s.supported_event_families]
    results, hypotheses, abstentions, kps = [], [], [], []

    for strategy in applicable:
        si_id = deterministic_id("si", [strategy.strategy_id, event_id])
        consensus_available = consensus_record is not None and consensus_record.get("value") is not None
        consensus_before = True
        if consensus_record and consensus_record.get("published_at_utc"):
            consensus_before = not is_post_event_consensus(consensus_record["published_at_utc"], event_time_utc)

        skip, reasons = should_abstain(
            consensus_available=consensus_available,
            consensus_before_event=consensus_before,
            point_in_time_grade=event_record.get("point_in_time_grade", "medium"),
            initial_value_verifiable=event_record.get("initial_value") is not None,
            event_time_reliable=bool(event_time_utc),
            market_window_available=market_window is not None,
        )

        if skip:
            abstentions.append(build_abstention_record(
                event_id=event_id, strategy_id=strategy.strategy_id,
                strategy_instance_id=si_id, reason_codes=reasons,
                information_cutoff_utc=replay_cutoffs.available_information_cutoff_utc))
            results.append(StrategyReplayResultV1(
                replay_result_id=deterministic_id("rr", [si_id, "abstained"]),
                event_id=event_id, strategy_id=strategy.strategy_id,
                strategy_instance_id=si_id, replay_status="abstained",
                strategy_state="insufficient_evidence",
                generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                available_information_cutoff_utc=replay_cutoffs.available_information_cutoff_utc))
            continue

        actual = event_record.get("initial_value")
        consensus = consensus_record.get("value") if consensus_record else None
        surprise, surprise_str = None, "neutral"
        if actual is not None and consensus is not None and consensus != 0:
            surprise = (actual - consensus) / abs(consensus)
            surprise_str = "positive" if surprise > 0.01 else "negative" if surprise < -0.01 else "neutral"

        has_surprise = surprise is not None
        has_macro = actual is not None and consensus is not None
        has_market = market_window is not None
        has_cross = cross_asset_state is not None and len(cross_asset_state) > 0

        expected_dir = "neutral"
        inf_fams = ("us_cpi", "us_core_cpi", "us_core_pce")
        if surprise_str == "positive" and strategy.strategy_family in inf_fams:
            expected_dir = "bearish"
        elif surprise_str == "negative" and strategy.strategy_family in inf_fams:
            expected_dir = "bullish"
        elif surprise_str == "positive" and strategy.strategy_family == "us_nonfarm_payrolls":
            expected_dir = "bullish"
        elif surprise_str == "negative" and strategy.strategy_family == "us_nonfarm_payrolls":
            expected_dir = "bearish"
        elif surprise_str == "positive" and strategy.strategy_family == "us_unemployment_rate":
            expected_dir = "bearish"
        elif surprise_str == "negative" and strategy.strategy_family == "us_unemployment_rate":
            expected_dir = "bullish"

        btc_pre = market_window.get("btc_price_pre") if market_window else None
        btc_post = market_window.get("btc_price_post_1h") if market_window else None
        spot_conf = evaluate_spot_confirmation(btc_pre_price=btc_pre, btc_post_price=btc_post, expected_direction=expected_dir)

        cross_conf = evaluate_cross_asset_confirmation(
            yield_2y_change=cross_asset_state.get("yield_2y_change") if cross_asset_state else None,
            dxy_change=cross_asset_state.get("dxy_change") if cross_asset_state else None,
            sp500_change=cross_asset_state.get("sp500_change") if cross_asset_state else None,
            expected_risk_direction="risk_off" if expected_dir == "bearish" else "risk_on")

        deriv_conf = evaluate_derivatives_confirmation(
            funding_rate_change=derivative_state.get("funding_change") if derivative_state else None,
            oi_change_pct=derivative_state.get("oi_change_pct") if derivative_state else None)

        has_contradiction = spot_conf.get("confirmed") is False and spot_conf.get("direction") not in ("neutral", expected_dir)
        if cross_conf.get("confirmation_level") == "contradicting":
            has_contradiction = True

        if spot_conf.get("confirmed") and cross_conf.get("confirmation_level") in ("spot_cross_asset_confirmed", "cross_asset_confirmed"):
            mk = MarketConfirmation.SPOT_CROSS_ASSET_CONFIRMED
        elif spot_conf.get("confirmed"):
            mk = MarketConfirmation.SPOT_CONFIRMED
        elif cross_conf.get("confirmation_level") in ("cross_asset_confirmed", "partial"):
            mk = MarketConfirmation.CROSS_ASSET_CONFIRMED
        elif deriv_conf.get("derivatives_only"):
            mk = MarketConfirmation.DERIVATIVES_ONLY
        elif cross_conf.get("confirmation_level") == "contradicting":
            mk = MarketConfirmation.CONTRADICTING
        else:
            mk = MarketConfirmation.AWAITING

        state = compute_next_state(
            current_state="candidate",
            has_surprise=has_surprise, has_macro_inputs=has_macro,
            has_market_data=has_market,
            has_cross_asset_confirmation=cross_conf.get("confirmation_level", "missing") in ("cross_asset_confirmed", "spot_cross_asset_confirmed", "partial"),
            has_derivatives_confirmation=deriv_conf.get("derivatives_only", False),
            has_contradiction=has_contradiction,
            missing_critical_inputs=not has_macro,
        )

        generated = []
        for horizon in strategy.supported_horizons:
            hyp = StrategyHypothesisV1(
                hypothesis_id=deterministic_id("hyp", [strategy.strategy_id, event_id, horizon]),
                strategy_id=strategy.strategy_id, strategy_instance_id=si_id,
                event_id=event_id, asset="BTC", time_horizon=horizon,
                expected_effect=expected_dir, strategy_state=state,
                market_confirmation=mk.value,
                transmission_signature="risk_off" if expected_dir == "bearish" else "risk_on",
                transmission_coherence="coherent" if not has_contradiction else "conflicting",
                transmission_conflicts=["spot_contradicts_macro"] if has_contradiction else [],
                confidence_type="directional",
                invalidation_conditions=list(strategy.invalidation_rules.values()),
                alternative_explanations=list(strategy.alternative_explanations))
            generated.append(hyp)

        rr_id = deterministic_id("rr", [si_id, state])
        result = StrategyReplayResultV1(
            replay_result_id=rr_id, event_id=event_id,
            strategy_id=strategy.strategy_id, strategy_instance_id=si_id,
            replay_status="completed", strategy_state=state,
            hypotheses=[h.hypothesis_id for h in generated],
            generated_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            available_information_cutoff_utc=replay_cutoffs.available_information_cutoff_utc)

        results.append(result)
        hypotheses.extend(generated)

        # Kernel package
        kp_id = compute_kernel_package_id(event_id, [strategy.strategy_id], [h.hypothesis_id for h in generated])
        contexts = {}
        for h in generated:
            contexts[h.hypothesis_id] = build_arbitration_context(h, strategy_origin_group=strategy.strategy_family)
        kp = KernelInputPackageV1(
            kernel_package_id=kp_id, event_id=event_id, asset="BTC",
            hypotheses=[h.__dict__ for h in generated],
            hypothesis_contexts={k: v.__dict__ for k, v in contexts.items()},
            evidence_state={"verdict": "compiled"},
            regime_state={"regime": regime_result.get("regime", "unknown")} if regime_result else {},
            source_strategy_ids=[strategy.strategy_id],
            source_replay_result_ids=[rr_id],
            information_cutoff_utc=replay_cutoffs.available_information_cutoff_utc,
            contract_versions={"strategy_replay": "1.0.0"})
        kps.append(kp)

    return {"results": results, "hypotheses": hypotheses, "abstentions": abstentions, "kernel_packages": kps,
            "event_id": event_id, "event_family": event_family}


def run_batch_replay(
    events: list[dict],
    strategies: list[StrategyDefinitionV1],
    consensus_map: Optional[dict[str, dict]] = None,
    market_window_map: Optional[dict[str, dict]] = None,
    cross_asset_map: Optional[dict[str, dict]] = None,
    derivative_map: Optional[dict[str, dict]] = None,
    regime_map: Optional[dict[str, dict]] = None,
    resume_from: Optional[str] = None,
) -> dict[str, Any]:
    """Run replay for a batch of events with resume support."""
    consensus_map = consensus_map or {}
    market_window_map = market_window_map or {}
    cross_asset_map = cross_asset_map or {}
    derivative_map = derivative_map or {}
    regime_map = regime_map or {}

    all_results, all_hypotheses, all_abstentions, all_kps = [], [], [], []
    processed, skipped = 0, 0
    resume_active = resume_from is None

    for event in events:
        eid = event.get("event_id", "")
        if not resume_active:
            if eid == resume_from:
                resume_active = True
            else:
                skipped += 1
                continue

        out = run_event_replay(
            event_record=event, consensus_record=consensus_map.get(eid),
            market_window=market_window_map.get(eid), cross_asset_state=cross_asset_map.get(eid),
            derivative_state=derivative_map.get(eid), strategy_definitions=strategies,
            regime_result=regime_map.get(eid))
        if "error" in out:
            continue
        all_results.extend(out.get("results", []))
        all_hypotheses.extend(out.get("hypotheses", []))
        all_abstentions.extend(out.get("abstentions", []))
        all_kps.extend(out.get("kernel_packages", []))
        processed += 1

    return {"results": all_results, "hypotheses": all_hypotheses, "abstentions": all_abstentions,
            "kernel_packages": all_kps, "processed_count": processed, "skipped_count": skipped}
