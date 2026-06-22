from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RevisionType(str, Enum):
    FIRST_SEEN = "first_seen"
    NO_CHANGE = "no_change"
    CONTENT_CHANGED = "content_changed"
    METADATA_CHANGED = "metadata_changed"
    CORRECTED = "corrected"
    RETRACTED = "retracted"
    DELETED = "deleted"
    RESTORED = "restored"
    REDIRECTED = "redirected"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class RevisionRecord:
    revision_id: str = ""
    source_id: str = ""
    observation_id: str = ""
    revision_type: RevisionType = RevisionType.FIRST_SEEN
    previous_revision_id: str = ""
    content_hash: str = ""
    identity_hash: str = ""
    previous_content_hash: str = ""
    raw_document_ref: str = ""
    first_seen_at: str = ""
    change_summary: str = ""
    retracted: bool = False
    retraction_revision_id: str = ""

    def to_dict(self) -> dict:
        return {
            "revision_id": self.revision_id, "source_id": self.source_id,
            "observation_id": self.observation_id,
            "revision_type": self.revision_type.value,
            "previous_revision_id": self.previous_revision_id,
            "content_hash": self.content_hash, "identity_hash": self.identity_hash,
            "previous_content_hash": self.previous_content_hash,
            "raw_document_ref": self.raw_document_ref,
            "first_seen_at": self.first_seen_at,
            "change_summary": self.change_summary,
            "retracted": self.retracted,
            "retraction_revision_id": self.retraction_revision_id,
        }


@dataclass
class RevisionLineage:
    source_id: str = ""
    observation_id: str = ""
    revisions: list[RevisionRecord] = field(default_factory=list)

    def add_revision(self, rev: RevisionRecord) -> None:
        self.revisions.append(rev)

    def latest_revision(self) -> RevisionRecord | None:
        return self.revisions[-1] if self.revisions else None

    def revisions_as_of(self, cutoff: datetime) -> list[RevisionRecord]:
        cutoff_s = cutoff.isoformat()
        return [r for r in self.revisions if r.first_seen_at and r.first_seen_at <= cutoff_s]

    def effective_as_of(self, cutoff: datetime) -> RevisionRecord | None:
        known = self.revisions_as_of(cutoff)
        return known[-1] if known else None
