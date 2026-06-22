from __future__ import annotations
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from market_radar.domains.macro.contracts.release_calendar import CalendarEventRecord, CalendarEventStatus


class ReleaseIdentityEngine:
    @staticmethod
    def identify_release_cluster(events: List[CalendarEventRecord]) -> str:
        """Create a deterministic cluster ID from events at the same release time."""
        raw = "|".join(
            f"{e.calendar_event_id}:{e.scheduled_release_time.isoformat() if isinstance(e.scheduled_release_time, datetime) else str(e.scheduled_release_time)}"
            for e in sorted(events, key=lambda x: x.calendar_event_id)
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def validate_calendar_integrity(calendar: CalendarEventRecord) -> List[str]:
        """Check for calendar data integrity issues. Returns list of issues."""
        issues: List[str] = []
        if calendar.status == CalendarEventStatus.UNKNOWN:
            issues.append("calendar_status_unknown")
        if calendar.scheduled_release_time is None:
            issues.append("release_time_missing")
        if not calendar.expected_components:
            issues.append("no_expected_components")
        return issues

    @staticmethod
    def detect_concurrent_events(events: List[CalendarEventRecord], window_minutes: int = 5) -> bool:
        """Check if multiple events share the same release time window."""
        if len(events) < 2:
            return False
        times: List[datetime] = []
        for e in events:
            t = e.scheduled_release_time
            if isinstance(t, datetime):
                times.append(t)
        if len(times) < 2:
            return False
        for i in range(len(times)):
            for j in range(i + 1, len(times)):
                diff = abs((times[i] - times[j]).total_seconds())
                if diff <= window_minutes * 60:
                    return True
        return False

    @staticmethod
    def compute_release_cluster_id(events: List[CalendarEventRecord]) -> str:
        """Compute a cluster ID for a group of events released at the same time."""
        return ReleaseIdentityEngine.identify_release_cluster(events)
