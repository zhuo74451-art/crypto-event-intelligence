"""F07: Market Decision Packet builder for the real pipeline."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from market_radar.cognition.strategy_components import MarketDecisionPacket, ArbitrationResult, ArbitrationOutcome
from market_radar.cognition.world_model import MarketWorldState, RegimeClassification
from market_radar.cognition.contracts import EventState, EventStatus


def build_decision_packet(
    event: EventState,
    world_state: MarketWorldState,
    regime: Optional[RegimeClassification],
    arbitration: ArbitrationResult,
    expectation_gap: Optional[float] = None,
    confirmation_verdict: str = "unavailable",
    priced_in_label: str = "indeterminate",
    transmission_paths: Optional[List[str]] = None,
) -> MarketDecisionPacket:
    import datetime
    pkt = MarketDecisionPacket(
        packet_id=_sha256_id(["pkt", event.event_id]),
        event_id=event.event_id,
        as_of=world_state.as_of,
        event_title=event.title,
        event_status=event.status,
        evidence_status="fixture_replay_only" if event.status == EventStatus.CANDIDATE.value else "active",
        world_model_summary=f"{len(world_state.available_domains())} of 11 domains available",
        available_domains=world_state.available_domains(),
        unavailable_domains=world_state.unavailable_domains,
        expectation_baseline="consensus" if expectation_gap is not None else "unavailable",
        expectation_gap=expectation_gap,
        affected_assets=event.affected_assets,
        transmission_paths=transmission_paths or [],
        confirmation_verdict=confirmation_verdict,
        priced_in_state=priced_in_label,
        eligible_strategies=arbitration.eligible_strategies,
        arbitration_outcome=arbitration.outcome,
        observation_stance=arbitration.selected_observation_stance or arbitration.outcome,
        confidence_components=arbitration.confidence_decomposition,
        overall_confidence=arbitration.overall_confidence,
        not_trading_instruction=True,
    )
    if arbitration.outcome == ArbitrationOutcome.ABSTAIN.value:
        pkt.observation_stance = ArbitrationOutcome.ABSTAIN.value
    return pkt


def _sha256_id(parts: List[str]) -> str:
    import hashlib
    return hashlib.sha256(":".join(parts).encode()).hexdigest()[:16]