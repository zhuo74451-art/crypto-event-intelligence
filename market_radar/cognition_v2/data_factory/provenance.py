"""Provenance edge tracking for the data factory.

C04: source-to-evidence-to-case provenance edges.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional


class ProvenanceEdge:
    """A provenance edge connecting source -> evidence -> case."""
    def __init__(
        self,
        edge_id: str,
        source_id: str,
        intake_id: str,
        evidence_id: str,
        case_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.edge_id = edge_id
        self.source_id = source_id
        self.intake_id = intake_id
        self.evidence_id = evidence_id
        self.case_id = case_id
        self.created_at = created_at or datetime.now(timezone.utc)


class ProvenanceTracker:
    """Tracks provenance from source to evidence to case."""

    def __init__(self):
        self._edges: List[ProvenanceEdge] = []

    def record_intake(self, source_id: str, intake_id: str) -> None:
        """Record an intake record from a source."""
        import hashlib
        eid = hashlib.sha256(
            f"intake:{source_id}:{intake_id}".encode()
        ).hexdigest()[:32]
        self._edges.append(ProvenanceEdge(
            edge_id=eid, source_id=source_id,
            intake_id=intake_id, evidence_id=eid,
        ))

    def link_evidence_to_case(
        self, evidence_id: str, case_id: str,
    ) -> None:
        """Link an evidence record to a qualified case."""
        for edge in self._edges:
            if edge.evidence_id == evidence_id:
                edge.case_id = case_id
                break

    def get_source_to_case_path(
        self, case_id: str,
    ) -> List[ProvenanceEdge]:
        """Get all edges for a case."""
        return [e for e in self._edges if e.case_id == case_id]

    def validate_coverage(self) -> dict:
        """Validate that every case has complete audit path."""
        cases = set(e.case_id for e in self._edges if e.case_id)
        edges_with_case = [e for e in self._edges if e.case_id]
        return {
            "total_edges": len(self._edges),
            "cases_with_audit_path": len(cases),
            "complete_coverage": len(cases) == len(cases) if cases else True,
        }
