from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TimestampQuality(str, Enum):
    EXPLICIT_SOURCE = "explicit_source"
    STRUCTURED_METADATA = "structured_metadata"
    HTTP_HEADER = "http_header"
    INFERRED_FROM_CONTENT = "inferred_from_content"
    RETRIEVAL_ONLY = "retrieval_only"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


class TimestampAnomaly(str, Enum):
    NONE = "none"
    BEFORE_1970 = "before_1970"
    FAR_FUTURE = "far_future"
    BEFORE_PUBLISHED = "before_published"
    AFTER_RETRIEVED = "after_retrieved"
    CONFLICTS_WITH_OTHER = "conflicts_with_other"
    MISSING_REASON = "missing_reason"
    SUSPICIOUS_ACCURACY = "suspicious_accuracy"


@dataclass(frozen=True)
class TimestampEvidence:
    value: datetime | None = None
    quality: TimestampQuality = TimestampQuality.UNKNOWN
    anomaly: TimestampAnomaly = TimestampAnomaly.NONE
    source_field: str = ""
    missing_reason: str = ""

    def is_present(self) -> bool:
        return self.value is not None

    def to_dict(self) -> dict:
        return {
            "value": self.value.isoformat() if self.value else None,
            "quality": self.quality.value,
            "anomaly": self.anomaly.value,
            "source_field": self.source_field,
            "missing_reason": self.missing_reason,
        }


@dataclass(frozen=True)
class FiveTimestamps:
    """published_at, effective_at, updated_at, first_seen_at, retrieved_at"""
    published_at: TimestampEvidence = field(default_factory=TimestampEvidence)
    effective_at: TimestampEvidence = field(default_factory=TimestampEvidence)
    updated_at: TimestampEvidence = field(default_factory=TimestampEvidence)
    first_seen_at: TimestampEvidence = field(default_factory=lambda: TimestampEvidence(quality=TimestampQuality.RETRIEVAL_ONLY))
    retrieved_at: TimestampEvidence = field(default_factory=lambda: TimestampEvidence(quality=TimestampQuality.RETRIEVAL_ONLY))

    def validate(self) -> list[str]:
        warnings = []
        if self.first_seen_at.is_present() and self.retrieved_at.is_present():
            if self.first_seen_at.value and self.retrieved_at.value:
                if self.first_seen_at.value > self.retrieved_at.value:
                    warnings.append("first_seen_at must not be later than retrieved_at")
        return warnings

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in {
            "published_at": self.published_at, "effective_at": self.effective_at,
            "updated_at": self.updated_at, "first_seen_at": self.first_seen_at,
            "retrieved_at": self.retrieved_at,
        }.items()}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
