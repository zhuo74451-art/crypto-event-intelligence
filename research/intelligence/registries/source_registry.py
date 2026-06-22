"""SourceRegistry — in-memory registry of ResearchSourceRecord objects."""

from __future__ import annotations

from typing import Optional

from research.intelligence.contracts.source_record import ResearchSourceRecord


class SourceRegistry:
    """In-memory registry for managing source records."""

    def __init__(self) -> None:
        self._records: dict[str, ResearchSourceRecord] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, record: ResearchSourceRecord) -> None:
        """Register a new source record."""
        self._records[record.source_record_id] = record

    def get(self, source_record_id: str) -> Optional[ResearchSourceRecord]:
        """Retrieve a source record by id, or None."""
        return self._records.get(source_record_id)

    def remove(self, source_record_id: str) -> bool:
        """Remove a source record. Returns True if it existed."""
        return self._records.pop(source_record_id, None) is not None

    def update(self, record: ResearchSourceRecord) -> None:
        """Replace the stored record for *record.source_record_id*."""
        self._records[record.source_record_id] = record

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[ResearchSourceRecord]:
        """Return all registered source records."""
        return list(self._records.values())

    def find_by_title(self, title: str) -> list[ResearchSourceRecord]:
        """Return records whose title contains *title* (case-insensitive)."""
        lower = title.lower()
        return [r for r in self._records.values() if lower in r.title.lower()]

    def find_by_domain(self, domain: str) -> list[ResearchSourceRecord]:
        """Return records that mention a specific domain."""
        return [r for r in self._records.values() if domain in r.domains]

    def count(self) -> int:
        """Return the number of registered records."""
        return len(self._records)
