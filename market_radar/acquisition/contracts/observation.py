from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .timestamps import FiveTimestamps, TimestampEvidence, TimestampQuality


class ObservationStatus(str, Enum):
    VALID = "valid"
    PARTIAL = "partial"
    CONFLICTING = "conflicting"
    STALE = "stale"
    RETRACTED = "retracted"
    PARSE_FAILED = "parse_failed"
    UNSUPPORTED = "unsupported"


@dataclass
class NormalizedObservation:
    """Acquisition-layer output — NO bullish/bearish/signal scores."""
    observation_id: str = ""
    observation_version: str = "1.0.0"
    source_id: str = ""
    source_event_id: str = ""
    source_role: str = ""
    authority_tier: str = ""
    independence_group: str = ""
    title: str = ""
    summary: str = ""
    body_text: str = ""
    language: str = ""
    entities: tuple[str, ...] = field(default_factory=tuple)
    assets: tuple[str, ...] = field(default_factory=tuple)
    jurisdictions: tuple[str, ...] = field(default_factory=tuple)
    event_family_hint: str = ""
    content_type: str = ""
    timestamps: FiveTimestamps = field(default_factory=lambda: FiveTimestamps(
        first_seen_at=TimestampEvidence(quality=TimestampQuality.RETRIEVAL_ONLY),
        retrieved_at=TimestampEvidence(quality=TimestampQuality.RETRIEVAL_ONLY),
    ))
    raw_document_ref: str = ""
    archive_ref: str = ""
    content_hash: str = ""
    revision_id: str = ""
    extraction_method: str = ""
    extraction_quality: str = "pending"
    text_length: int = 0
    limitations: tuple[str, ...] = field(default_factory=tuple)
    status: ObservationStatus = ObservationStatus.VALID

    def to_dict(self) -> dict:
        return {
            "observation_id": self.observation_id,
            "observation_version": self.observation_version,
            "source_id": self.source_id,
            "source_event_id": self.source_event_id,
            "source_role": self.source_role,
            "authority_tier": self.authority_tier,
            "independence_group": self.independence_group,
            "title": self.title,
            "summary": self.summary,
            "body_text": self.body_text,
            "language": self.language,
            "entities": list(self.entities),
            "assets": list(self.assets),
            "jurisdictions": list(self.jurisdictions),
            "event_family_hint": self.event_family_hint,
            "content_type": self.content_type,
            "timestamps": self.timestamps.to_dict(),
            "raw_document_ref": self.raw_document_ref,
            "archive_ref": self.archive_ref,
            "content_hash": self.content_hash,
            "revision_id": self.revision_id,
            "extraction_method": self.extraction_method,
            "extraction_quality": self.extraction_quality,
            "text_length": self.text_length,
            "limitations": list(self.limitations),
            "status": self.status.value,
        }
