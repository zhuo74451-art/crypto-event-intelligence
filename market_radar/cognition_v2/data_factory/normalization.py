"""Deterministic normalization and point-in-time authority.

D05: Normalize source records into canonical evidence with explicit
point-in-time fields.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional

from market_radar.cognition_v2.data_factory.contracts import (
    NormalizedEvidenceRecord,
    RawIntakeRecord,
    SCHEMA_VERSION,
)


class EvidenceNormalizer:
    """Deterministic normalizer for raw intake records."""

    def normalize(
        self,
        record: RawIntakeRecord,
        authority: str = "unknown",
        fact_permission: str = "unknown",
        publication_time: Optional[datetime] = None,
        effective_time: Optional[datetime] = None,
        first_seen_at: Optional[datetime] = None,
        assessment_time: Optional[datetime] = None,
    ) -> NormalizedEvidenceRecord:
        """Normalize a raw intake record into canonical evidence."""
        retrieval_time = record.retrieved_at
        first_seen = first_seen_at or retrieval_time

        evidence = NormalizedEvidenceRecord(
            evidence_id="",
            source_id=record.source_id,
            source_url=record.source_url,
            authority=authority,
            fact_permission=fact_permission,
            publication_time=publication_time,
            effective_time=effective_time,
            first_seen_at=first_seen,
            retrieval_time=retrieval_time,
            assessment_time=assessment_time,
            normalized_fact=record.raw_body[:1000] if record.raw_body else "",
            short_excerpt=record.raw_body[:500] if record.raw_body else "",
            parser_version=record.parser_version,
        )
        evidence.content_hash = evidence.compute_content_hash()
        evidence.evidence_id = hashlib.sha256(
            json.dumps({
                "source": evidence.source_id,
                "hash": evidence.content_hash,
                "first_seen": evidence.first_seen_at.isoformat() if evidence.first_seen_at else None,
            }, sort_keys=True, default=str).encode()
        ).hexdigest()[:32]
        return evidence


def point_in_time_available(
    evidence: NormalizedEvidenceRecord,
    cutoff: datetime,
) -> bool:
    """Check if evidence is available at a point-in-time cutoff.
    
    availability_time = max(first_seen_at, retrieval_time)
    Publication or effective time alone never makes later-retrieved
    information available earlier.
    """
    if evidence.first_seen_at is None or evidence.retrieval_time is None:
        return False
    availability = max(evidence.first_seen_at, evidence.retrieval_time)
    return availability <= cutoff
