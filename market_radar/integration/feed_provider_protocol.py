"""Feed Provider Protocol — injectable, bounded, read-only.

Integration layer contract for feed data providers.
W3 CuratedApiReader (or any future reader) registers as a FeedProvider.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from market_radar.intelligence_feed.models import FeedItem


# ── Batch Result ──────────────────────────────────────────────────────

@dataclass
class IntegrationFeedBatch:
    """Standardised output from a Feed Provider.

    Items use the existing W3 FeedItem type so Workbench rendering works
    without transformation.  The Integration layer never re-parses items.
    """
    provider_name: str
    overall_status: str           # "ok" | "degraded" | "unavailable"
    records_seen: int = 0
    records_accepted: int = 0
    records_rejected: int = 0
    live_count: int = 0
    fixture_count: int = 0
    research_count: int = 0
    cached_count: int = 0
    items: list[FeedItem] = field(default_factory=list)
    source_statuses: list[dict] = field(default_factory=list)
    next_cursor: Optional[str] = None
    cursor_safe: bool = True
    provenance: str = "feed_provider"
    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "overall_status": self.overall_status,
            "records_seen": self.records_seen,
            "records_accepted": self.records_accepted,
            "records_rejected": self.records_rejected,
            "live_count": self.live_count,
            "fixture_count": self.fixture_count,
            "research_count": self.research_count,
            "cached_count": self.cached_count,
            "item_count": len(self.items),
            "source_statuses": self.source_statuses,
            "next_cursor": self.next_cursor,
            "cursor_safe": self.cursor_safe,
            "provenance": self.provenance,
            "errors": self.errors,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


# ── Provider Input ───────────────────────────────────────────────────

@dataclass
class FeedProviderInput:
    """Input parameters passed to every Feed Provider call."""
    since_cursor: Optional[str] = None
    limit: int = 100
    max_items: int = 500
    timeout_seconds: float = 10.0
    run_id: str = ""
    no_send: bool = True
    mode: str = "fixture"


# ── Feed Cursor State (persisted) ────────────────────────────────────

@dataclass
class FeedCursorState:
    """Persistent cursor state for incremental feed consumption."""
    cursor_name: str = ""
    cursor_value: Optional[str] = None
    updated_at: str = ""
    provider_name: str = ""
    last_successful_run_id: str = ""
    accepted_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Provider Protocol ─────────────────────────────────────────────────

class FeedProviderProtocol(Protocol):
    """Callable contract for a Feed Provider.

    Integration calls this once per run, never in a loop.
    Provider is responsible for its own bounded timeout.
    """
    def __call__(
        self,
        inp: FeedProviderInput,
    ) -> IntegrationFeedBatch:
        """Execute one feed fetch.  Never raises — catches its own errors.

        Args:
            inp: Input parameters including cursor, limit, timeout.

        Returns:
            IntegrationFeedBatch with items and status.
        """
        ...
