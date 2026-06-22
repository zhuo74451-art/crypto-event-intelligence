"""Promotion — transition maps and validation for promotion across lifecycle stages.

This module defines the allowed transitions between statuses for various
life-cycle enums and provides helper functions to validate promotions.
"""

from __future__ import annotations

from research.intelligence.contracts.common import (
    ClaimStatus,
    ConflictType,
    GapStatus,
    HypothesisStatus,
    ResolutionStatus,
    RuntimeContractStatus,
    StrategyCandidateValidationStatus,
    StrategySeedStatus,
    UnexplainedEventStatus,
)

# ---------------------------------------------------------------------------
# Transition maps
# ---------------------------------------------------------------------------

CLAIM_STATUS_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.UNVERIFIED: {ClaimStatus.CANDIDATE, ClaimStatus.STALE, ClaimStatus.RETRACTED},
    ClaimStatus.CANDIDATE: {ClaimStatus.SUPPORTED, ClaimStatus.CONTRADICTED, ClaimStatus.MIXED, ClaimStatus.STALE, ClaimStatus.RETRACTED},
    ClaimStatus.SUPPORTED: {ClaimStatus.MIXED, ClaimStatus.CONTRADICTED, ClaimStatus.STALE, ClaimStatus.RETRACTED},
    ClaimStatus.CONTRADICTED: {ClaimStatus.SUPPORTED, ClaimStatus.MIXED, ClaimStatus.STALE, ClaimStatus.RETRACTED},
    ClaimStatus.MIXED: {ClaimStatus.SUPPORTED, ClaimStatus.CONTRADICTED, ClaimStatus.STALE, ClaimStatus.RETRACTED},
    ClaimStatus.STALE: {ClaimStatus.UNVERIFIED, ClaimStatus.CANDIDATE, ClaimStatus.RETRACTED},
    ClaimStatus.RETRACTED: set(),
    ClaimStatus.BACKGROUND: {ClaimStatus.UNVERIFIED, ClaimStatus.CANDIDATE, ClaimStatus.STALE},
}

HYPOTHESIS_STATUS_TRANSITIONS: dict[HypothesisStatus, set[HypothesisStatus]] = {
    HypothesisStatus.PROPOSED: {HypothesisStatus.SPECIFICATION_READY, HypothesisStatus.DATA_BLOCKED, HypothesisStatus.REJECTED, HypothesisStatus.STALE},
    HypothesisStatus.SPECIFICATION_READY: {HypothesisStatus.DATA_BLOCKED, HypothesisStatus.VALIDATION_READY, HypothesisStatus.REJECTED, HypothesisStatus.STALE},
    HypothesisStatus.DATA_BLOCKED: {HypothesisStatus.SPECIFICATION_READY, HypothesisStatus.REJECTED, HypothesisStatus.STALE},
    HypothesisStatus.VALIDATION_READY: {HypothesisStatus.UNDER_TEST, HypothesisStatus.REJECTED, HypothesisStatus.STALE},
    HypothesisStatus.UNDER_TEST: {HypothesisStatus.SUPPORTED, HypothesisStatus.REJECTED, HypothesisStatus.MIXED, HypothesisStatus.STALE},
    HypothesisStatus.SUPPORTED: {HypothesisStatus.MIXED, HypothesisStatus.STALE, HypothesisStatus.REJECTED},
    HypothesisStatus.REJECTED: {HypothesisStatus.PROPOSED, HypothesisStatus.STALE},
    HypothesisStatus.MIXED: {HypothesisStatus.UNDER_TEST, HypothesisStatus.SUPPORTED, HypothesisStatus.REJECTED, HypothesisStatus.STALE},
    HypothesisStatus.STALE: {HypothesisStatus.PROPOSED, HypothesisStatus.REJECTED},
}

