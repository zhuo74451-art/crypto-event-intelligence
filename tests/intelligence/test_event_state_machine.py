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


class TestEventStateMachine:
    def test_legal_progression(self):
        sm = EventStateMachineV1()
        event = make_event()
        tx = sm.transition(event, EventState.PROPOSED, reason="Official proposal")
        assert event.current_state == EventState.PROPOSED
        assert tx.transition_type == TransitionType.PROGRESSION
        assert event.state_version == 2

    def test_illegal_jump_raises(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.RUMOR)
        with pytest.raises(IntelligenceError) as exc:
            sm.transition(event, EventState.COMPLETED)
        assert exc.value.code == ErrorCode.ILLEGAL_EVENT_TRANSITION

    def test_idempotent_transition(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.APPROVED)
        tx = sm.transition(event, EventState.APPROVED)
        assert event.current_state == EventState.APPROVED
        assert tx.from_state == EventState.APPROVED
        assert tx.to_state == EventState.APPROVED

    def test_revision_allowed_always(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.COMPLETED, family="regulatory")
        tx = sm.transition(event, EventState.APPROVED,
                           transition_type=TransitionType.REVISION,
                           reason="Correction: status was misreported")
        assert event.current_state == EventState.APPROVED
        assert tx.transition_type == TransitionType.REVISION

    def test_delay_transition(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.SCHEDULED)
        tx = sm.transition(event, EventState.DELAYED,
                           transition_type=TransitionType.DELAY)
        assert event.current_state == EventState.DELAYED

    def test_partial_reversal(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.EFFECTIVE)
        tx = sm.transition(event, EventState.PARTIALLY_REVERSED,
                           transition_type=TransitionType.PARTIAL_REVERSAL)
        assert event.current_state == EventState.PARTIALLY_REVERSED

    def test_full_reversal(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.EFFECTIVE)
        tx = sm.transition(event, EventState.REVERSED,
                           transition_type=TransitionType.REVERSAL)
        assert event.current_state == EventState.REVERSED

    def test_expiry(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.ANNOUNCED)
        tx = sm.transition(event, EventState.EXPIRED,
                           transition_type=TransitionType.EXPIRY)
        assert event.current_state == EventState.EXPIRED

    def test_unknown_to_rumor(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.UNKNOWN)
        tx = sm.transition(event, EventState.RUMOR)
        assert event.current_state == EventState.RUMOR

    def test_transition_history_append_only(self):
        sm = EventStateMachineV1()
        event = make_event()
        t1 = sm.transition(event, EventState.PROPOSED)
        t2 = sm.transition(event, EventState.ANNOUNCED)
        assert event.state_version == 3
        assert t1.to_state == EventState.PROPOSED
        assert t2.to_state == EventState.ANNOUNCED

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
        tx = sm.transition(event, EventState.APPROVED)
        assert event.current_state == EventState.APPROVED

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
        for s in states:
            sm.transition(event, s)
        assert event.current_state == EventState.COMPLETED
        assert event.state_version == len(states) + 1  # +1 for initial state

    def test_terminal_expired_no_outgoing(self):
        sm = EventStateMachineV1()
        event = make_event(state=EventState.EXPIRED)
        with pytest.raises(IntelligenceError):
            sm.transition(event, EventState.ANNOUNCED)
