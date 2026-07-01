"""Cognition v2 lifecycle service tests."""

from datetime import datetime, timezone
import pytest

from market_radar.cognition_v2.domain.contracts import (
    ThesisState,
    CANONICAL_STATES,
    CANONICAL_EDGES,
    LifecycleTransitionRequest,
)
from market_radar.cognition_v2.lifecycle.service import (
    LifecycleValidator,
    LifecycleService,
)


NOW = datetime.now(timezone.utc)

ALL_STATES = list(CANONICAL_STATES)
LEGAL_EDGES = CANONICAL_EDGES

# Collect all legal transitions
LEGAL_TRANSITIONS = [(f, t) for f, targets in LEGAL_EDGES.items() for t in targets]

# Representative illegal jumps
ILLEGAL_JUMPS = [
    (ThesisState.DISCOVERED, ThesisState.ACTIVE),
    (ThesisState.DISCOVERED, ThesisState.ARCHIVED),
    (ThesisState.DISCOVERED, ThesisState.DORMANT),
    (ThesisState.ARCHIVED, ThesisState.DISCOVERED),
    (ThesisState.REJECTED, ThesisState.ACTIVE),
    (ThesisState.ISOLATED, ThesisState.ACTIVE),
    (ThesisState.DORMANT, ThesisState.QUALIFYING),
    (ThesisState.INVALIDATED, ThesisState.ACTIVE),
    (ThesisState.EXPIRED, ThesisState.CANDIDATE),
]


@pytest.fixture
def validator():
    return LifecycleValidator()


@pytest.fixture
def service():
    return LifecycleService()


class TestLifecycleValidator:
    def test_all_legal_transitions(self, validator):
        for from_state, to_state in LEGAL_TRANSITIONS:
            assert validator.validate(from_state, to_state), (
                f"{from_state.value} -> {to_state.value} should be legal"
            )

    def test_representative_illegal_jumps(self, validator):
        jumps = [
            (ThesisState.DISCOVERED, ThesisState.ACTIVE),
            (ThesisState.DISCOVERED, ThesisState.ARCHIVED),
            (ThesisState.ARCHIVED, ThesisState.DISCOVERED),
            (ThesisState.REJECTED, ThesisState.ACTIVE),
            (ThesisState.ISOLATED, ThesisState.ACTIVE),
            (ThesisState.DORMANT, ThesisState.QUALIFYING),
            (ThesisState.INVALIDATED, ThesisState.ACTIVE),
        ]
        for from_state, to_state in jumps:
            assert not validator.validate(from_state, to_state), (
                f"{from_state.value} -> {to_state.value} should be illegal"
            )
            with pytest.raises(ValueError, match="Illegal transition"):
                validator.validate_or_raise(from_state, to_state)

    def test_self_loop_only_active(self, validator):
        assert validator.validate(ThesisState.ACTIVE, ThesisState.ACTIVE)
        for state in ALL_STATES:
            if state != ThesisState.ACTIVE:
                assert not validator.validate(state, state), (
                    f"{state.value} -> {state.value} should be illegal"
                )

    def test_get_legal_transitions(self, validator):
        for state in ALL_STATES:
            trans = validator.get_legal_transitions(state)
            assert isinstance(trans, list)
            assert len(trans) > 0

    def test_archived_only_reopen(self, validator):
        trans = validator.get_legal_transitions(ThesisState.ARCHIVED)
        assert ThesisState.REOPEN_REVIEW in trans
        assert len(trans) == 1

    def test_unknown_state_returns_false(self, validator):
        assert validator.validate(99, ThesisState.ACTIVE) is False  # type: ignore

    def test_code_size_positive(self, validator):
        assert validator.code_size > 0


class TestLifecycleService:
    def test_legal_transition_validates(self, service):
        req = LifecycleTransitionRequest(
            thesis_id="t1",
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1,
            reason="New evidence obtained",
            idempotency_key="ik1",
        )
        service.validate_transition(req, ThesisState.DISCOVERED, 1)

    def test_wrong_state_raises(self, service):
        req = LifecycleTransitionRequest(
            thesis_id="t1",
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1,
            reason="test",
            idempotency_key="ik1",
        )
        with pytest.raises(ValueError, match="does not match"):
            service.validate_transition(req, ThesisState.ACTIVE, 1)

    def test_wrong_version_raises(self, service):
        req = LifecycleTransitionRequest(
            thesis_id="t1",
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=2,
            reason="test",
            idempotency_key="ik1",
        )
        with pytest.raises(ValueError, match="does not match"):
            service.validate_transition(req, ThesisState.DISCOVERED, 1)

    def test_illegal_transition_raises(self, service):
        req = LifecycleTransitionRequest(
            thesis_id="t1",
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.ACTIVE,
            expected_version=1,
            reason="skip qualifying",
            idempotency_key="ik1",
        )
        with pytest.raises(ValueError, match="Illegal transition"):
            service.validate_transition(req, ThesisState.DISCOVERED, 1)


class TestIdempotentTransition:
    def test_same_request_validates_twice(self, service):
        """Same idempotency_key can be validated against same state."""
        req = LifecycleTransitionRequest(
            thesis_id="t1",
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1,
            reason="test",
            idempotency_key="ik_same",
        )
        service.validate_transition(req, ThesisState.DISCOVERED, 1)
        # Same request, same state — should still validate
        service.validate_transition(req, ThesisState.DISCOVERED, 1)


class TestRevisionBody:
    def test_build_revision_body(self, service):
        req = LifecycleTransitionRequest(
            thesis_id="t1",
            from_state=ThesisState.DISCOVERED,
            to_state=ThesisState.QUALIFYING,
            expected_version=1,
            reason="New evidence",
            idempotency_key="ik1",
        )
        body = service.build_revision_body(req)
        assert "DISCOVERED" in body
        assert "QUALIFYING" in body
        assert "New evidence" in body
