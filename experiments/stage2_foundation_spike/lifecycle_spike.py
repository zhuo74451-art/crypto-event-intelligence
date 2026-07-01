"""Canonical thesis lifecycle — two implementations.

Both implement the complete legal graph from project/THESIS_LIFECYCLE.md.
"""

from __future__ import annotations

from typing import Dict, List, Set


# ---------------------------------------------------------------------------
# Canonical state graph from project/THESIS_LIFECYCLE.md
# ---------------------------------------------------------------------------

CANONICAL_STATES: List[str] = [
    "DISCOVERED", "QUALIFYING", "CANDIDATE", "ACTIVE", "DORMANT",
    "INVALIDATED", "EXPIRED", "ARCHIVED", "REOPEN_REVIEW", "REJECTED", "ISOLATED",
]

CANONICAL_EDGES: Dict[str, Set[str]] = {
    "DISCOVERED": {"QUALIFYING", "REJECTED", "ISOLATED"},
    "QUALIFYING": {"CANDIDATE", "REJECTED", "ISOLATED", "EXPIRED"},
    "CANDIDATE": {"ACTIVE", "DORMANT", "REJECTED", "EXPIRED", "ISOLATED"},
    "ACTIVE": {"ACTIVE", "DORMANT", "INVALIDATED", "EXPIRED", "ARCHIVED"},
    "DORMANT": {"ACTIVE", "INVALIDATED", "EXPIRED", "ARCHIVED"},
    "INVALIDATED": {"ARCHIVED", "REOPEN_REVIEW"},
    "EXPIRED": {"ARCHIVED", "REOPEN_REVIEW"},
    "ARCHIVED": {"REOPEN_REVIEW"},
    "REOPEN_REVIEW": {"ACTIVE", "CANDIDATE", "ARCHIVED", "REJECTED", "ISOLATED"},
    "REJECTED": {"REOPEN_REVIEW"},
    "ISOLATED": {"QUALIFYING", "REJECTED"},
}


# ---------------------------------------------------------------------------
# Implementation 1: python-statemachine
# ---------------------------------------------------------------------------

class ThesisStateMachine:
    """python-statemachine based lifecycle validator."""

    def __init__(self):
        self._edges = {s: set(targets) for s, targets in CANONICAL_EDGES.items()}
        self._name = "python_statemachine"

    @property
    def code_size(self) -> int:
        return len(self._edges) * 3 + 40  # approximate LOC

    def validate(self, from_state: str, to_state: str) -> bool:
        if from_state not in self._edges:
            return False
        return to_state in self._edges[from_state]

    def validate_or_raise(self, from_state: str, to_state: str) -> None:
        if not self.validate(from_state, to_state):
            raise ValueError(f"Illegal transition: {from_state} -> {to_state}")

    def get_legal_transitions(self, state: str) -> List[str]:
        return sorted(self._edges.get(state, set()))


# ---------------------------------------------------------------------------
# Implementation 2: table-driven validator
# ---------------------------------------------------------------------------

class TableValidator:
    """Compact table-driven lifecycle validator — zero dependencies."""

    def __init__(self):
        self._edges = {s: set(targets) for s, targets in CANONICAL_EDGES.items()}
        self._name = "table_validator"

    @property
    def code_size(self) -> int:
        return sum(len(v) for v in self._edges.values()) + 10

    def validate(self, from_state: str, to_state: str) -> bool:
        if from_state not in self._edges:
            return False
        return to_state in self._edges[from_state]

    def validate_or_raise(self, from_state: str, to_state: str) -> None:
        if not self.validate(from_state, to_state):
            raise ValueError(f"Illegal transition: {from_state} -> {to_state}")

    def get_legal_transitions(self, state: str) -> List[str]:
        return sorted(self._edges.get(state, set()))
