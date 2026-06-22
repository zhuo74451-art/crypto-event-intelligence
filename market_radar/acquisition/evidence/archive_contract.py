"""Archive protocol ABC and a fake in-memory implementation."""

from __future__ import annotations

import abc
import dataclasses
import hashlib
import time
import uuid


# ---------------------------------------------------------------------------
# Simple value objects
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class ArchiveResult:
    archive_id: str
    original_url: str
    archived_at: str   # ISO-8601 UTC string
    content_hash: str
    status: str
    error: str | None = None


@dataclasses.dataclass
class ArchiveFailure:
    archive_id: str
    reason: str
    timestamp: str     # ISO-8601 UTC string


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class ArchiveClientProtocol(abc.ABC):
    """Interface for archive back-ends."""

    @abc.abstractmethod
    def archive(self, url: str, content: bytes, content_type: str) -> str:
        """Persist *content* under *url* and return an archive identifier."""
        ...

    @abc.abstractmethod
    def retrieve(self, archive_id: str) -> bytes | None:
        """Return previously archived content, or *None* if missing."""
        ...

    @abc.abstractmethod
    def status(self, archive_id: str) -> str:
        """Return a human-readable status string for the given archive."""
        ...


# ---------------------------------------------------------------------------
# Fake in-memory client (useful for testing / local development)
# ---------------------------------------------------------------------------

class FakeArchiveClient(ArchiveClientProtocol):
    """Dictionary-backed *ArchiveClientProtocol* returning fake IDs."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}   # archive_id -> {content, url, content_type, status}

    def archive(self, url: str, content: bytes, content_type: str) -> str:
        archive_id = f"fake-{uuid.uuid4().hex}"
        self._store[archive_id] = {
            "content": content,
            "url": url,
            "content_type": content_type,
            "status": "archived",
        }
        return archive_id

    def retrieve(self, archive_id: str) -> bytes | None:
        entry = self._store.get(archive_id)
        return entry["content"] if entry else None

    def status(self, archive_id: str) -> str:
        entry = self._store.get(archive_id)
        return entry["status"] if entry else "not_found"
