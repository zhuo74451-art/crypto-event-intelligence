"""UnexplainedEventRegistry — in-memory registry of UnexplainedEvent objects."""

from __future__ import annotations

from typing import Optional

from research.intelligence.contracts.unexplained_event import UnexplainedEvent
from research.intelligence.contracts.common import UnexplainedEventStatus


class UnexplainedEventRegistry:
    """In-memory registry for managing unexplained events."""

    def __init__(self) -> None:
        self._records: dict[str, UnexplainedEvent] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, event: UnexplainedEvent) -> None:
        """Register a new unexplained event."""
        self._records[event.unexplained_event_id] = event

    def get(self, unexplained_event_id: str) -> Optional[UnexplainedEvent]:
        """Retrieve an event by id, or None."""
        return self._records.get(unexplained_event_id)

    def remove(self, unexplained_event_id: str) -> bool:
        """Remove an event. Returns True if it existed."""
        return self._records.pop(unexplained_event_id, None) is not None

    def update(self, event: UnexplainedEvent) -> None:
        """Replace the stored event for *event.unexplained_event_id*."""
        self._records[event.unexplained_event_id] = event

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[UnexplainedEvent]:
        """Return all registered events."""
        return list(self._records.values())

    def find_by_status(self, status: UnexplainedEventStatus) -> list[UnexplainedEvent]:
        """Return events with a specific status."""
        return [e for e in self._records.values() if e.research_status == status]

    def open_events(self) -> list[UnexplainedEvent]:
        """Return events that are still open or under investigation."""
        return [
            e for e in self._records.values()
            if e.research_status in (
                UnexplainedEventStatus.OPEN,
                UnexplainedEventStatus.UNDER_INVESTIGATION,
            )
        ]

    def count(self) -> int:
        """Return the number of registered events."""
        return len(self._records)
