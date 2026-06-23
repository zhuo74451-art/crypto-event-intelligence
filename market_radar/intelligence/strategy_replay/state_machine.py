"""Strategy state machine — deterministic state transitions for macro strategy replay.

State flow:
candidate -> triggered -> awaiting_confirmation -> confirmed -> supported
Any state may transition to: invalidated, expired, insufficient_evidence
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class StrategyState(str, Enum):
    CANDIDATE = "candidate"
    TRIGGERED = "triggered"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    SUPPORTED = "supported"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


# Allowed transitions per state
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "candidate": {"triggered", "insufficient_evidence", "expired"},
    "triggered": {"awaiting_confirmation", "confirmed", "insufficient_evidence", "invalidated", "expired"},
    "awaiting_confirmation": {"confirmed", "supported", "insufficient_evidence", "invalidated", "expired"},
    "confirmed": {"supported", "invalidated", "expired"},
    "supported": {"invalidated", "expired"},
    "invalidated": set(),  # Terminal
    "expired": set(),      # Terminal
    "insufficient_evidence": {"triggered", "expired"},  # Can recover if new data arrives
}


def is_terminal(state: str) -> bool:
    return state in ("invalidated", "expired")


def can_transition(current: str, target: str) -> bool:
    """Check if a state transition is valid."""
    if current == target:
        return True  # Staying in same state is always valid
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    return target in allowed


def compute_next_state(
    current_state: str,
    has_surprise: bool = False,
    has_macro_inputs: bool = False,
    has_market_data: bool = False,
    has_cross_asset_confirmation: bool = False,
    has_derivatives_confirmation: bool = False,
    has_contradiction: bool = False,
    is_expired: bool = False,
    is_invalidated: bool = False,
    missing_critical_inputs: bool = False,
) -> str:
    """Deterministically compute the next strategy state based on available evidence.

    This is the core state machine logic. Same inputs always produce same output.
    """
    # Terminal overrides
    if is_expired:
        return "expired"
    if is_invalidated:
        return "invalidated"

    # Insufficient evidence check
    if missing_critical_inputs:
        return "insufficient_evidence"

    # State progression
    if current_state == "candidate":
        if has_surprise and has_macro_inputs:
            return "triggered"
        return "candidate"

    if current_state == "triggered":
        if has_contradiction:
            return "invalidated"
        if has_market_data and has_cross_asset_confirmation:
            return "confirmed"
        if has_market_data:
            return "awaiting_confirmation"
        return "triggered"

    if current_state == "awaiting_confirmation":
        if has_contradiction:
            return "invalidated"
        if has_cross_asset_confirmation:
            return "confirmed"
        return "awaiting_confirmation"

    if current_state == "confirmed":
        if has_contradiction:
            return "invalidated"
        if has_derivatives_confirmation:
            return "supported"
        return "confirmed"

    if current_state == "supported":
        if has_contradiction:
            return "invalidated"
        return "supported"

    if current_state == "insufficient_evidence":
        if has_surprise and has_macro_inputs:
            return "triggered"
        return "insufficient_evidence"

    return current_state


def validate_transition_sequence(states: list[str]) -> list[str]:
    """Validate a sequence of state transitions and return any violations."""
    violations = []
    for i in range(len(states) - 1):
        if not can_transition(states[i], states[i + 1]):
            violations.append(f"{states[i]} -> {states[i + 1]} (invalid)")
    return violations
