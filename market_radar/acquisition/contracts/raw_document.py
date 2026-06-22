from __future__ import annotations
from dataclasses import dataclass, field
from .timestamps import FiveTimestamps, TimestampEvidence, TimestampQuality, TimestampAnomaly


@dataclass
class RawDocument:
    raw_document_id: str = ""
    source_id: str = ""
    source_event_id: str = ""
    canonical_url: str = ""
    retrieved_url: str = ""
    http_status: int = 0
    content_type: str = ""
    encoding: str = ""
    timestamps: FiveTimestamps = field(default_factory=lambda: FiveTimestamps(
        first_seen_at=TimestampEvidence(quality=TimestampQuality.RETRIEVAL_ONLY),
        retrieved_at=TimestampEvidence(quality=TimestampQuality.RETRIEVAL_ONLY),
    ))
    headers_subset: dict[str, str] = field(default_factory=dict)
    raw_payload_ref: str = ""
    payload_size: int = 0
    content_hash: str = ""
    identity_hash: str = ""
    extraction_status: str = "pending"
    revision_status: str = "pending"
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "raw_document_id": self.raw_document_id,
            "source_id": self.source_id,
            "source_event_id": self.source_event_id,
            "canonical_url": self.canonical_url,
            "retrieved_url": self.retrieved_url,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "encoding": self.encoding,
            "timestamps": self.timestamps.to_dict(),
            "headers_subset": dict(self.headers_subset),
            "raw_payload_ref": self.raw_payload_ref,
            "payload_size": self.payload_size,
            "content_hash": self.content_hash,
            "identity_hash": self.identity_hash,
            "extraction_status": self.extraction_status,
            "revision_status": self.revision_status,
            "error": self.error,
        }
