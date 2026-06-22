"""Event state contracts — event entities, transitions, and state machine config."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .common import ContractBase


class EventState(str, Enum):
    RUMOR = "rumor"
    PROPOSED = "proposed"
    ANNOUNCED = "announced"
    SCHEDULED = "scheduled"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    SIGNED = "signed"
    EFFECTIVE = "effective"
    EXECUTING = "executing"
    COMPLETED = "completed"
    DELAYED = "delayed"
    PARTIALLY_REVERSED = "partially_reversed"
    REVERSED = "reversed"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class TransitionType(str, Enum):
    PROGRESSION = "progression"
    REVISION = "revision"
    DELAY = "delay"
    PARTIAL_REVERSAL = "partial_reversal"
    REVERSAL = "reversal"
    EXPIRY = "expiry"
    CORRECTION = "correction"
    STATE_CORRECTION = "state_correction"


@dataclass
class EventEntity(ContractBase):
    """An event in the intelligence system."""
    contract_name: str = "EventEntity"
    schema_version: str = "1.0.0"

    event_id: str = ""
    event_family: str = "generic"
    title: str = ""
    entities: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)

    current_state: EventState = EventState.UNKNOWN
    previous_state: Optional[EventState] = None
    state_version: int = 1

    parent_event_id: Optional[str] = None
    revision_of: Optional[str] = None
    reversal_of: Optional[str] = None
    evidence_bundle_id: Optional[str] = None
    effective_scope: dict[str, Any] = field(default_factory=dict)
    transitions: list[EventTransition] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.current_state, str):
            self.current_state = EventState(self.current_state)
        if isinstance(self.previous_state, str):
            self.previous_state = EventState(self.previous_state)


@dataclass
class EventTransition(ContractBase):
    """A transition in an event's lifecycle."""
    contract_name: str = "EventTransition"
    schema_version: str = "1.0.0"

    transition_id: str = ""
    event_id: str = ""
    from_state: Optional[EventState] = None
    to_state: EventState = EventState.UNKNOWN
    transition_type: TransitionType = TransitionType.PROGRESSION
    transition_time: str = ""
    first_seen_at: str = ""
    evidence_refs: list[str] = field(default_factory=list)
    reason: str = ""
    magnitude: Optional[float] = None

    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.from_state, str):
            self.from_state = EventState(self.from_state)
        if isinstance(self.to_state, str):
            self.to_state = EventState(self.to_state)
        if isinstance(self.transition_type, str):
            self.transition_type = TransitionType(self.transition_type)


@dataclass
class EventFamilyConfig:
    """Configuration for a specific event family's state machine."""
    family: str = "generic"
    allowed_transitions: dict[str, list[str]] = field(default_factory=dict)
    description: str = ""

    def is_allowed(self, from_state: EventState, to_state: EventState) -> bool:
        if from_state not in self.allowed_transitions:
            return from_state == to_state
        allowed = self.allowed_transitions[from_state.value]
        return to_state.value in allowed


@dataclass
class EventStateMachineRules:
    """Default state machine transition rules."""
    defaults: dict[str, list[str]] = field(default_factory=lambda: {
        EventState.RUMOR.value: [
            EventState.PROPOSED.value, EventState.ANNOUNCED.value,
            EventState.UNKNOWN.value, EventState.EXPIRED.value,
        ],
        EventState.PROPOSED.value: [
            EventState.ANNOUNCED.value, EventState.SCHEDULED.value,
            EventState.UNKNOWN.value, EventState.EXPIRED.value,
        ],
        EventState.ANNOUNCED.value: [
            EventState.SCHEDULED.value, EventState.UNDER_REVIEW.value,
            EventState.DELAYED.value, EventState.UNKNOWN.value,
            EventState.EXPIRED.value,
        ],
        EventState.SCHEDULED.value: [
            EventState.UNDER_REVIEW.value, EventState.DELAYED.value,
            EventState.UNKNOWN.value, EventState.EXPIRED.value,
        ],
        EventState.UNDER_REVIEW.value: [
            EventState.APPROVED.value, EventState.DELAYED.value,
            EventState.UNKNOWN.value, EventState.EXPIRED.value,
        ],
        EventState.APPROVED.value: [
            EventState.SIGNED.value, EventState.EFFECTIVE.value,
            EventState.PARTIALLY_REVERSED.value, EventState.REVERSED.value,
            EventState.EXPIRED.value,
        ],
        EventState.SIGNED.value: [
            EventState.EFFECTIVE.value, EventState.PARTIALLY_REVERSED.value,
            EventState.REVERSED.value, EventState.EXPIRED.value,
        ],
        EventState.EFFECTIVE.value: [
            EventState.EXECUTING.value, EventState.COMPLETED.value,
            EventState.PARTIALLY_REVERSED.value, EventState.REVERSED.value,
            EventState.EXPIRED.value,
        ],
        EventState.EXECUTING.value: [
            EventState.COMPLETED.value, EventState.DELAYED.value,
            EventState.PARTIALLY_REVERSED.value, EventState.REVERSED.value,
        ],
        EventState.COMPLETED.value: [
            EventState.PARTIALLY_REVERSED.value, EventState.REVERSED.value,
        ],
        EventState.DELAYED.value: [
            EventState.SCHEDULED.value, EventState.UNDER_REVIEW.value,
            EventState.UNKNOWN.value, EventState.EXPIRED.value,
        ],
        EventState.PARTIALLY_REVERSED.value: [
            EventState.REVERSED.value, EventState.EXPIRED.value,
        ],
        EventState.REVERSED.value: [EventState.EXPIRED.value],
        EventState.EXPIRED.value: [],
        EventState.UNKNOWN.value: [
            EventState.RUMOR.value, EventState.PROPOSED.value,
            EventState.ANNOUNCED.value,
        ],
    })
