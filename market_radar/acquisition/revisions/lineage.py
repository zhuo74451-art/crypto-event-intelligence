from __future__ import annotations
from datetime import datetime
from ..contracts.revision import RevisionRecord, RevisionLineage


class LineageTracker:
    """Track revision lineages across multiple sources and observations."""

    def __init__(self):
        self._lineages: dict[tuple[str, str], RevisionLineage] = {}

    def add_revision(self, revision: RevisionRecord) -> None:
        key = (revision.source_id, revision.observation_id)
        if key not in self._lineages:
            self._lineages[key] = RevisionLineage(
                source_id=revision.source_id,
                observation_id=revision.observation_id,
            )
        self._lineages[key].add_revision(revision)

    def get_lineage(self, source_id: str, observation_id: str) -> RevisionLineage:
        key = (source_id, observation_id)
        return self._lineages.get(key, RevisionLineage(source_id=source_id, observation_id=observation_id))

    def latest_revision(self, source_id: str, observation_id: str) -> RevisionRecord | None:
        lineage = self.get_lineage(source_id, observation_id)
        return lineage.latest_revision()

    def revisions_as_of(self, source_id: str, observation_id: str, cutoff: datetime) -> list[RevisionRecord]:
        lineage = self.get_lineage(source_id, observation_id)
        return lineage.revisions_as_of(cutoff)
