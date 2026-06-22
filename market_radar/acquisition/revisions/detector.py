from __future__ import annotations
from typing import Optional
from ..contracts.revision import RevisionType


class RevisionDetector:
    """Detect revision type by comparing old and new hashes/metadata."""

    def detect(
        self,
        prev_content_hash: str | None,
        curr_content_hash: str,
        prev_identity_hash: str | None,
        curr_identity_hash: str,
        prev_metadata: dict | None = None,
        curr_metadata: dict | None = None,
        prev_is_deleted: bool = False,
    ) -> tuple[RevisionType, str]:
        if prev_content_hash is None:
            return RevisionType.FIRST_SEEN, "First observation"

        if not curr_content_hash or not curr_identity_hash:
            return RevisionType.DELETED, "Content or identity hash is empty"

        if prev_is_deleted:
            return RevisionType.RESTORED, "Content restored after deletion"

        if prev_content_hash != curr_content_hash:
            return RevisionType.CONTENT_CHANGED, "Content hash differs"

        if prev_identity_hash != curr_identity_hash:
            return RevisionType.CONTENT_CHANGED, "Identity hash differs"

        if prev_metadata is not None and curr_metadata is not None:
            if prev_metadata != curr_metadata:
                return RevisionType.METADATA_CHANGED, "Metadata changed but content same"

        return RevisionType.NO_CHANGE, "No change detected"
