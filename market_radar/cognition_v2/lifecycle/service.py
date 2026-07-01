"""Canonical 11-state thesis lifecycle service.

Dependency: domain contracts only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from market_radar.cognition_v2.domain.contracts import (
    CANONICAL_EDGES,
    CANONICAL_STATES,
    EvidenceRef,
    LifecycleTransitionRequest,
    ThesisState,
)


class LifecycleValidator:
    """Table-driven thesis lifecycle validator — zero dependencies."""

    def __init__(self):
        self._edges: Dict[ThesisState, Set[ThesisState]] = {
            s: set(targets) for s, targets in CANONICAL_EDGES.items()
        }

    @property
    def code_size(self) -> int:
        return sum(len(v) for v in self._edges.values())

    def validate(self, from_state: ThesisState, to_state: ThesisState) -> bool:
        """Check if a transition is legal according to the canonical graph."""
        return to_state in self._edges.get(from_state, set())

    def validate_or_raise(self, from_state: ThesisState, to_state: ThesisState) -> None:
        if not self.validate(from_state, to_state):
            raise ValueError(
                f"Illegal transition: {from_state.value} -> {to_state.value}"
            )

    def get_legal_transitions(self, state: ThesisState) -> List[ThesisState]:
        return sorted(self._edges.get(state, set()), key=lambda s: s.value)

    def all_states(self) -> List[ThesisState]:
        return list(CANONICAL_STATES)


class LifecycleService:
    """Application service for thesis lifecycle transitions.

    Validates, records revision, and applies compare-and-swap update.
    This is the domain service; persistence is injected.
    """

    def __init__(self, validator: Optional[LifecycleValidator] = None):
        self._validator = validator or LifecycleValidator()

    @property
    def validator(self) -> LifecycleValidator:
        return self._validator

    def validate_transition(
        self,
        request: LifecycleTransitionRequest,
        current_state: ThesisState,
        current_version: int,
    ) -> None:
        """Validate a lifecycle transition request against current state."""
        # Check state match
        if current_state != request.from_state:
            raise ValueError(
                f"Current state {current_state.value} does not match "
                f"expected from_state {request.from_state.value}"
            )

        # Check version match
        if current_version != request.expected_version:
            raise ValueError(
                f"Current version {current_version} does not match "
                f"expected version {request.expected_version}"
            )

        # Check legal transition
        self._validator.validate_or_raise(request.from_state, request.to_state)

        # Check reason
        if not request.reason.strip():
            raise ValueError("Transition reason must not be empty")

    def build_revision_body(
        self,
        request: LifecycleTransitionRequest,
    ) -> str:
        """Build a revision body from a transition request."""
        evidence_summary = (
            f" evidence_refs={len(request.evidence_refs)},"
            if request.evidence_refs
            else ""
        )
        return (
            f"Transition: {request.from_state.value} -> {request.to_state.value}. "
            f"Reason: {request.reason}.{evidence_summary}"
        )
