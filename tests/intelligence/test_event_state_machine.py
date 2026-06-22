"""Tests for Event State Machine V1."""

import pytest

from market_radar.intelligence.contracts.event import (
    EventEntity, EventTransition, EventState, TransitionType,
    EventFamilyConfig,
)
from market_radar.intelligence.engines.event_state_machine import EventStateMachineV1
from market_radar.intelligence.errors.codes import IntelligenceError, ErrorCode


def make_event(eid="evt_001", state=EventState.RUMOR, family="generic"):
    return EventEntity(event_id=eid, event_family=family, current_state=state)


def apply(sm, event, to_state, **kwargs):
    """Helper: apply transition and return the updated event."""
    result = sm.transition(event, to_state, **kwargs)
    return result.updated_event, result


class TestEventStateMachine:
    def test_legal_progression(self):
        sm = EventStateMachineV1()
        event = make_event()
        result = sm.transition(event, EventState.PROPOSED, reason="Official proposal")
        updated = result.updated_event
        assert updated.current_state == EventState.PROPOSED
        assert result.transition.transition_type == TransitionType.PROGRESSION
        assert updated.state_version == 2
        # Input is not mutated
        assert event.current_state == EventState.RUMOR

    def test_illegal_jump_raises(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.RUMOR)
        with pytest.raises(IntelligenceError) as exc:
            sm.transition(event, EventState.COMPLETED)
        assert exc.value.code == ErrorCode.ILLEGAL_EVENT_TRANSITION

    def test_idempotent_transition(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.APPROVED)
        # First call creates the transition (not idempotent)
        result1 = sm.transition(event, EventState.APPROVED)
        ev1 = result1.updated_event
        assert ev1.current_state == EventState.APPROVED
        assert result1.transition.from_state == EventState.APPROVED
        assert result1.transition.to_state == EventState.APPROVED
        # Second call with same transition IS idempotent
        result2 = sm.transition(ev1, EventState.APPROVED)
        assert result2.idempotent is True

    def test_revision_allowed_always(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.COMPLETED, family="regulatory")
        result = sm.transition(event, EventState.COMPLETED,
                               transition_type=TransitionType.REVISION,
                               reason="Correction: status was misreported")
        updated = result.updated_event
        # Revision does NOT change state by default; to_state must equal current state
        assert updated.current_state == EventState.COMPLETED
        assert result.transition.transition_type == TransitionType.REVISION
        assert result.transition.to_state == EventState.COMPLETED

    def test_delay_transition(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.SCHEDULED)
        result = sm.transition(event, EventState.DELAYED,
                               transition_type=TransitionType.DELAY)
        updated = result.updated_event
        assert updated.current_state == EventState.DELAYED
        assert result.transition.transition_type == TransitionType.DELAY

    def test_partial_reversal(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.APPROVED)
        result = sm.transition(event, EventState.UNDER_REVIEW,
                               transition_type=TransitionType.PARTIAL_REVERSAL)
        updated = result.updated_event
        assert updated.current_state == EventState.UNDER_REVIEW
        assert result.transition.transition_type == TransitionType.PARTIAL_REVERSAL

    def test_full_reversal(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.EFFECTIVE)
        result = sm.transition(event, EventState.REVERSED,
                               transition_type=TransitionType.REVERSAL)
        updated = result.updated_event
        assert updated.current_state == EventState.REVERSED
        assert result.transition.transition_type == TransitionType.REVERSAL

    def test_expiry(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.ANNOUNCED)
        result = sm.transition(event, EventState.EXPIRED,
                               transition_type=TransitionType.EXPIRY)
        updated = result.updated_event
        assert updated.current_state == EventState.EXPIRED
        assert result.transition.transition_type == TransitionType.EXPIRY

    def test_unknown_to_rumor(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.UNKNOWN)
        result = sm.transition(event, EventState.RUMOR)
        updated = result.updated_event
        assert updated.current_state == EventState.RUMOR
        assert result.transition.to_state == EventState.RUMOR

    def test_transition_history_append_only(self):
        sm = EventStateMachineV1()
        event = make_event()
        r1 = sm.transition(event, EventState.PROPOSED)
        ev1 = r1.updated_event
        r2 = sm.transition(ev1, EventState.ANNOUNCED)
        ev2 = r2.updated_event
        assert ev2.state_version == 3
        assert r1.transition.to_state == EventState.PROPOSED
        assert r2.transition.to_state == EventState.ANNOUNCED
        # Original input not mutated
        assert event.state_version == 1

    def test_as_of_reconstruction(self):
        sm = EventStateMachineV1()
        txs = [
            EventTransition(
                transition_id="t1", event_id="evt_001",
                from_state=EventState.RUMOR, to_state=EventState.PROPOSED,
                transition_type=TransitionType.PROGRESSION,
                first_seen_at="2024-01-01T00:00:00Z",
            ),
            EventTransition(
                transition_id="t2", event_id="evt_001",
                from_state=EventState.PROPOSED, to_state=EventState.APPROVED,
                transition_type=TransitionType.PROGRESSION,
                first_seen_at="2024-06-01T00:00:00Z",
            ),
        ]
        state = sm.reconstruct_as_of(txs, "2024-03-01T00:00:00Z")
        assert state == EventState.PROPOSED

    def test_as_of_before_any_transition(self):
        sm = EventStateMachineV1()
        state = sm.reconstruct_as_of([], "2024-01-01T00:00:00Z")
        assert state == EventState.UNKNOWN

    def test_revision_does_not_affect_as_of(self):
        sm = EventStateMachineV1()
        txs = [
            EventTransition(
                transition_id="t1", event_id="evt_001",
                from_state=EventState.RUMOR, to_state=EventState.PROPOSED,
                transition_type=TransitionType.PROGRESSION,
                first_seen_at="2024-01-01T00:00:00Z",
            ),
            EventTransition(
                transition_id="t2", event_id="evt_001",
                from_state=EventState.PROPOSED, to_state=EventState.ANNOUNCED,
                transition_type=TransitionType.REVISION,  # Revision, not progression
                first_seen_at="2024-06-01T00:00:00Z",
            ),
        ]
        # After revision, as_of at a later time should still show PROPOSED
        # because revisions don't affect historical state reconstruction
        state = sm.reconstruct_as_of(txs, "2024-06-15T00:00:00Z")
        assert state == EventState.PROPOSED  # Revision not applied

    def test_custom_family_registration(self):
        sm = EventStateMachineV1()
        config = EventFamilyConfig(
            family="custom",
            allowed_transitions={"proposed": ["approved"]},
        )
        sm.register_family(config)
        event = make_event(state=EventState.PROPOSED, family="custom")
        result = sm.transition(event, EventState.APPROVED)
        updated = result.updated_event
        assert updated.current_state == EventState.APPROVED
        assert result.transition.to_state == EventState.APPROVED

    def test_custom_family_rejects_unknown(self):
        sm = EventStateMachineV1()
        config = EventFamilyConfig(
            family="custom",
            allowed_transitions={"proposed": ["approved"]},
        )
        sm.register_family(config)
        event = make_event(state=EventState.PROPOSED, family="custom")
        with pytest.raises(IntelligenceError):
            sm.transition(event, EventState.RUMOR)

    def test_forward_progression_multiple_steps(self):
        sm = EventStateMachineV1()
        event = make_event()
        states = [
            EventState.PROPOSED, EventState.ANNOUNCED,
            EventState.SCHEDULED, EventState.UNDER_REVIEW,
            EventState.APPROVED, EventState.SIGNED,
            EventState.EFFECTIVE, EventState.EXECUTING,
            EventState.COMPLETED,
        ]
        ev = event
        for s in states:
            result = sm.transition(ev, s)
            ev = result.updated_event
        assert ev.current_state == EventState.COMPLETED
        assert ev.state_version == len(states) + 1  # +1 for initial state
        # Original input not mutated
        assert event.current_state == EventState.RUMOR

    def test_terminal_expired_no_outgoing(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.EXPIRED)
        with pytest.raises(IntelligenceError):
            sm.transition(event, EventState.ANNOUNCED)
