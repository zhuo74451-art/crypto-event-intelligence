"""Strategy Lifecycle Engine V1 — deterministic strategy instance lifecycle."""

from __future__ import annotations

from typing import Optional

from ..contracts.strategy import (
    StrategyPack, StrategyInstance, StrategyInstanceState,
    InstanceTransition,
)
from ..errors.codes import IntelligenceError, ErrorCode


class StrategyLifecycleEngineV1:
    """Deterministic strategy instance lifecycle engine.

    States: inactive -> watching -> triggered -> awaiting_confirmation
            -> confirmed | weakened | invalidated | expired

    Rules:
    - Each state change has a reason and evidence refs
    - Context must be met before Confirmed
    - Missing confirmation -> Awaiting Confirmation
    - Invalidation conditions -> immediate Invalidated
    - Time window exceeded -> Expired
    - New evidence can move Confirmed -> Weakened
    - Invalidated cannot auto-recover; requires new instance
    """

    VALID_TRANSITIONS: dict[StrategyInstanceState, list[StrategyInstanceState]] = {
        StrategyInstanceState.INACTIVE: [
            StrategyInstanceState.WATCHING,
        ],
        StrategyInstanceState.WATCHING: [
            StrategyInstanceState.TRIGGERED,
            StrategyInstanceState.INACTIVE,
            StrategyInstanceState.INVALIDATED,
            StrategyInstanceState.EXPIRED,
        ],
        StrategyInstanceState.TRIGGERED: [
            StrategyInstanceState.AWAITING_CONFIRMATION,
            StrategyInstanceState.CONFIRMED,
            StrategyInstanceState.INVALIDATED,
            StrategyInstanceState.WATCHING,
            StrategyInstanceState.EXPIRED,
        ],
        StrategyInstanceState.AWAITING_CONFIRMATION: [
            StrategyInstanceState.CONFIRMED,
            StrategyInstanceState.WEAKENED,
            StrategyInstanceState.INVALIDATED,
            StrategyInstanceState.EXPIRED,
        ],
        StrategyInstanceState.CONFIRMED: [
            StrategyInstanceState.WEAKENED,
            StrategyInstanceState.INVALIDATED,
            StrategyInstanceState.EXPIRED,
        ],
        StrategyInstanceState.WEAKENED: [
            StrategyInstanceState.CONFIRMED,
            StrategyInstanceState.INVALIDATED,
            StrategyInstanceState.EXPIRED,
        ],
        StrategyInstanceState.INVALIDATED: [],
        StrategyInstanceState.EXPIRED: [],
    }

    def is_allowed(self, instance: StrategyInstance,
                   to_state: StrategyInstanceState) -> bool:
        if to_state == instance.state:
            return True
        allowed = self.VALID_TRANSITIONS.get(instance.state, [])
        return to_state in allowed

    def transition(self, instance: StrategyInstance,
                   to_state: StrategyInstanceState,
                   reason: str = "",
                   evidence_refs: Optional[list[str]] = None,
                   transition_time: Optional[str] = None) -> InstanceTransition:
        """Execute a state transition for a strategy instance.

        Returns the transition record. Raises if transition is illegal.
        """
        if not self.is_allowed(instance, to_state):
            raise IntelligenceError(
                ErrorCode.INVALID_STRATEGY_TRANSITION,
                f"Cannot transition from {instance.state.value} to {to_state.value}",
            )

        if to_state == StrategyInstanceState.INVALIDATED and instance.state == StrategyInstanceState.INVALIDATED:
            # Already invalidated
            raise IntelligenceError(
                ErrorCode.INVALID_STRATEGY_TRANSITION,
                "Invalidated instances cannot transition (terminal state)",
            )

        tx = InstanceTransition(
            from_state=instance.state,
            to_state=to_state,
            transition_time=transition_time or instance.as_of_time or "",
            reason=reason,
            evidence_refs=evidence_refs or [],
        )

        instance.state = to_state
        instance.transitions.append(tx)

        return tx

    def evaluate(self, instance: StrategyInstance,
                 context_met: bool = False,
                 trigger_met: bool = False,
                 confirmation_met: bool = False,
                 invalidation_triggered: bool = False,
                 expired: bool = False,
                 weakening_evidence: bool = False,
                 transition_time: Optional[str] = None) -> Optional[InstanceTransition]:
        """Evaluate the instance and transition automatically.

        This is a convenience method that checks conditions and
        transitions the instance deterministically.
        """
        # Terminal states — no further evaluation
        if instance.state in (StrategyInstanceState.INVALIDATED,
                              StrategyInstanceState.EXPIRED):
            return None

        # Invalidation takes priority
        if invalidation_triggered:
            return self.transition(
                instance, StrategyInstanceState.INVALIDATED,
                reason="Invalidation conditions triggered",
                transition_time=transition_time,
            )

        # Expiry check
        if expired:
            return self.transition(
                instance, StrategyInstanceState.EXPIRED,
                reason="Time window expired",
                transition_time=transition_time,
            )

        state = instance.state

        # INACTIVE -> WATCHING (if context met)
        if state == StrategyInstanceState.INACTIVE and context_met:
            return self.transition(
                instance, StrategyInstanceState.WATCHING,
                reason="Context conditions met, starting to watch",
                transition_time=transition_time,
            )

        # WATCHING -> TRIGGERED
        if state == StrategyInstanceState.WATCHING and trigger_met:
            return self.transition(
                instance, StrategyInstanceState.TRIGGERED,
                reason="Trigger conditions met",
                transition_time=transition_time,
            )

        # TRIGGERED -> AWAITING_CONFIRMATION | CONFIRMED
        if state == StrategyInstanceState.TRIGGERED:
            if confirmation_met:
                return self.transition(
                    instance, StrategyInstanceState.CONFIRMED,
                    reason="Confirmation conditions satisfied",
                    transition_time=transition_time,
                )
            return self.transition(
                instance, StrategyInstanceState.AWAITING_CONFIRMATION,
                reason="Triggered but awaiting confirmation",
                transition_time=transition_time,
            )

        # AWAITING_CONFIRMATION -> CONFIRMED | WEAKENED
        if state == StrategyInstanceState.AWAITING_CONFIRMATION:
            if confirmation_met:
                return self.transition(
                    instance, StrategyInstanceState.CONFIRMED,
                    reason="Confirmation received",
                    transition_time=transition_time,
                )
            if weakening_evidence:
                return self.transition(
                    instance, StrategyInstanceState.WEAKENED,
                    reason="Contradicting evidence while awaiting confirmation",
                    transition_time=transition_time,
                )

        # CONFIRMED -> WEAKENED
        if state == StrategyInstanceState.CONFIRMED and weakening_evidence:
            return self.transition(
                instance, StrategyInstanceState.WEAKENED,
                reason="New evidence weakens the confirmed hypothesis",
                transition_time=transition_time,
            )

        return None