SEED_STATUS_TRANSITIONS: dict[StrategySeedStatus, set[StrategySeedStatus]] = {
    StrategySeedStatus.UNVERIFIED: {StrategySeedStatus.RESEARCH_READY, StrategySeedStatus.REJECTED, StrategySeedStatus.STALE},
    StrategySeedStatus.RESEARCH_READY: {StrategySeedStatus.SPECIFICATION_READY, StrategySeedStatus.REJECTED, StrategySeedStatus.STALE},
    StrategySeedStatus.SPECIFICATION_READY: {StrategySeedStatus.VALIDATION_READY, StrategySeedStatus.REJECTED, StrategySeedStatus.STALE},
    StrategySeedStatus.VALIDATION_READY: {StrategySeedStatus.REJECTED, StrategySeedStatus.STALE},
    StrategySeedStatus.REJECTED: {StrategySeedStatus.UNVERIFIED, StrategySeedStatus.STALE},
    StrategySeedStatus.STALE: {StrategySeedStatus.UNVERIFIED, StrategySeedStatus.REJECTED},
}

CANDIDATE_VALIDATION_TRANSITIONS: dict[StrategyCandidateValidationStatus, set[StrategyCandidateValidationStatus]] = {
    StrategyCandidateValidationStatus.UNVALIDATED: {
        StrategyCandidateValidationStatus.DATA_BLOCKED,
        StrategyCandidateValidationStatus.VALIDATION_READY,
        StrategyCandidateValidationStatus.REJECTED,
    },
    StrategyCandidateValidationStatus.DATA_BLOCKED: {
        StrategyCandidateValidationStatus.UNVALIDATED,
        StrategyCandidateValidationStatus.VALIDATION_READY,
        StrategyCandidateValidationStatus.REJECTED,
    },
    StrategyCandidateValidationStatus.VALIDATION_READY: {
        StrategyCandidateValidationStatus.UNDER_EXTERNAL_VALIDATION,
        StrategyCandidateValidationStatus.REJECTED,
    },
    StrategyCandidateValidationStatus.UNDER_EXTERNAL_VALIDATION: {
        StrategyCandidateValidationStatus.VALIDATION_READY,
        StrategyCandidateValidationStatus.REJECTED,
    },
    StrategyCandidateValidationStatus.REJECTED: {StrategyCandidateValidationStatus.UNVALIDATED},
}

RUNTIME_STATUS_TRANSITIONS: dict[RuntimeContractStatus, set[RuntimeContractStatus]] = {
    RuntimeContractStatus.PENDING_INTEGRATION: {RuntimeContractStatus.INTEGRATION_READY, RuntimeContractStatus.INCOMPATIBLE},
    RuntimeContractStatus.INCOMPATIBLE: {RuntimeContractStatus.PENDING_INTEGRATION},
    RuntimeContractStatus.INTEGRATION_READY: {RuntimeContractStatus.INCOMPATIBLE},
}

RESOLUTION_STATUS_TRANSITIONS: dict[ResolutionStatus, set[ResolutionStatus]] = {
    ResolutionStatus.UNRESOLVED: {ResolutionStatus.PARTIALLY_RESOLVED, ResolutionStatus.NOT_A_TRUE_CONFLICT, ResolutionStatus.LEFT_MORE_SUPPORTED, ResolutionStatus.RIGHT_MORE_SUPPORTED, ResolutionStatus.REGIME_DEPENDENT, ResolutionStatus.MEASUREMENT_DEPENDENT},
    ResolutionStatus.PARTIALLY_RESOLVED: {ResolutionStatus.UNRESOLVED, ResolutionStatus.LEFT_MORE_SUPPORTED, ResolutionStatus.RIGHT_MORE_SUPPORTED, ResolutionStatus.REGIME_DEPENDENT, ResolutionStatus.MEASUREMENT_DEPENDENT},
    ResolutionStatus.NOT_A_TRUE_CONFLICT: set(),
    ResolutionStatus.LEFT_MORE_SUPPORTED: set(),
    ResolutionStatus.RIGHT_MORE_SUPPORTED: set(),
    ResolutionStatus.REGIME_DEPENDENT: {ResolutionStatus.UNRESOLVED},
    ResolutionStatus.MEASUREMENT_DEPENDENT: {ResolutionStatus.UNRESOLVED},
}

GAP_STATUS_TRANSITIONS: dict[GapStatus, set[GapStatus]] = {
    GapStatus.OPEN: {GapStatus.PARTIALLY_ADDRESSED, GapStatus.CLOSED, GapStatus.SUPERSEDED},
    GapStatus.PARTIALLY_ADDRESSED: {GapStatus.OPEN, GapStatus.CLOSED, GapStatus.SUPERSEDED},
    GapStatus.CLOSED: {GapStatus.OPEN, GapStatus.SUPERSEDED},
    GapStatus.SUPERSEDED: set(),
}

