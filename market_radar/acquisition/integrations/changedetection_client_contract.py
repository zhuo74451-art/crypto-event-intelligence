from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from market_radar.acquisition.contracts.revision import RevisionType


# ── Protocol ──────────────────────────────────────────────────────────────


class ChangedetectionClientProtocol(ABC):
    """Abstract interface for a Changedetection.io client."""

    @abstractmethod
    def get_watch(self, watch_id: str) -> dict | None:
        """Return watch details for *watch_id*, or *None* if not found."""
        ...

    @abstractmethod
    def get_watch_history(self, watch_id: str) -> list[dict]:
        """Return the change history for the given watch."""
        ...

    @abstractmethod
    def get_all_watches(self) -> list[dict]:
        """Return every watch known to the backend."""
        ...


# ── Contract dataclass ────────────────────────────────────────────────────


@dataclass
class ChangedetectionWatchContract:
    watch_id: str
    target_url: str
    last_checked_at: datetime | None = None
    last_changed_at: datetime | None = None
    current_hash: str = ""
    triggered: bool = False
    notification_sent: bool = False


# ── Adapter ───────────────────────────────────────────────────────────────


class ChangedetectionEventAdapter:
    """Maps a Changedetection.io notification payload to a *Revision* candidate.

    Deduplication is handled by tracking already-processed event identifiers.
    """

    def __init__(self) -> None:
        self._processed_ids: set[str] = set()

    def adapt_event(
        self,
        watch: ChangedetectionWatchContract,
        change_event: dict,
    ) -> tuple[RevisionType, str] | None:
        """Convert *change_event* (from CD) into a ``(RevisionType, summary)``
        pair, or return *None* when the event is a duplicate.

        The dedup key is derived from ``watch_id + event_id`` (or
        ``watch_id + timestamp`` when no explicit event id is available).
        """
        event_id = change_event.get("id") or change_event.get("event_id")
        if event_id is None:
            # fall back to a combination of watch id and a timestamp field
            ts = change_event.get("timestamp") or change_event.get("when") or str(datetime.now(timezone.utc))
            dedup_key = f"{watch.watch_id}::{ts}"
        else:
            dedup_key = f"{watch.watch_id}::{event_id}"

        if dedup_key in self._processed_ids:
            return None

        self._processed_ids.add(dedup_key)

        change_type = change_event.get("change_type", "changed")
        if change_type == "new":
            revision_type = RevisionType.FIRST_SEEN
        elif change_type in ("changed", "content_changed"):
            revision_type = RevisionType.CONTENT_CHANGED
        elif change_type == "metadata_changed":
            revision_type = RevisionType.METADATA_CHANGED
        else:
            revision_type = RevisionType.CONTENT_CHANGED

        summary = (
            change_event.get("summary")
            or change_event.get("message")
            or f"Watch {watch.watch_id} detected a change"
        )
        return revision_type, summary

    def reset(self) -> None:
        """Clear the internal dedup tracking set."""
        self._processed_ids.clear()


# ── Fake client (in-memory) ──────────────────────────────────────────────


class FakeChangedetectionClient(ChangedetectionClientProtocol):
    """In‑memory implementation of
    :class:`ChangedetectionClientProtocol` for testing.
    """

    def __init__(self) -> None:
        self._watches: dict[str, dict] = {}
        self._history: dict[str, list[dict]] = {}

    def add_watch(
        self,
        watch_id: str,
        target_url: str = "",
        last_checked_at: str | None = None,
        last_changed_at: str | None = None,
        current_hash: str = "",
        triggered: bool = False,
        notification_sent: bool = False,
        history: list[dict] | None = None,
    ) -> None:
        """Register a watch (and optionally its history) for testing."""
        self._watches[watch_id] = {
            "id": watch_id,
            "url": target_url,
            "last_checked": last_checked_at,
            "last_changed": last_changed_at,
            "hash": current_hash,
            "triggered": triggered,
            "notification_sent": notification_sent,
        }
        if history is not None:
            self._history[watch_id] = history

    # -- protocol implementation -------------------------------------------

    def get_watch(self, watch_id: str) -> dict | None:
        return self._watches.get(watch_id)

    def get_watch_history(self, watch_id: str) -> list[dict]:
        return self._history.get(watch_id, [])

    def get_all_watches(self) -> list[dict]:
        return list(self._watches.values())
