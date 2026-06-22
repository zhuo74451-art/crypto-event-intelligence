"""HypothesisRegistry — in-memory registry of ResearchHypothesis objects."""

from __future__ import annotations

from typing import Optional

from research.intelligence.contracts.hypothesis import ResearchHypothesis
from research.intelligence.contracts.common import HypothesisStatus


class HypothesisRegistry:
    """In-memory registry for managing research hypotheses."""

    def __init__(self) -> None:
        self._records: dict[str, ResearchHypothesis] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(self, hypothesis: ResearchHypothesis) -> None:
        """Register a new hypothesis."""
        self._records[hypothesis.hypothesis_id] = hypothesis

    def get(self, hypothesis_id: str) -> Optional[ResearchHypothesis]:
        """Retrieve a hypothesis by id, or None."""
        return self._records.get(hypothesis_id)

    def remove(self, hypothesis_id: str) -> bool:
        """Remove a hypothesis. Returns True if it existed."""
        return self._records.pop(hypothesis_id, None) is not None

    def update(self, hypothesis: ResearchHypothesis) -> None:
        """Replace the stored hypothesis for *hypothesis.hypothesis_id*."""
        self._records[hypothesis.hypothesis_id] = hypothesis

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_all(self) -> list[ResearchHypothesis]:
        """Return all registered hypotheses."""
        return list(self._records.values())

    def find_by_status(self, status: HypothesisStatus) -> list[ResearchHypothesis]:
        """Return hypotheses with a specific status."""
        return [h for h in self._records.values() if h.status == status]

    def find_active(self) -> list[ResearchHypothesis]:
        """Return hypotheses that are still under active investigation."""
        return [
            h for h in self._records.values()
            if h.status in (
                HypothesisStatus.PROPOSED,
                HypothesisStatus.SPECIFICATION_READY,
                HypothesisStatus.VALIDATION_READY,
                HypothesisStatus.UNDER_TEST,
            )
        ]

    def count(self) -> int:
        """Return the number of registered hypotheses."""
        return len(self._records)