UNEXPLAINED_EVENT_STATUS_TRANSITIONS: dict[UnexplainedEventStatus, set[UnexplainedEventStatus]] = {
    UnexplainedEventStatus.OPEN: {UnexplainedEventStatus.UNDER_INVESTIGATION, UnexplainedEventStatus.DISMISSED},
    UnexplainedEventStatus.UNDER_INVESTIGATION: {UnexplainedEventStatus.CANDIDATE_EXPLANATION_FOUND, UnexplainedEventStatus.RESOLVED, UnexplainedEventStatus.DISMISSED},
    UnexplainedEventStatus.CANDIDATE_EXPLANATION_FOUND: {UnexplainedEventStatus.UNDER_INVESTIGATION, UnexplainedEventStatus.RESOLVED, UnexplainedEventStatus.DISMISSED},
    UnexplainedEventStatus.RESOLVED: {UnexplainedEventStatus.OPEN, UnexplainedEventStatus.DISMISSED},
    UnexplainedEventStatus.DISMISSED: {UnexplainedEventStatus.OPEN},
}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def can_transition_claim(current: ClaimStatus, target: ClaimStatus) -> bool:
    """Return True if the transition from *current* to *target* is allowed."""
    return target in CLAIM_STATUS_TRANSITIONS.get(current, set())


def can_transition_hypothesis(current: HypothesisStatus, target: HypothesisStatus) -> bool:
    """Return True if the transition from *current* to *target* is allowed."""
    return target in HYPOTHESIS_STATUS_TRANSITIONS.get(current, set())


def can_transition_seed(current: StrategySeedStatus, target: StrategySeedStatus) -> bool:
    """Return True if the transition from *current* to *target* is allowed."""
    return target in SEED_STATUS_TRANSITIONS.get(current, set())


def can_transition_candidate_validation(
    current: StrategyCandidateValidationStatus,
    target: StrategyCandidateValidationStatus,
) -> bool:
    """Return True if the transition from *current* to *target* is allowed."""
    return target in CANDIDATE_VALIDATION_TRANSITIONS.get(current, set())


def can_transition_runtime(current: RuntimeContractStatus, target: RuntimeContractStatus) -> bool:
    """Return True if the transition from *current* to *target* is allowed."""
    return target in RUNTIME_STATUS_TRANSITIONS.get(current, set())


def can_transition_resolution(current: ResolutionStatus, target: ResolutionStatus) -> bool:
    """Return True if the transition from *current* to *target* is allowed."""
    return target in RESOLUTION_STATUS_TRANSITIONS.get(current, set())


def can_transition_gap(current: GapStatus, target: GapStatus) -> bool:
    """Return True if the transition from *current* to *target* is allowed."""
    return target in GAP_STATUS_TRANSITIONS.get(current, set())


def can_transition_unexplained_event(
    current: UnexplainedEventStatus,
    target: UnexplainedEventStatus,
) -> bool:
    """Return True if the transition from *current* to *target* is allowed."""
    return target in UNEXPLAINED_EVENT_STATUS_TRANSITIONS.get(current, set())


# Map / dispatch helpers

TRANSITION_DISPATCH = {
    "claim": (CLAIM_STATUS_TRANSITIONS, can_transition_claim),
    "hypothesis": (HYPOTHESIS_STATUS_TRANSITIONS, can_transition_hypothesis),
    "seed": (SEED_STATUS_TRANSITIONS, can_transition_seed),
    "candidate_validation": (CANDIDATE_VALIDATION_TRANSITIONS, can_transition_candidate_validation),
    "runtime": (RUNTIME_STATUS_TRANSITIONS, can_transition_runtime),
    "resolution": (RESOLUTION_STATUS_TRANSITIONS, can_transition_resolution),
    "gap": (GAP_STATUS_TRANSITIONS, can_transition_gap),
    "unexplained_event": (UNEXPLAINED_EVENT_STATUS_TRANSITIONS, can_transition_unexplained_event),
}
