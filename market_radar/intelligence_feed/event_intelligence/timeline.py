"""Timeline builder — manages event timeline entries, idempotent re-entry."""
from __future__ import annotations
from .models import IntelligenceEvent, TimelineEntry, EventStatus


class TimelineBuilder:
    """Builds and maintains event timelines.

    Idempotent: same feed_id added twice produces identical timeline.
    """

    @staticmethod
    def add_entry(event: IntelligenceEvent, entry: TimelineEntry):
        """Add a timeline entry if not already present (by item_id + event_type)."""
        existing = {(e.item_id, e.event_type) for e in event.timeline}
        if (entry.item_id, entry.event_type) not in existing:
            event.timeline.append(entry)

    @staticmethod
    def update_status(event: IntelligenceEvent, new_status: EventStatus, reason: str = ""):
        """Update event status with a timeline entry."""
        old = event.status
        if old == new_status:
            return
        event.status = new_status
        event.timeline.append(TimelineEntry(
            timestamp=event.latest_at or "",
            item_id=event.event_id,
            source_label="system",
            event_type="status_change",
            summary=reason or f"Status: {old.value} → {new_status.value}",
            previous_status=old.value,
            new_status=new_status.value,
        ))
