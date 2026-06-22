"""Evidence manifest data structure."""

from __future__ import annotations

import dataclasses
import time
import uuid


@dataclasses.dataclass
class EvidenceManifest:
    """Describes a set of evidence entries at a point in time."""

    manifest_id: str
    created_at: str          # ISO-8601 UTC string
    source_id: str
    entries: list[dict]
    total_size: int
    entry_count: int

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dictionary."""
        return {
            "manifest_id": self.manifest_id,
            "created_at": self.created_at,
            "source_id": self.source_id,
            "entries": self.entries,
            "total_size": self.total_size,
            "entry_count": self.entry_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EvidenceManifest:
        """Build an instance from a dictionary (complement of *to_dict*)."""
        return cls(
            manifest_id=d["manifest_id"],
            created_at=d["created_at"],
            source_id=d["source_id"],
            entries=d["entries"],
            total_size=d["total_size"],
            entry_count=d["entry_count"],
        )
