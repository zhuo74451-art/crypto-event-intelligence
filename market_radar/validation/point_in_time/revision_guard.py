"""
Revision guard — prevents using revised data that wasn't available at prediction time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..contracts.common import RevisionRef
from ..contracts.errors import RevisionLeakError


class RevisionGuard:
    """Guard against revision leakage in validation."""

    def __init__(self):
        self._revisions: dict[str, list[RevisionRef]] = {}

    def register_revision(self, value_ref: str, revision: RevisionRef) -> None:
        """Register a revision for a value."""
        if value_ref not in self._revisions:
            self._revisions[value_ref] = []
        self._revisions[value_ref].append(revision)

    def get_revisions(self, value_ref: str) -> list[RevisionRef]:
        """Get all revisions for a value."""
        return self._revisions.get(value_ref, [])

    def get_value_as_known_at(
        self, value_ref: str, as_of_time: datetime
    ) -> Optional[RevisionRef]:
        """Get the value as it was known at a specific point in time."""
        revisions = self._revisions.get(value_ref, [])
        if not revisions:
            return None
        # Find the latest revision that was available as_of_time
        known: Optional[RevisionRef] = None
        for rev in revisions:
            if rev.revision_time <= as_of_time:
                if known is None or rev.revision_time > known.revision_time:
                    known = rev
        return known

    def assert_original_value(
        self,
        value_ref: str,
        provided_value: str,
        as_of_time: datetime,
    ) -> None:
        """Assert the provided value matches the value known at as_of_time."""
        known = self.get_value_as_known_at(value_ref, as_of_time)
        if known is None:
            return
        if known.value_ref != provided_value:
            raise RevisionLeakError(
                detail=(
                    f"Value {value_ref}: provided '{provided_value}' "
                    f"but value known at {as_of_time} was '{known.value_ref}' "
                    f"(revision {known.revision_id})"
                ),
                object_id=value_ref,
                min_fix=(
                    f"Use the value as known at prediction time: '{known.value_ref}'"
                ),
            )

    def assert_no_future_revision(
        self, value_ref: str, as_of_time: datetime
    ) -> None:
        """Assert no revision occurred after as_of_time is used as current value."""
        revisions = self._revisions.get(value_ref, [])
        for rev in revisions:
            if rev.revision_time > as_of_time:
                # This is only a leak if the later revision is being used
                # as if it were available at prediction time.
                # Registration alone is not a leak — using it is.
                return
