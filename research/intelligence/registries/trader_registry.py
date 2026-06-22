"""TraderRegistry — in-memory registry of TraderProfile objects."""

from __future__ import annotations

from typing import Optional

from research.intelligence.contracts.trader_profile import TraderProfile
from research.intelligence.contracts.common import TraderVerificationStatus


class TraderRegistry:
    """In-memory registry for managing trader profiles."""

    def __init__(self) -> None:
        self._records: dict[str, TraderProfile] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, profile: TraderProfile) -> None:
        """Register a new trader profile."""
        self._records[profile.trader_profile_id] = profile

    def get(self, trader_profile_id: str) -> Optional[TraderProfile]:
        """Retrieve a trader profile by id, or None."""
        return self._records.get(trader_profile_id)

    def remove(self, trader_profile_id: str) -> bool:
        """Remove a trader profile. Returns True if it existed."""
        return self._records.pop(trader_profile_id, None) is not None

    def update(self, profile: TraderProfile) -> None:
        """Replace the stored profile for *profile.trader_profile_id*."""
        self._records[profile.trader_profile_id] = profile

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[TraderProfile]:
        """Return all registered trader profiles."""
        return list(self._records.values())

    def find_by_name(self, name: str) -> list[TraderProfile]:
        """Return profiles whose display_name contains *name* (case-insensitive)."""
        lower = name.lower()
        return [p for p in self._records.values() if lower in p.display_name.lower()]

    def find_by_verification(self, status: TraderVerificationStatus) -> list[TraderProfile]:
        """Return profiles with a specific verification status."""
        return [p for p in self._records.values() if p.source_verification_status == status]

    def with_unverified_performance(self) -> list[TraderProfile]:
        """Return profiles that have unverified performance claims."""
        return [p for p in self._records.values() if p.unverified_performance_claims]

    def count(self) -> int:
        """Return the number of registered trader profiles."""
        return len(self._records)
