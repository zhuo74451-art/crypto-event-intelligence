"""F06: Registry and arbitration behavior.

Registry enforces ID+version uniqueness, validates fields,
links research claims, prevents unsupported production-ready labels.
Arbitration evaluates every candidate, preserves disagreements,
produces actionable_watch/monitor/abstain/insufficient_evidence.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from market_radar.cognition.strategy_components import (
    StrategySpec, RegisteredComponent, StrategyRegistry,
    ArbitrationResult, ArbitrationOutcome, StrategyStatus,
)
from market_radar.cognition.world_model import MarketWorldState, RegimeClassification


def register_strategies(registry: StrategyRegistry,
        specs: List[StrategySpec]) -> List[str]:
    errors = []
    for spec in specs:
        err = registry.register(spec)
        if err:
            errors.append(err)
    return errors


def update_registry_status(registry: StrategyRegistry,
        strategy_id: str, new_status: str) -> Optional[str]:
    if strategy_id not in registry.components:
        return f"not_found: {strategy_id}"
    valid_statuses = [s.value for s in StrategyStatus]
    if new_status not in valid_statuses:
        return f"invalid_status: {new_status}"
    if new_status == StrategyStatus.HISTORICAL_SUPPORTED.value:
        import datetime
        registry.components[strategy_id].status = new_status
        registry.components[strategy_id].updated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return None
    registry.components[strategy_id].status = new_status
    return None


def arbitrate(
    world_state: MarketWorldState,
    event_id: str,
    event_status: str,
    expectation_gap: Optional[float],
    market_confirmation_verdict: str,
    has_source_conflicts: bool,
    available_variables: Dict[str, Any],
    registry: Optional[StrategyRegistry] = None,
    candidate_specs: Optional[List[StrategySpec]] = None,
) -> ArbitrationResult:
    """Evaluate all candidates against world state and event state."""
    from market_radar.cognition.strategy_library import evaluate_strategy_eligibility
    result = ArbitrationResult(
        event_id=event_id,
        arbitration_id=_sha256_id(["arb", event_id]),
        as_of=world_state.as_of,
    )

    candidates = []
    if registry:
        candidates = [c.spec for c in registry.components.values()
                     if c.spec is not None]
    if candidate_specs:
        candidates.extend(candidate_specs)

    for spec in candidates:
        eligible, reason = evaluate_strategy_eligibility(spec, available_variables)
        if eligible:
            result.eligible_strategies.append(spec.strategy_id)
            # Check if event supports or contradicts this strategy
            if market_confirmation_verdict == "supports":
                result.support_reasons.setdefault(spec.strategy_id, []).append("market_confirms_direction")
            elif market_confirmation_verdict == "contradicts":
                result.contradiction_reasons.setdefault(spec.strategy_id, []).append("market_contradicts_hypothesis")
        else:
            result.rejected_strategies[spec.strategy_id] = reason
            result.missing_inputs.setdefault(spec.strategy_id, []).append(reason)

    # Determine outcome
    if not result.eligible_strategies:
        result.outcome = ArbitrationOutcome.INSUFFICIENT_EVIDENCE.value
        result.selected_observation_stance = ArbitrationOutcome.ABSTAIN.value
    elif has_source_conflicts:
        result.outcome = ArbitrationOutcome.MONITOR.value
        result.selected_observation_stance = "monitor_pending_resolution"
    elif result.eligible_strategies:
        result.outcome = ArbitrationOutcome.ACTIONABLE_WATCH.value
        result.selected_observation_stance = ArbitrationOutcome.ACTIONABLE_WATCH.value

    # Confidence decomposition
    n_eligible = len(result.eligible_strategies)
    n_rejected = len(result.rejected_strategies)
    total = n_eligible + n_rejected
    if total > 0:
        result.confidence_decomposition = {
            "eligibility_ratio": round(n_eligible / total, 2),
            "market_confirmation_weight": 0.3 if market_confirmation_verdict != "unavailable" else 0.0,
            "expectation_weight": 0.3 if expectation_gap is not None else 0.0,
        }
        result.overall_confidence = round(
            sum(result.confidence_decomposition.values()) / max(len(result.confidence_decomposition), 1), 2)

    return result


def _sha256_id(parts: List[str]) -> str:
    import hashlib
    return hashlib.sha256(":".join(parts).encode()).hexdigest()[:16]