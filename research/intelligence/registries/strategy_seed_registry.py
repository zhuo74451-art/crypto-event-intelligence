"""StrategySeedRegistry — in-memory registry of StrategySeed objects."""

from __future__ import annotations

from typing import Optional

from research.intelligence.contracts.strategy_seed import StrategySeed
from research.intelligence.contracts.common import StrategySeedStatus


class StrategySeedRegistry:
    """In-memory registry for managing strategy seeds."""

    def __init__(self) -> None:
        self._records: dict[str, StrategySeed] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, seed: StrategySeed) -> None:
        """Register a new strategy seed."""
        self._records[seed.strategy_seed_id] = seed

    def get(self, strategy_seed_id: str) -> Optional[StrategySeed]:
        """Retrieve a seed by id, or None."""
        return self._records.get(strategy_seed_id)

    def remove(self, strategy_seed_id: str) -> bool:
        """Remove a seed. Returns True if it existed."""
        return self._records.pop(strategy_seed_id, None) is not None

    def update(self, seed: StrategySeed) -> None:
        """Replace the stored seed for *seed.strategy_seed_id*."""
        self._records[seed.strategy_seed_id] = seed

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[StrategySeed]:
        """Return all registered seeds."""
        return list(self._records.values())

    def find_by_status(self, status: StrategySeedStatus) -> list[StrategySeed]:
        """Return seeds with a specific research status."""
        return [s for s in self._records.values() if s.research_status == status]

    def find_by_domain(self, domain: str) -> list[StrategySeed]:
        """Return seeds in a specific domain."""
        return [s for s in self._records.values() if domain in s.domains]

    def find_research_ready(self) -> list[StrategySeed]:
        """Return seeds that are research-ready."""
        return [s for s in self._records.values() if s.research_status == StrategySeedStatus.RESEARCH_READY]

    def count(self) -> int:
        """Return the number of registered seeds."""
        return len(self._records)
