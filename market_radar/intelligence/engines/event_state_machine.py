"""Event State Machine V1 — deterministic event state transitions."""

from __future__ import annotations

from typing import Optional

from ..contracts.event import (
    EventState, EventEntity, EventTransition, TransitionType,
    EventFamilyConfig, EventStateMachineRules,
)
from ..errors.codes import IntelligenceError, ErrorCode


class EventStateMachineV1:
    """Deterministic event state machine.

    Supports:
    - Default state transition rules
    - Custom family-specific rules
    - Transition validation
    - Idempotent duplicate transitions
    - Append-only transition history
    - As-of state reconstruction
    - Separation of revision from real transitions
    """

    def __init__(self):
        self.default_rules = EventStateMachineRules()
        self.family_configs: dict[str, EventFamilyConfig] = {}

    def register_family(self, config: EventFamilyConfig) -> None:
        """Register custom state machine rules for an event family."""
        self.family_configs[config.family] = config

    def is_allowed(self, event: EventEntity, to_state: EventState,
                   transition_type: TransitionType = TransitionType.PROGRESSION) -> bool:
        """Check if a transition is legal for this event."""
        from_state = event.current_state

        # Revisions and corrections are always allowed
        if transition_type in (TransitionType.REVISION, TransitionType.CORRECTION):
            return True

        # Reversal transitions
        if transition_type in (TransitionType.REVERSAL, TransitionType.PARTIAL_REVERSAL):
            return True

        # Expiry
        if transition_type == TransitionType.EXPIRY and to_state == EventState.EXPIRED:
            return True

        # Idempotent
        if from_state == to_state:
            return True

        # Check family-specific rules first
        family = event.event_family
        if family in self.family_configs:
            config = self.family_configs[family]
            return config.is_allowed(from_state, to_state)

        # Use default rules
        rules = self.default_rules.defaults
        from_val = from_state.value
        if from_val not in rules:
            return False
        return to_state.value in rules[from_val]

    def transition(self, event: EventEntity, to_state: EventState,
                   transition_type: TransitionType = TransitionType.PROGRESSION,
                   reason: str = "", evidence_refs: Optional[list[str]] = None,
                   transition_time: Optional[str] = None,
                   first_seen_at: Optional[str] = None) -> EventTransition:
        """Execute a state transition and return the transition record.

        Args:
            event: The event entity to transition.
            to_state: Target state.
            transition_type: Type of transition.
            reason: Human-readable reason.
            evidence_refs: References to supporting evidence.
            transition_time: When the transition occurred.
            first_seen_at: When the transition was first observed.

        Returns:
            The EventTransition record (appended to event's history implicitly
            via caller).
        """
        if not self.is_allowed(event, to_state, transition_type):
            from_state = event.current_state
            raise IntelligenceError(
                ErrorCode.ILLEGAL_EVENT_TRANSITION,
                f"Cannot transition from {from_state.value} to {to_state.value} "
                f"via {transition_type.value}",
            )

        from_state = event.current_state
        transition = EventTransition(
            transition_id=f"trn_{event.event_id}_{event.state_version + 1}",
            event_id=event.event_id,
            from_state=from_state,
            to_state=to_state,
            transition_type=transition_type,
            transition_time=transition_time or event.as_of_time or "",
            first_seen_at=first_seen_at or transition_time or event.as_of_time or "",
            evidence_refs=evidence_refs or [],
            reason=reason,
        )

        # Update event state
        event.previous_state = from_state
        event.current_state = to_state
        event.state_version += 1

        return transition

    def reconstruct_as_of(self, transitions: list[EventTransition],
                          as_of_time: str) -> EventState:
        """Reconstruct the event state at a given time.

        Revisions do NOT overwrite past known states — only the first
        transition observed for a given time period is authoritative.
        """
        filtered = [t for t in transitions if t.first_seen_at <= as_of_time]
        if not filtered:
            return EventState.UNKNOWN

        # Sort by first_seen_at
        sorted_tx = sorted(filtered, key=lambda t: t.first_seen_at)

        # Walk through transitions in order
        state = EventState.UNKNOWN
        for tx in sorted_tx:
            # Only apply progression-type transitions for historical state
            if tx.transition_type in (
                TransitionType.PROGRESSION,
                TransitionType.DELAY,
                TransitionType.PARTIAL_REVERSAL,
                TransitionType.REVERSAL,
                TransitionType.EXPIRY,
            ):
                state = tx.to_state
            # Revisions are not applied — they don't change historical state
        return state
