from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from .common import MacroEnum


class CalendarEventStatus(MacroEnum):
    """Current status of a scheduled macro release event."""
    SCHEDULED = "scheduled"
    RESCHEDULED = "rescheduled"
    RELEASED = "released"
    DELAYED = "delayed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class CalendarSource(MacroEnum):
    """Recognised sources of calendar event information."""
    BLOOMBERG = "bloomberg"
    REUTERS = "reuters"
    INVESTING_DOT_COM = "investing_dot_com"
    FOREX_FACTORY = "forex_factory"
    GOVERNMENT_CALENDAR = "government_calendar"
    CENTRAL_BANK = "central_bank"
    MANUAL = "manual"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CalendarEventRecord:
    """A scheduled (or already-published) macro-economic data release.

    Attributes:
        calendar_event_id: Unique identifier for this calendar entry.
        release_family: Logical grouping (e.g. 'NFP', 'CPI', 'GDP').
        scheduled_release_time: The official scheduled release datetime.
        source_timezone: IANA timezone of the release authority.
        expected_components: Named sub-components expected in this release.
        release_authority: The agency producing the release (e.g. 'BLS').
        calendar_source: Which feed / vendor provided this calendar entry.
        calendar_first_seen_at: When this event first appeared in our system.
        calendar_updated_at: When this calendar record was last updated.
        rescheduled_from: Previous scheduled time if this is a reschedule.
        status: Current status of the calendar event.
    """
    calendar_event_id: str
    release_family: str
    scheduled_release_time: datetime
    source_timezone: str = "UTC"
    expected_components: list[str] = field(default_factory=list)
    release_authority: str = ""
    calendar_source: CalendarSource = CalendarSource.UNKNOWN
    calendar_first_seen_at: Optional[datetime] = None
    calendar_updated_at: Optional[datetime] = None
    rescheduled_from: Optional[datetime] = None
    status: CalendarEventStatus = CalendarEventStatus.SCHEDULED

    @property
    def is_pending(self) -> bool:
        """True if the event has not yet been released."""
        return self.status in (
            CalendarEventStatus.SCHEDULED,
            CalendarEventStatus.RESCHEDULED,
            CalendarEventStatus.DELAYED,
        )

    @property
    def is_resolved(self) -> bool:
        """True if the event has been released or cancelled."""
        return self.status in (
            CalendarEventStatus.RELEASED,
            CalendarEventStatus.CANCELLED,
        )

    @property
    def had_schedule_change(self) -> bool:
        """True if this event was rescheduled or delayed."""
        return self.status in (
            CalendarEventStatus.RESCHEDULED,
            CalendarEventStatus.DELAYED,
        )
