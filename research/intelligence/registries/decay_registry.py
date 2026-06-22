"""DecayRegistry — in-memory registry of KnowledgeDecayRecord objects."""

from __future__ import annotations

from typing import Optional

from research.intelligence.contracts.knowledge_decay import KnowledgeDecayRecord
from research.intelligence.contracts.common import DecayRisk


class DecayRegistry:
    """In-memory registry for managing knowledge decay records."""

    def __init__(self) -> None:
        self._records: dict[str, KnowledgeDecayRecord] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, record: KnowledgeDecayRecord) -> None:
        """Register a new decay record."""
        self._records[record.decay_id] = record

    def get(self, decay_id: str) -> Optional[KnowledgeDecayRecord]:
        """Retrieve a decay record by id, or None."""
        return self._records.get(decay_id)

    def remove(self, decay_id: str) -> bool:
        """Remove a decay record. Returns True if it existed."""
        return self._records.pop(decay_id, None) is not None

    def update(self, record: KnowledgeDecayRecord) -> None:
        """Replace the stored record for *record.decay_id*."""
        self._records[record.decay_id] = record

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[KnowledgeDecayRecord]:
        """Return all registered decay records."""
        return list(self._records.values())

    def find_by_claim(self, claim_id: str) -> list[KnowledgeDecayRecord]:
        """Return decay records affecting a specific claim."""
        return [r for r in self._records.values() if claim_id in r.claim_ids]

    def find_by_risk(self, risk: DecayRisk) -> list[KnowledgeDecayRecord]:
        """Return decay records with a specific risk level."""
        return [r for r in self._records.values() if r.decay_risk == risk]

    def high_risk(self) -> list[KnowledgeDecayRecord]:
        """Return records with high decay risk."""
        return [r for r in self._records.values() if r.decay_risk == DecayRisk.HIGH]

    def count(self) -> int:
        """Return the number of registered decay records."""
        return len(self._records)
