"""GapRegistry — in-memory registry of KnowledgeGap objects."""

from __future__ import annotations

from typing import Optional

from research.intelligence.contracts.knowledge_gap import KnowledgeGap
from research.intelligence.contracts.common import GapStatus, Priority
from research.intelligence.contracts.errors import knowledge_gap_duplicate


class GapRegistry:
    """In-memory registry for managing knowledge gaps."""

    def __init__(self) -> None:
        self._records: dict[str, KnowledgeGap] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, gap: KnowledgeGap) -> None:
        """Register a new knowledge gap. Rejects duplicates by gap_id."""
        if gap.gap_id in self._records:
            raise knowledge_gap_duplicate(gap.gap_id)
        self._records[gap.gap_id] = gap

    def get(self, gap_id: str) -> Optional[KnowledgeGap]:
        """Retrieve a gap by id, or None."""
        return self._records.get(gap_id)

    def remove(self, gap_id: str) -> bool:
        """Remove a gap. Returns True if it existed."""
        return self._records.pop(gap_id, None) is not None

    def update(self, gap: KnowledgeGap) -> None:
        """Replace the stored gap for *gap.gap_id*."""
        self._records[gap.gap_id] = gap

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[KnowledgeGap]:
        """Return all registered gaps."""
        return list(self._records.values())

    def find_by_domain(self, domain: str) -> list[KnowledgeGap]:
        """Return gaps for a specific domain."""
        return [g for g in self._records.values() if domain in g.domains]

    def find_by_status(self, status: GapStatus) -> list[KnowledgeGap]:
        """Return gaps with a specific status."""
        return [g for g in self._records.values() if g.status == status]

    def open_gaps(self) -> list[KnowledgeGap]:
        """Return gaps that are still open."""
        return [g for g in self._records.values() if g.status == GapStatus.OPEN]

    def by_priority(self) -> list[KnowledgeGap]:
        """Return gaps sorted by priority (P0 first)."""
        order = {Priority.P0: 0, Priority.P1: 1, Priority.P2: 2, Priority.P3: 3}
        return sorted(self._records.values(), key=lambda g: order.get(g.priority, 99))

    def count(self) -> int:
        """Return the number of registered gaps."""
        return len(self._records)
