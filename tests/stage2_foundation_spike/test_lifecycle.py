"""Test lifecycle validators: ThesisStateMachine and TableValidator."""

import pytest
from experiments.stage2_foundation_spike.lifecycle_spike import (
    ThesisStateMachine,
    TableValidator,
)


@pytest.fixture(params=[ThesisStateMachine, TableValidator])
def validator(request):
    """Parametrize over both validator implementations."""
    return request.param()


class TestLegalTransitions:
    def test_draft_to_under_review(self, validator):
        assert validator.validate("DRAFT", "UNDER_REVIEW") is True

    def test_under_review_to_accepted(self, validator):
        assert validator.validate("UNDER_REVIEW", "ACCEPTED") is True

    def test_under_review_to_rejected(self, validator):
        assert validator.validate("UNDER_REVIEW", "REJECTED") is True

    def test_accepted_to_stale(self, validator):
        assert validator.validate("ACCEPTED", "STALE") is True

    def test_rejected_to_under_review(self, validator):
        assert validator.validate("REJECTED", "UNDER_REVIEW") is True

    def test_stale_to_archived(self, validator):
        assert validator.validate("STALE", "ARCHIVED") is True


class TestIllegalTransitions:
    def test_draft_to_accepted_raises(self, validator):
        with pytest.raises(ValueError):
            validator.validate_or_raise("DRAFT", "ACCEPTED")

    def test_archived_to_draft_raises(self, validator):
        with pytest.raises(ValueError):
            validator.validate_or_raise("ARCHIVED", "DRAFT")

    def test_draft_to_archived_raises(self, validator):
        with pytest.raises(ValueError):
            validator.validate_or_raise("DRAFT", "ARCHIVED")


class TestGetLegalTransitions:
    def test_draft_transitions(self, validator):
        t = validator.get_legal_transitions("DRAFT")
        assert "UNDER_REVIEW" in t
        assert len(t) >= 1

    def test_archived_no_transitions(self, validator):
        t = validator.get_legal_transitions("ARCHIVED")
        assert len(t) == 0


class TestCodeSize:
    def test_both_validators_exist(self):
        tsm = ThesisStateMachine()
        tv = TableValidator()
        assert tsm is not None
        assert tv is not None
        assert hasattr(tsm, "validate")
        assert hasattr(tv, "validate")
        assert hasattr(tsm, "validate_or_raise")
        assert hasattr(tv, "validate_or_raise")


class TestInitialisation:
    def test_state_machine_init(self):
        tsm = ThesisStateMachine()
        assert tsm is not None

    def test_table_validator_init(self):
        tv = TableValidator()
        assert tv is not None
