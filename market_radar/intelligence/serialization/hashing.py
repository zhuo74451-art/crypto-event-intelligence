"""Hashing utilities for intelligence objects.

Three distinct hash types:
- identity_hash: Stable hash of canonical identity fields
- content_hash: Hash of full content (canonical JSON)
- revision_hash: Hash excluding metadata (created_at, updated_at)
"""

from __future__ import annotations

import hashlib
from typing import Any

from .canonical_json import canonical_json


def compute_identity_hash(namespace: str, canonical_payload: str) -> str:
    """Compute a stable identity hash.

    Args:
        namespace: A prefix/namespace for the object type (e.g. "evidence", "event").
        canonical_payload: The canonical string representation of identity fields.

    Returns:
        A 32-character hex string.
    """
    raw = f"{namespace}:{canonical_payload}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def compute_content_hash(data: dict[str, Any]) -> str:
    """Compute a content hash from canonical JSON."""
    raw = canonical_json(data)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def compute_revision_hash(data: dict[str, Any]) -> str:
    """Compute a revision hash (excludes metadata timestamps)."""
    excluded = {"created_at", "updated_at", "revision_hash", "as_of_time"}
    filtered = {k: v for k, v in data.items() if k not in excluded}
    return compute_content_hash(filtered)


def hash_field(value: Any) -> str:
    """Hash a single field value for deterministic referencing."""
    raw = str(value)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
