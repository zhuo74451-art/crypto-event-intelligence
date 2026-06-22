"""Base provider interface for macro-economic data sources.

All providers must implement this base class and register with the provider registry.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from ..contracts import (
    MacroReleaseEventV1,
    MacroConsensusObservationV1,
    MacroRevisionRecordV1,
    MacroSourceSnapshotV1,
    Provider,
    ParseStatus,
    generate_snapshot_id,
    utc_now,
)


class ProviderBase(ABC):
    """Abstract base for all macro data providers."""

    provider_name: str = ""
    base_url: str = ""
    user_agent: str = "CryptoEventIntelligence/1.0 (research; +https://github.com/zhuo74451-art/crypto-event-intelligence)"
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 2.0
    rate_limit_delay: float = 1.0

    def __init__(self, cache_dir: str = "", output_dir: str = ""):
        self.cache_dir = cache_dir
        self.output_dir = output_dir
        self._snapshots: list[MacroSourceSnapshotV1] = []
        self._last_request_time: float = 0.0

    @abstractmethod
    def fetch_release_calendar(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch the release calendar for this provider."""
        ...

    @abstractmethod
    def fetch_release_values(self, series_id: str, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Fetch actual release values for a series."""
        ...

    @abstractmethod
    def fetch_revision_history(self, series_id: str) -> list[dict[str, Any]]:
        """Fetch revision history for a series."""
        ...

    @abstractmethod
    def normalize_release(self, raw: dict[str, Any]) -> Optional[MacroReleaseEventV1]:
        """Normalize a raw record into a canonical MacroReleaseEventV1."""
        ...

    @abstractmethod
    def normalize_revision(self, raw: dict[str, Any]) -> Optional[MacroRevisionRecordV1]:
        """Normalize a raw record into a canonical MacroRevisionRecordV1."""
        ...

    def fetch_consensus_observations(self, event_family: str, reference_period: str) -> list[dict[str, Any]]:
        """Fetch consensus observations for an event. Default: return empty."""
        return []

    def normalize_consensus(self, raw: dict[str, Any]) -> Optional[MacroConsensusObservationV1]:
        """Normalize a raw consensus record. Default: return None."""
        return None

    def save_raw_snapshot(self, url: str, content: bytes,
                           content_type: str, published_at: str = "") -> MacroSourceSnapshotV1:
        """Save raw fetched content to disk and create a snapshot record."""
        sha256_hash = hashlib.sha256(content).hexdigest()
        retrieved_at = utc_now()

        snapshot = MacroSourceSnapshotV1(
            provider=self.provider_name,
            source_url=url,
            retrieved_at_utc=retrieved_at,
            published_at_utc=published_at or retrieved_at,
            content_type=content_type,
            sha256=sha256_hash,
            http_status=200,
            parse_status="pending",
        )

        # Write to raw data directory
        if self.output_dir:
            raw_dir = os.path.join(self.output_dir, "raw", self.provider_name)
            os.makedirs(raw_dir, exist_ok=True)
            fname = f"{snapshot.snapshot_id}_{''.join(c for c in url.split('/')[-1][:80] if c.isalnum() or c in '._-')[:60]}"
            fpath = os.path.join(raw_dir, fname)
            with open(fpath, "wb") as f:
                f.write(content)
            snapshot.local_path = fpath

        self._snapshots.append(snapshot)
        return snapshot

    def _rate_limit(self):
        """Enforce rate limit between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    def get_snapshots(self) -> list[MacroSourceSnapshotV1]:
        return list(self._snapshots)
