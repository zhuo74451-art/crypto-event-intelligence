"""
Thesis lifecycle state machine — two implementations:
1. ThesisStateMachine using python-statemachine (library-driven)
2. TableValidator using a compact dict-of-dicts (table-driven)

Both expose:
    validate(from_state, to_state) -> bool
    validate_or_raise(from_state, to_state)  -> None | raise ValueError
    get_legal_transitions(state) -> list[str]
"""

from __future__ import annotations

from statemachine import State, StateMachine

# ── 1. Library-driven implementation ────────────────────────────────────────

class ThesisStateMachine(StateMachine):
    """State machine backed by python-statemachine."""

    draft = State("DRAFT", initial=True)
    under_review = State("UNDER_REVIEW")
    accepted = State("ACCEPTED")
    rejected = State("REJECTED")
    stale = State("STALE")
    archived = State("ARCHIVED", final=True)

    # ── transitions ────────────────────────────────────────────────────
    submit = draft.to(under_review)
    approve = under_review.to(accepted)
    reject = under_review.to(rejected)
    reopen_accepted = accepted.to(under_review)
    stale_accepted = accepted.to(stale)
    reopen_rejected = rejected.to(under_review)
    archive_rejected = rejected.to(archived)
    archive_stale = stale.to(archived)
    reopen_stale = stale.to(under_review)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Build a plain-dict lookup so we don't couple callers to the
        # library's TransitionList internals.
        self._legal: dict[str, set[str]] = {}
        for state in self.states_map.values():
            self._legal[state.name] = {t.target.name for t in state.transitions}

    # ── public helpers ─────────────────────────────────────────────────

    def validate(self, from_state: str, to_state: str) -> bool:
        """Return True iff the transition is allowed."""
        return to_state in self._legal.get(from_state, set())

    def validate_or_raise(self, from_state: str, to_state: str) -> None:
        """Raise ValueError if the transition is not allowed."""
        if not self.validate(from_state, to_state):
            raise ValueError(
                f"Illegal transition: {from_state} -> {to_state}. "
                f"Legal targets from {from_state}: "
                f"{sorted(self._legal.get(from_state, set()))}"
            )

    def get_legal_transitions(self, state: str) -> list[str]:
        """Return sorted list of states reachable from *state*."""
        return sorted(self._legal.get(state, set()))


# ── 2. Table-driven implementation ─────────────────────────────────────────

class TableValidator:
    """Validator built from a plain dict-of-sets — zero dependencies."""

    # The full transition table as a dict-of-sets.
    # This is the single source of truth for this class.
    _legal: dict[str, set[str]] = {
        "DRAFT": {"UNDER_REVIEW"},
        "UNDER_REVIEW": {"ACCEPTED", "REJECTED"},
        "ACCEPTED": {"STALE", "UNDER_REVIEW"},
        "REJECTED": {"UNDER_REVIEW", "ARCHIVED"},
        "STALE": {"ARCHIVED", "UNDER_REVIEW"},
        "ARCHIVED": set(),
    }

    def validate(self, from_state: str, to_state: str) -> bool:
        """Return True iff the transition is allowed."""
        return to_state in self._legal.get(from_state, set())

    def validate_or_raise(self, from_state: str, to_state: str) -> None:
        """Raise ValueError if the transition is not allowed."""
        if not self.validate(from_state, to_state):
            raise ValueError(
                f"Illegal transition: {from_state} -> {to_state}. "
                f"Legal targets from {from_state}: "
                f"{sorted(self._legal.get(from_state, set()))}"
            )

    def get_legal_transitions(self, state: str) -> list[str]:
        """Return sorted list of states reachable from *state*."""
        return sorted(self._legal.get(state, set()))


# ── Code-size comparison ────────────────────────────────────────────────────
# ThesisStateMachine  : ~50 lines (class body + imports)
#   - includes State/StateMachine imports, state declarations, transition
#     definitions, __init__ builder, and three public methods.
#   - leans on a ~130 kB library with a full event-loop, guards, listeners, etc.
#
# TableValidator      : ~30 lines (class body + imports)
#   - zero dependencies outside stdlib.
#   - the transition table is expressed as a single dict-of-sets literal.
#   - three public methods (validate, validate_or_raise, get_legal_transitions).
#
# For this problem domain the table-driven version is both shorter and easier
# to audit — the transition matrix is visible at a glance.
# ─────────────────────────────────────────────────────────────────────────────


__all__ = ["ThesisStateMachine", "TableValidator"]
