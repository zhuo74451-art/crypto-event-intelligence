"""Test canonical lifecycle with both validators — exact state graph from THESIS_LIFECYCLE.md."""

import pytest
from experiments.stage2_foundation_spike.lifecycle_spike import (
    ThesisStateMachine,
    TableValidator,
    CANONICAL_EDGES,
    CANONICAL_STATES,
)


ALL_STATES = CANONICAL_STATES
LEGAL_EDGES = CANONICAL_EDGES

# Collect all legal edges for parametrized testing
LEGAL_TRANSITIONS = [(f, t) for f, targets in LEGAL_EDGES.items() for t in targets]

# Collect all pair combinations — illegal unless in LEGAL_EDGES
ALL_PAIRS = [(f, t) for f in ALL_STATES for t in ALL_STATES]


@pytest.fixture(params=[ThesisStateMachine, TableValidator])
def validator(request):
    return request.param()


class TestLegalEdges:
    @pytest.mark.parametrize("from_state,to_state", LEGAL_TRANSITIONS)
    def test_legal_transition_accepted(self, validator, from_state, to_state):
        assert validator.validate(from_state, to_state), f"{from_state} -> {to_state} should be legal"


class TestIllegalEdges:
    # Representative illegal jumps
    ILLEGAL = [
        ("DISCOVERED", "ACTIVE"),
        ("DISCOVERED", "ARCHIVED"),
        ("ARCHIVED", "DISCOVERED"),
        ("REJECTED", "ACTIVE"),
        ("ISOLATED", "ACTIVE"),
        ("DORMANT", "QUALIFYING"),
        ("INVALIDATED", "ACTIVE"),
        ("EXPIRED", "CANDIDATE"),
    ]

    @pytest.mark.parametrize("from_state,to_state", ILLEGAL)
    def test_illegal_transition_raises(self, validator, from_state, to_state):
        assert not validator.validate(from_state, to_state), f"{from_state} -> {to_state} should be illegal"
        with pytest.raises(ValueError, match="Illegal transition"):
            validator.validate_or_raise(from_state, to_state)


class TestGetLegalTransitions:
    def test_all_states_have_definition(self, validator):
        for state in ALL_STATES:
            trans = validator.get_legal_transitions(state)
            assert isinstance(trans, list)

    def test_archived_only_reopen(self, validator):
        trans = validator.get_legal_transitions("ARCHIVED")
        assert trans == ["REOPEN_REVIEW"]

    def test_reopen_review_has_multiple_targets(self, validator):
        trans = validator.get_legal_transitions("REOPEN_REVIEW")
        assert len(trans) >= 4


class TestValidation:
    def test_unknown_state_returns_false(self, validator):
        assert validator.validate("UNKNOWN", "ACTIVE") is False

    def test_self_transition_allowed_only_for_active(self, validator):
        assert validator.validate("ACTIVE", "ACTIVE") is True
        for s in ALL_STATES:
            if s != "ACTIVE":
                assert not validator.validate(s, s), f"{s} -> {s} should be illegal"


class TestCodeSize:
    def test_both_validators_exist(self):
        tsm = ThesisStateMachine()
        tv = TableValidator()
        assert tsm.code_size > 0
        assert tv.code_size > 0
