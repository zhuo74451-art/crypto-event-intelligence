"""
Point-in-Time availability ledger — tracks when data was available to the model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from ..contracts.observation import DataAvailabilityRecord
from ..contracts.errors import FutureInformationLeakError


class AvailabilityLedger:
    """Ledger tracking when each data element became available for modeling."""

    def __init__(self):
        self._records: dict[str, DataAvailabilityRecord] = {}

    def add_record(self, record: DataAvailabilityRecord) -> None:
        self._records[record.record_id] = record

    def get_record(self, record_id: str) -> Optional[DataAvailabilityRecord]:
        return self._records.get(record_id)

    def is_available_before(self, record_id: str, as_of_time: datetime) -> bool:
        """Check if a data element was available before a given time."""
        record = self._records.get(record_id)
        if record is None:
            return False
        available = record.available_to_model_at
        if available is None:
            available = record.retrieved_at or record.first_seen_at or record.event_time
        if available is None:
            return True  # no time info — assume available
        return available <= as_of_time

    def assert_available(
        self, record_id: str, as_of_time: datetime
    ) -> None:
        """Assert data was available before as_of_time, or raise leak error."""
        record = self._records.get(record_id)
        if record is None:
            raise FutureInformationLeakError(
                detail=f"Record {record_id} not found in availability ledger",
                object_id=record_id,
                min_fix="Add the record to the ledger before checking availability",
            )
        available = record.available_to_model_at
        if available is None:
            available = record.retrieved_at or record.first_seen_at or record.event_time
        if available is None:
            return
        if available > as_of_time:
            raise FutureInformationLeakError(
                detail=(
                    f"Record {record_id} available at {available} "
                    f"but prediction as_of_time is {as_of_time}"
                ),
                object_id=record_id,
                min_fix="Use data that was available at or before prediction time",
            )

    def compute_available_to_model_at(
        self,
        published_at: Optional[datetime] = None,
        first_seen_at: Optional[datetime] = None,
        retrieved_at: Optional[datetime] = None,
    ) -> Optional[datetime]:
        """Compute the earliest time data was available to a model.

        The model cannot use data before it was:
        1. Published by the source
        2. First seen by the system
        3. Retrieved by the system
        """
        candidates = [t for t in [published_at, first_seen_at, retrieved_at] if t]
        if not candidates:
            return None
        return max(candidates)
