"""Evidence — local file-based evidence storage and archive protocols."""

from .archive_contract import (
    ArchiveClientProtocol,
    ArchiveFailure,
    ArchiveResult,
    FakeArchiveClient,
)
from .hashing import compute_content_hash, compute_identity_hash, verify_hash
from .local_evidence_store import LocalEvidenceStore
from .manifest import EvidenceManifest


class ContentHashing:
    """Static-method wrapper for the hashing utilities."""

    @staticmethod
    def compute_content_hash(raw_bytes: bytes) -> str:
        return compute_content_hash(raw_bytes)

    @staticmethod
    def compute_identity_hash(normalized_text: str) -> str:
        return compute_identity_hash(normalized_text)

    @staticmethod
    def verify_hash(data: bytes, expected: str) -> bool:
        return verify_hash(data, expected)


__all__ = [
    "ContentHashing",
    "ArchiveClientProtocol",
    "ArchiveResult",
    "ArchiveFailure",
    "FakeArchiveClient",
    "LocalEvidenceStore",
    "EvidenceManifest",
]
