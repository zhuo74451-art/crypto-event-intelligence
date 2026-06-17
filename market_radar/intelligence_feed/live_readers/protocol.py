"""Reader Protocol — abstraction for one-shot synchronous feed readers.

All readers:
  - Execute read_once() exactly once per call
  - Return synchronously (no async, no threads)
  - Accept input paths via constructor injection
  - Never hardcode production paths
  - Never write to source files/DBs
  - Never start daemons, schedulers, or loops
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from market_radar.intelligence_feed.models import (
    FeedItem, FeedSourceType, FeedDataMode,
)


class ReaderStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ReaderHealth:
    """Health snapshot for a single reader after a read_once() call.

    Records operational status, timing, error info, and data-mode metadata
    so consumers can distinguish live, cached, and degraded results.
    """
    status: ReaderStatus                    # ok / degraded / unavailable
    source_name: str                        # e.g. "flash_jsonl", "news_csv"
    source_type: FeedSourceType             # FLASH / NEWS / TELEGRAM
    last_success_at: Optional[str] = None   # UTC ISO 8601
    latency_ms: Optional[float] = None      # wall-clock milliseconds
    stale: bool = False
    error: Optional[str] = None
    record_count: int = 0
    records_seen: int = 0
    records_rejected: int = 0
    data_mode: FeedDataMode = FeedDataMode.LIVE  # metadata only; actual items carry their own

    def as_dict(self) -> dict:
        return {
            "status": self.status.value,
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "last_success_at": self.last_success_at,
            "latency_ms": self.latency_ms,
            "stale": self.stale,
            "error": self.error,
            "record_count": self.record_count,
            "records_seen": self.records_seen,
            "records_rejected": self.records_rejected,
            "data_mode": self.data_mode.value,
        }


@dataclass
class ReaderBatchResult:
    """Result of a single read_once() call.

    Fields:
        source_name: Human-readable label for the source.
        source_type: FeedSourceType classification.
        status: ReaderStatus — ok / degraded / unavailable.
        items: List of normalized FeedItem instances (empty on failure).
        records_seen: Total rows/records processed before filtering.
        records_accepted: Items that passed validation.
        records_rejected: Items that failed validation.
        errors: List of error messages (per-row errors do not block batch).
        provenance: Description of data origin for audit.
        started_at: UTC ISO 8601 when read started.
        finished_at: UTC ISO 8601 when read finished.
        data_mode: Effective data mode (each item carries its own).
        next_cursor: Optional cursor for incremental reads (UTC ISO 8601).
        cursor_safe: True if cursor can be trusted for incremental reads.
        cached_count: Number of cached items in this batch.
        source_statuses: Per-source status breakdown.
        provider_name: Name of the provider/reader.
        metadata: Arbitrary reader-specific metadata.
    """
    source_name: str
    source_type: FeedSourceType
    status: ReaderStatus
    items: list[FeedItem] = field(default_factory=list)
    records_seen: int = 0
    records_accepted: int = 0
    records_rejected: int = 0
    errors: list[str] = field(default_factory=list)
    provenance: str = "injected_path"
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    data_mode: FeedDataMode = FeedDataMode.LIVE
    # Public contract fields (backward-compatible defaults)
    next_cursor: Optional[str] = None
    cursor_safe: bool = True
    cached_count: int = 0
    source_statuses: list[dict] = field(default_factory=list)
    provider_name: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d: dict = {
            "source_name": self.source_name,
            "source_type": self.source_type.value,
            "status": self.status.value,
            "items_count": len(self.items),
            "records_seen": self.records_seen,
            "records_accepted": self.records_accepted,
            "records_rejected": self.records_rejected,
            "errors": self.errors,
            "provenance": self.provenance,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "data_mode": self.data_mode.value,
            "next_cursor": self.next_cursor,
            "cursor_safe": self.cursor_safe,
            "cached_count": self.cached_count,
            "source_statuses": self.source_statuses,
            "provider_name": self.provider_name,
            "metadata": self.metadata,
        }
        return d

    def to_health(self, latency_ms: Optional[float] = None) -> ReaderHealth:
        return ReaderHealth(
            status=self.status,
            source_name=self.source_name,
            source_type=self.source_type,
            last_success_at=self.finished_at if self.status == ReaderStatus.OK else None,
            latency_ms=latency_ms,
            error=self.errors[0] if self.errors else None,
            record_count=len(self.items),
            records_seen=self.records_seen,
            records_rejected=self.records_rejected,
            data_mode=self.data_mode,
        )


class ReaderProtocol(ABC):
    """Abstract base for a single one-shot feed reader.

    Subclasses must implement read_once(). All readers:
      - Execute exactly once per call
      - Return synchronously
      - Accept input paths via constructor injection
    """

    @abstractmethod
    def read_once(self) -> ReaderBatchResult:
        """Read and return all items from the configured source.

        Returns a ReaderBatchResult. Never raises — errors are captured
        in the result object. Individual row failures do not block the batch.
        """
        ...

    @property
    @abstractmethod
    def source_type(self) -> FeedSourceType:
        """The FeedSourceType this reader produces."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable label for this source."""
        ...


# ── Helpers ────────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_ms() -> float:
    return datetime.now(timezone.utc).timestamp() * 1000
