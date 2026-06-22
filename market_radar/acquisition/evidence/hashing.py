"""Content hashing utilities — deterministic SHA-256 helpers."""

import hashlib
import re


def compute_content_hash(raw_bytes: bytes) -> str:
    """SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(raw_bytes).hexdigest()


def compute_identity_hash(normalized_text: str) -> str:
    """SHA-256 hex digest of whitespace-normalized text.

    Normalization: strip, collapse all runs of whitespace (spaces,
    newlines, tabs) into a single space, strip again.
    """
    collapsed = re.sub(r'\s+', ' ', normalized_text.strip()).strip()
    return hashlib.sha256(collapsed.encode('utf-8')).hexdigest()


def verify_hash(data: bytes, expected: str) -> bool:
    """Compare SHA-256 hex digest of *data* against *expected*."""
    return compute_content_hash(data) == expected
