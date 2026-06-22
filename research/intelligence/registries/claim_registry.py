"""ClaimRegistry — in-memory registry of ResearchClaim objects."""

from __future__ import annotations

from typing import Optional

from research.intelligence.contracts.claim import ResearchClaim
from research.intelligence.contracts.common import ClaimStatus, ClaimType


class ClaimRegistry:
    """In-memory registry for managing claims."""

    def __init__(self) -> None:
        self._records: dict[str, ResearchClaim] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, claim: ResearchClaim) -> None:
        """Register a new claim."""
        self._records[claim.claim_id] = claim

    def get(self, claim_id: str) -> Optional[ResearchClaim]:
        """Retrieve a claim by id, or None."""
        return self._records.get(claim_id)

    def remove(self, claim_id: str) -> bool:
        """Remove a claim. Returns True if it existed."""
        return self._records.pop(claim_id, None) is not None

    def update(self, claim: ResearchClaim) -> None:
        """Replace the stored claim for *claim.claim_id*."""
        self._records[claim.claim_id] = claim

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[ResearchClaim]:
        """Return all registered claims."""
        return list(self._records.values())

    def find_by_source(self, source_record_id: str) -> list[ResearchClaim]:
        """Return claims linked to a specific source record."""
        return [
            c for c in self._records.values()
            if source_record_id in c.source_record_ids or c.primary_source_record_id == source_record_id
        ]

    def find_by_type(self, claim_type: ClaimType) -> list[ResearchClaim]:
        """Return claims of a specific type."""
        return [c for c in self._records.values() if c.claim_type == claim_type]

    def find_by_status(self, status: ClaimStatus) -> list[ResearchClaim]:
        """Return claims with a specific status."""
        return [c for c in self._records.values() if c.status == status]

    def null_results(self) -> list[ResearchClaim]:
        """Return claims that are null results."""
        return [c for c in self._records.values() if c.claim_type == ClaimType.NULL_RESULT]

    def retracted(self) -> list[ResearchClaim]:
        """Return claims that have been retracted."""
        return [c for c in self._records.values() if c.status == ClaimStatus.RETRACTED]

    def find_by_domain(self, domain: str) -> list[ResearchClaim]:
        """Return claims in a specific domain."""
        return [c for c in self._records.values() if domain in c.domains]

    def count(self) -> int:
        """Return the number of registered claims."""
        return len(self._records)
