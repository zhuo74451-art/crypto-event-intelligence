"""Integrated program runner -- connects every stage into one path.

Pipeline: input adapters -> blocking validation -> cognition spine -> world model ->
regime/priced-in classifiers -> 8 strategy evaluators -> arbitration ->
Market Decision Packet -> historical baselines -> complete shadow outputs.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from market_radar.cognition.orchestrator import run_cognition, CognitionRunResult
from market_radar.cognition.world_builder import (
    build_world_state, build_regime_classification, classify_priced_in,
)
from market_radar.cognition.strategy_library import get_all_strategy_specs
from market_radar.cognition.strategy_evaluators import evaluate_all as evaluate_all_strategies
from market_radar.cognition.strategy_components import (
    StrategyRegistry, MarketDecisionPacket,
)
from market_radar.cognition.arbitration_engine import register_strategies, arbitrate_with_evaluations
from market_radar.cognition.decision_pipeline import build_decision_packet
from market_radar.cognition.shadow_runner import build_evaluation_report
from market_radar.cognition.contracts import utc_now
from market_radar.cognition.intake_contracts import MarketStateInput


@dataclass
class IntegratedResult:
    run_id: str = ""
    status: str = "ok"
    cognition: Any = None
    world_state: Any = None
    regime: Any = None
    registry: Any = None
    arbitration_results: list = field(default_factory=list)
    decision_packets: list = field(default_factory=list)
    evaluation_report: dict = field(default_factory=dict)
    output_dir: str = ""
    errors: list = field(default_factory=list)


def run_program(input_path, output_root, run_id, mode="replay",
                as_of=None, strict=False, assets=None):
    result = IntegratedResult(run_id=run_id, output_dir=str(output_root))
    output_root.mkdir(parents=True, exist_ok=True)
    errors = []

    # Stage 1: Cognition spine
    cog = run_cognition(input_path, output_root, run_id,
                        mode=mode, as_of=as_of, strict=strict, assets=assets)
    result.cognition = cog
    if cog.status == "failed":
        result.status = "failed"
        result.errors = cog.errors
        return result

    # Stage 2: World model
    market_inputs = []
    for snap in cog.snapshots:
        mi = MarketStateInput(asset=snap.asset, as_of=snap.as_of,
                              price=snap.price, volume_24h=snap.volume_24h)
        market_inputs.append(mi)

    ws = build_world_state(as_of=as_of or utc_now(),
                           market_inputs=market_inputs,
                           event_assets=assets or ["BTC", "ETH"])
    result.world_state = ws

    # Stage 3: Regime classifiers
    btc_data = next((mi for mi in market_inputs if mi.asset == "BTC"), None)
    regime = build_regime_classification(
        as_of=as_of or utc_now(),
        btc_return_24h=btc_data.return_24h if btc_data else None,
        funding_rate=btc_data.funding_rate if btc_data else None,
        btc_price=btc_data.price if btc_data else None,
        volume_24h=btc_data.volume_24h if btc_data else None,
    )
    result.regime = regime

    # Stage 4: Strategy registration
    registry = StrategyRegistry()
    reg_errors = register_strategies(registry, get_all_strategy_specs())
    errors.extend(reg_errors)
    result.registry = registry

    # Stage 5: Arbitration + Decision Packets per event
    for ev in cog.events:
        exp = next((e for e in cog.expectations if e.event_id == ev.event_id), None)
        confs = [c for c in cog.confirmations if c.event_id == ev.event_id]
        verdicts = [c.verdict for c in confs]
        market_verdict = ("supports" if "supports" in verdicts else
                          "contradicts" if "contradicts" in verdicts else "unavailable")
        has_conflicts = any(cf.event_id == ev.event_id for cf in cog.conflicts)
        gap = exp.signed_surprise if exp else None

        available_vars = {
            "signed_surprise": gap,
            "price_return": next((c.measured_value for c in confs
                                  if c.dimension == "price_direction"), None),
            "volume_24h": next((s.volume_24h for s in cog.snapshots
                                if s.event_id == ev.event_id), None),
            "funding_rate": btc_data.funding_rate if btc_data else None,
            "open_interest": btc_data.open_interest if btc_data else None,
            "btc_return_24h": btc_data.return_24h if btc_data else None,
            "eth_return_24h": None,
            "exchange_netflow": None,
            "stablecoin_liquidity": None,
            "unlock_amount": None,
            "circulating_supply": None,
            "incident_severity": None,
            "affected_tvl": None,
        }

        # Execute all 8 strategy evaluators as code
        strategy_evals = evaluate_all_strategies(available_vars)

        # Determine priced-in state
        pi_label = "indeterminate"
        snap = next((s for s in cog.snapshots if s.event_id == ev.event_id), None)
        if snap and snap.pre_event_ref and snap.price and snap.pre_event_ref != 0:
            pre_event_movement = ((snap.price - snap.pre_event_ref)
                                  / snap.pre_event_ref) * 100.0
            pi_label, _ = classify_priced_in(pre_event_movement, gap)

        # Arbitration consumes strategy evaluation records
        arb = arbitrate_with_evaluations(
            evaluations=strategy_evals,
            world_state=ws,
            event_id=ev.event_id,
            regime_label=regime.risk_label if regime else "",
            priced_in_label=pi_label,
            has_source_conflicts=has_conflicts,
        )
        result.arbitration_results.append(arb)

        pkt = build_decision_packet(ev, ws, regime, arb, gap, market_verdict,
                                    pi_label, [])
        result.decision_packets.append(pkt)

    # Stage 6: Write decision packets
    with open(str(output_root / "decision_packets.jsonl"), "w") as f:
        for pkt in result.decision_packets:
            f.write(json.dumps(pkt.to_dict()) + chr(10))

    # Stage 7: Evaluation report
    eval_report = build_evaluation_report(cog.events, cog.assessments,
                                          cog.abstentions, as_of=as_of)
    result.evaluation_report = eval_report
    with open(str(output_root / "evaluation_report.json"), "w") as f:
        json.dump(eval_report, f, indent=2)

    # Stage 8: Write world state + regime
    with open(str(output_root / "world_state.json"), "w") as f:
        json.dump(ws.to_dict(), f, indent=2, default=str)
    with open(str(output_root / "regime_classification.json"), "w") as f:
        json.dump(regime.to_dict(), f, indent=2, default=str)

    # Stage 9: Strategy registry output
    with open(str(output_root / "strategy_registry.json"), "w") as f:
        json.dump({
            "components": {
                sid: {"strategy_id": c.spec.strategy_id if c.spec else "",
                      "name": c.spec.name if c.spec else "",
                      "status": c.status,
                      "thesis": c.spec.thesis if c.spec else ""}
                for sid, c in registry.components.items()
            }
        }, f, indent=2)

    result.errors = errors
    if errors:
        result.status = "degraded"
    return result
