"""Event State Machine V1 — deterministic event state transitions.

Key fixes over original:
- Revision/Correction do NOT change state by default
- State correction requires special authorization
- Idempotent duplicate detection
- Pure function: does NOT mutate input EventEntity
- All time comparisons use aware UTC datetimes
- Append-only history for as-of reconstruction
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..contracts.event import (
    EventState, EventEntity, EventTransition, TransitionType,
    EventFamilyConfig, EventStateMachineRules,
)
from ..contracts.common import utc_parse
from ..errors.codes import IntelligenceError, ErrorCode


@dataclass
class EventTransitionResult:
    """Result of applying a transition to an event."""
    updated_event: EventEntity
    transition: EventTransition
    idempotent: bool = False
    validation_trace: list[str] = field(default_factory=list)


class EventStateMachineV1:
    """Deterministic event state machine.

    Pure function semantics: transition() returns a NEW EventEntity
    with the transition applied, leaving the input unchanged.

    Supports:
    - Default state transition rules
    - Custom family-specific rules (override defaults)
    - Transition validation
    - Idempotent duplicate detection
    - Revision/Correction (non-state-changing)
    - State Correction (with special authorization)
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

        # Revisions and corrections never change state by default
        if transition_type in (TransitionType.REVISION, TransitionType.CORRECTION):
            return to_state == from_state

        # State correction: only allowed for authorized state changes
        if transition_type == TransitionType.STATE_CORRECTION:
            # Must be a different state, must have evidence
            return to_state != from_state

        # Reversal transitions: validate
        if transition_type in (TransitionType.REVERSAL, TransitionType.PARTIAL_REVERSAL):
            return self._is_valid_reversal(from_state, to_state, transition_type, event)

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

    def _is_valid_reversal(self, from_state: EventState, to_state: EventState,
                            transition_type: TransitionType,
                            event: EventEntity) -> bool:
        """Check if a reversal is valid for this event."""
        # REVERSAL: can go to reversed state
        if transition_type == TransitionType.REVERSAL:
            return to_state == EventState.REVERSED

        # PARTIAL_REVERSAL: can go to a subset of valid states
        valid_partial = {
            EventState.APPROVED: [EventState.UNDER_REVIEW],
            EventState.SIGNED: [EventState.APPROVED, EventState.UNDER_REVIEW],
            EventState.EFFECTIVE: [EventState.SIGNED, EventState.APPROVED],
            EventState.EXECUTING: [EventState.EFFECTIVE, EventState.APPROVED],
            EventState.COMPLETED: [EventState.EXECUTING, EventState.EFFECTIVE],
        }
        allowed_from = valid_partial.get(from_state, [])
        return to_state in allowed_from

    def transition(self, event: EventEntity, to_state: EventState,
                   transition_type: TransitionType = TransitionType.PROGRESSION,
                   reason: str = "",
                   evidence_refs: Optional[list[str]] = None,
                   transition_time: Optional[str] = None,
                   first_seen_at: Optional[str] = None,
                   force_state_change: bool = False) -> EventTransitionResult:
        """Apply a state transition and return the result.

        This is a PURE FUNCTION: the input event is NOT modified.
        Returns EventTransitionResult with a NEW event and the transition record.

        Args:
            event: The event entity to transition (not modified).
            to_state: Target state.
            transition_type: Type of transition.
            reason: Human-readable reason.
            evidence_refs: References to supporting evidence.
            transition_time: When the transition occurred (UTC ISO).
            first_seen_at: When the transition was first observed (UTC ISO).
            force_state_change: For STATE_CORRECTION type, allows state change.

        Returns:
            EventTransitionResult with new event, transition, and trace.
        """
        trace: list[str] = []
        from_state = event.current_state

        # Idempotency check: same event, same transition
        if (from_state == to_state and
                transition_type not in (TransitionType.REVISION, TransitionType.CORRECTION)):
            # Check if this exact transition already exists in event history
            for t in event.transitions:
                if (t.from_state == from_state and t.to_state == to_state and
                        t.transition_type == transition_type):
                    return EventTransitionResult(
                        updated_event=event,
                        transition=t,
                        idempotent=True,
                        validation_trace=trace + ["IDEMPOTENT: exact transition exists"],
                    )

        # Validate transition
        if not self.is_allowed(event, to_state, transition_type):
            trace.append(f"BLOCKED: {from_state.value} -> {to_state.value} via {transition_type.value}")
            raise IntelligenceError(
                ErrorCode.ILLEGAL_EVENT_TRANSITION,
                f"Cannot transition from {from_state.value} to {to_state.value} "
                f"via {transition_type.value}",
            )

        # Revision/Correction: do not change state by default
        actual_to_state = to_state
        if (transition_type in (TransitionType.REVISION, TransitionType.CORRECTION)
                and not force_state_change):
            actual_to_state = from_state
            trace.append(f"{transition_type.value}: state unchanged (stays {from_state.value})")

        # State correction requires authorization
        if transition_type == TransitionType.STATE_CORRECTION:
            if not force_state_change:
                trace.append("BLOCKED: state_correction requires force_state_change=True")
                raise IntelligenceError(
                    ErrorCode.ILLEGAL_EVENT_TRANSITION,
                    "state_correction requires force_state_change=True",
                )

        # Use aware UTC times
        if transition_time:
            try:
                utc_parse(transition_time)
            except (ValueError, TypeError):
                raise IntelligenceError(
                    ErrorCode.ILLEGAL_EVENT_TRANSITION,
                    f"Invalid transition_time: {transition_time}",
                )
        if first_seen_at:
            try:
                utc_parse(first_seen_at)
            except (ValueError, TypeError):
                raise IntelligenceError(
                    ErrorCode.ILLEGAL_EVENT_TRANSITION,
                    f"Invalid first_seen_at: {first_seen_at}",
                )

        # Create transition record
        transition = EventTransition(
            transition_id=f"trn_{event.event_id}_{event.state_version + 1}",
            event_id=event.event_id,
            from_state=from_state,
            to_state=actual_to_state,
            transition_type=transition_type,
            transition_time=transition_time or event.as_of_time or "",
            first_seen_at=first_seen_at or transition_time or event.as_of_time or "",
            evidence_refs=evidence_refs or [],
            reason=reason,
        )

        trace.append(f"PROCEED: {from_state.value} -> {actual_to_state.value} via {transition_type.value}")

        # Create NEW event (don't mutate input)
        updated = EventEntity(
            event_id=event.event_id,
            event_family=event.event_family,
            title=event.title,
            entities=list(event.entities),
            assets=list(event.assets),
            current_state=actual_to_state,
            previous_state=from_state if actual_to_state != from_state else event.previous_state,
            state_version=event.state_version + 1 if actual_to_state != from_state else event.state_version,
            parent_event_id=event.parent_event_id,
            revision_of=event.revision_of,
            reversal_of=event.reversal_of,
            evidence_bundle_id=event.evidence_bundle_id,
            effective_scope=dict(event.effective_scope),
            transitions=list(event.transitions) + [transition],
        )

        return EventTransitionResult(
            updated_event=updated,
            transition=transition,
            idempotent=False,
            validation_trace=trace,
        )

    def reconstruct_as_of(self, transitions: list[EventTransition],
                          as_of_time: str) -> EventState:
        """Reconstruct the event state at a given point in time.

        Uses aware datetime comparison. Only transitions with
        first_seen_at <= as_of_time are included.

        Revisions/Corrections do NOT change state (historical integrity).
        """
        try:
            as_of_dt = utc_parse(as_of_time)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid as_of_time: {as_of_time}")

        filtered = []
        for t in transitions:
            try:
                ts_dt = utc_parse(t.first_seen_at)
                if ts_dt <= as_of_dt:
                    filtered.append(t)
            except (ValueError, TypeError):
                continue

        if not filtered:
            return EventState.UNKNOWN

        # Sort by first_seen_at
        sorted_tx = sorted(filtered, key=lambda t: utc_parse(t.first_seen_at))

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
                TransitionType.STATE_CORRECTION,
            ):
                state = tx.to_state
            # Revisions/corrections do not change historical state
        return state
