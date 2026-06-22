"""ConflictRegistry — in-memory registry of ClaimConflict objects."""

from __future__ import annotations

from typing import Optional

from research.intelligence.contracts.conflict import ClaimConflict
from research.intelligence.contracts.common import ConflictType, ResolutionStatus


class ConflictRegistry:
    """In-memory registry for managing claim conflicts."""

    def __init__(self) -> None:
        self._records: dict[str, ClaimConflict] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, conflict: ClaimConflict) -> None:
        """Register a new conflict."""
        self._records[conflict.conflict_id] = conflict

    def get(self, conflict_id: str) -> Optional[ClaimConflict]:
        """Retrieve a conflict by id, or None."""
        return self._records.get(conflict_id)

    def remove(self, conflict_id: str) -> bool:
        """Remove a conflict. Returns True if it existed."""
        return self._records.pop(conflict_id, None) is not None

    def update(self, conflict: ClaimConflict) -> None:
        """Replace the stored conflict for *conflict.conflict_id*."""
        self._records[conflict.conflict_id] = conflict

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[ClaimConflict]:
        """Return all registered conflicts."""
        return list(self._records.values())

    def find_by_claim(self, claim_id: str) -> list[ClaimConflict]:
        """Return conflicts involving a specific claim (as left or right side)."""
        return [
            c for c in self._records.values()
            if c.left_claim_id == claim_id or c.right_claim_id == claim_id
        ]

    def find_by_type(self, conflict_type: ConflictType) -> list[ClaimConflict]:
        """Return conflicts of a specific type."""
        return [c for c in self._records.values() if c.conflict_type == conflict_type]

    def unresolved(self) -> list[ClaimConflict]:
        """Return conflicts that have not yet been resolved."""
        return [c for c in self._records.values() if c.resolution_status == ResolutionStatus.UNRESOLVED]

    def count(self) -> int:
        """Return the number of registered conflicts."""
        return len(self._records)
