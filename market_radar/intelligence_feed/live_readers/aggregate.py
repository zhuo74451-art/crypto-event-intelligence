"""Aggregate reader — run multiple readers, collect results, deduplicate.

read_all_once() is the one-shot entry point that:
  - Runs all provided readers (each exactly once)
  - Collects results and health for each
  - Deduplicates by feed_id
  - Detects ID conflicts with different content
  - Summarizes live / fixture / cached / rejected counts
  - Never sends, persists, or starts background work
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from market_radar.intelligence_feed.live_readers.protocol import (
    ReaderProtocol, ReaderBatchResult, ReaderHealth, ReaderStatus,
)
from market_radar.intelligence_feed.models import FeedItem, FeedDataMode


@dataclass
class FeedReadSummary:
    """Aggregated result from running multiple readers.

    Fields:
        items: Deduplicated list of FeedItems from all readers.
        health: List of ReaderHealth, one per reader.
        source_statuses: Dict mapping source_name to status string.
        counts: Breakdown of items by data_mode.
        errors: All errors from all readers.
        overall_status: 'ok' if at least one reader succeeded,
                       'degraded' if some failed,
                       'unavailable' if all failed.
    """
    items: list[FeedItem] = field(default_factory=list)
    health: list[ReaderHealth] = field(default_factory=list)
    source_statuses: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=lambda: {
        "live": 0, "fixture": 0, "cached": 0, "research_sample": 0,
        "rejected": 0, "total_items": 0,
    })
    errors: list[str] = field(default_factory=list)
    overall_status: str = "unavailable"

    def as_dict(self) -> dict:
        return {
            "items_count": len(self.items),
            "health": [h.as_dict() for h in self.health],
            "source_statuses": self.source_statuses,
            "counts": self.counts,
            "errors": self.errors,
            "overall_status": self.overall_status,
        }


def read_all_once(readers: list[ReaderProtocol]) -> FeedReadSummary:
    """Run all readers once, collect and deduplicate results.

    Single reader failure does not block others. Returns a FeedReadSummary
    with deduplicated items, health reports, and aggregated counts.

    Args:
        readers: List of ReaderProtocol instances to execute.

    Returns:
        FeedReadSummary with all results.
    """
    health_list: list[ReaderHealth] = []
    all_items: list[FeedItem] = []
    all_errors: list[str] = []
    source_statuses: dict[str, str] = {}

    for reader in readers:
        try:
            result = reader.read_once()
            batch_health = result.to_health()
            health_list.append(batch_health)
            source_statuses[result.source_name] = result.status.value
            all_items.extend(result.items)
            if result.errors:
                all_errors.extend(
                    f"[{result.source_name}] {e}" for e in result.errors
                )
        except Exception as e:
            health_list.append(ReaderHealth(
                status=ReaderStatus.UNAVAILABLE,
                source_name=reader.source_name,
                source_type=reader.source_type,
                error=str(e),
            ))
            source_statuses[reader.source_name] = "unavailable"
            all_errors.append(f"[{reader.source_name}] Exception: {e}")

    # Deduplicate by feed_id
    seen: dict[str, FeedItem] = {}
    id_conflicts: list[str] = []

    for item in all_items:
        existing = seen.get(item.feed_id)
        if existing is None:
            seen[item.feed_id] = item
        else:
            # Check for content conflict
            if (existing.title != item.title or
                    existing.body != item.body):
                id_conflicts.append(
                    f"ID conflict: {item.feed_id} — "
                    f"'{existing.title}' vs '{item.title}'"
                )
            # Keep first occurrence (deterministic)

    # Count by data_mode
    live_count = sum(1 for i in seen.values() if i.data_mode == FeedDataMode.LIVE)
    fixture_count = sum(1 for i in seen.values() if i.data_mode == FeedDataMode.FIXTURE)
    cached_count = sum(1 for i in seen.values() if i.data_mode == FeedDataMode.CACHED)
    research_count = sum(1 for i in seen.values() if i.data_mode == FeedDataMode.RESEARCH_SAMPLE)

    # Determine overall status
    succeeded = sum(1 for h in health_list if h.status == ReaderStatus.OK)
    failed = sum(1 for h in health_list if h.status in (ReaderStatus.DEGRADED, ReaderStatus.UNAVAILABLE))

    if succeeded > 0 and failed == 0:
        overall = "ok"
    elif succeeded > 0:
        overall = "degraded"
    elif succeeded == 0 and len(readers) > 0:
        overall = "unavailable"
    else:
        overall = "unavailable"

    return FeedReadSummary(
        items=list(seen.values()),
        health=health_list,
        source_statuses=source_statuses,
        counts={
            "live": live_count,
            "fixture": fixture_count,
            "cached": cached_count,
            "research_sample": research_count,
            "rejected": sum(h.records_rejected for h in health_list),
            "total_items": len(seen),
        },
        errors=all_errors,
        overall_status=overall,
    )
