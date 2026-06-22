from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from market_radar.acquisition.contracts.revision import RevisionType


# ── Protocol ──────────────────────────────────────────────────────────────


class ArchiveClientProtocol(ABC):
    """Abstract interface for an ArchiveBox client."""

    @abstractmethod
    def submit_archive(self, url: str) -> str:
        """Submit *url* for archiving and return the assigned ``archive_id``."""
        ...

    @abstractmethod
    def get_archive(self, archive_id: str) -> dict | None:
        """Return archive details for *archive_id*, or *None* if not found."""
        ...

    @abstractmethod
    def check_status(self, archive_id: str) -> str:
        """Return the current status of the archive: ``pending``,
        ``completed``, or ``failed``."""
        ...


# ── Contract dataclasses ─────────────────────────────────────────────────


@dataclass
class ArchiveRequest:
    """Represents a request to archive a URL."""
    url: str
    archive_id: str = ""
    submitted_at: datetime | None = None
    status: str = "pending"


@dataclass
class ArchiveReceipt:
    """Represents a completed archive artifact."""
    archive_id: str
    original_url: str
    archived_at: datetime | None = None
    content_hash: str = ""
    output_format: str = ""
    status: str = "completed"


@dataclass
class ArchiveFailure:
    """Represents a failed archiving attempt."""
    archive_id: str
    reason: str = ""
    occurred_at: datetime | None = None


# ── Fake client (in-memory) ──────────────────────────────────────────────


class FakeArchiveBoxClient(ArchiveClientProtocol):
    """In‑memory implementation of :class:`ArchiveClientProtocol` for testing.

    Generated archive IDs always start with ``"ab-fake-"``.
    """

    def __init__(self) -> None:
        self._archives: dict[str, dict] = {}
        self._counter: int = 0

    # -- protocol implementation -------------------------------------------

    def submit_archive(self, url: str) -> str:
        self._counter += 1
        archive_id = f"ab-fake-{self._counter}"
        self._archives[archive_id] = {
            "id": archive_id,
            "url": url,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }
        return archive_id

    def get_archive(self, archive_id: str) -> dict | None:
        return self._archives.get(archive_id)

    def check_status(self, archive_id: str) -> str:
        entry = self._archives.get(archive_id)
        if entry is None:
            return "failed"
        return entry.get("status", "pending")

    # -- test helpers ------------------------------------------------------

    def set_status(self, archive_id: str, status: str) -> None:
        """Override the status for testing purposes."""
        if archive_id in self._archives:
            self._archives[archive_id]["status"] = status

    def reset(self) -> None:
        """Clear all stored archives and counter."""
        self._archives.clear()
        self._counter = 0
