"""Curated Feed Provider Adapter — wraps W3 CuratedApiReader as FeedProviderProtocol.

Thin mapping layer: never copies W3 HTTP, pagination, or field-parsing logic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from market_radar.integration.feed_provider_protocol import (
    FeedProviderProtocol, FeedProviderInput, IntegrationFeedBatch,
)
from market_radar.intelligence_feed.live_readers import (
    CuratedApiReader, CuratedApiConfig, ReaderBatchResult,
)
from market_radar.intelligence_feed.models import FeedDataMode


def _count_data_modes(items: list) -> dict[str, int]:
    """Count items by FeedDataMode from their data_mode attribute."""
    counts = {"live": 0, "fixture": 0, "research": 0, "cached": 0}
    for item in items:
        dm = getattr(item, "data_mode", None)
        if dm == FeedDataMode.LIVE:
            counts["live"] += 1
        elif dm == FeedDataMode.FIXTURE:
            counts["fixture"] += 1
        elif dm == FeedDataMode.RESEARCH_SAMPLE:
            counts["research"] += 1
        # cached is explicit via result.cached_count
    return counts


class CuratedFeedProvider:
    """FeedProviderProtocol adapter for W3 CuratedApiReader.

    Usage:
        provider = CuratedFeedProvider(base_url="...")
        result = run_one_shot(config, feed_provider=provider)
    """

    def __init__(
        self,
        base_url: str = "http://43.98.174.247:8001/api/integration/curated",
        limit: int = 100,
        max_items: int = 500,
        max_pages: int = 5,
        timeout_seconds: float = 15.0,
        reference_time: Optional[datetime] = None,
    ):
        self._base_url = base_url
        self._limit = limit
        self._max_items = max_items
        self._max_pages = max_pages
        self._timeout_seconds = timeout_seconds
        self._reference_time = reference_time

    def __call__(self, inp: FeedProviderInput) -> IntegrationFeedBatch:
        """FeedProviderProtocol entry point. Called once per run."""
        cfg = CuratedApiConfig(
            base_url=self._base_url,
            limit=self._limit,
            max_pages=self._max_pages,
            max_items=self._max_items,
            timeout_seconds=self._timeout_seconds,
            since=inp.since_cursor,
            include_raw_json=False,
        )
        reader = CuratedApiReader(cfg, reference_time=self._reference_time)
        result: ReaderBatchResult = reader.read_once()

        # Verify W1 compatibility: ss.get("ok", False) on normal sources
        for ss in result.source_statuses:
            if ss.get("status") == "ok" and not ss.get("ok", False):
                raise AssertionError(
                    f"W1 contract violation: source {ss.get('source')} "
                    f"status=ok but ss.get('ok', False) is False"
                )

        # Count data modes from actual items
        mode_counts = _count_data_modes(result.items)

        return IntegrationFeedBatch(
            provider_name=result.provider_name or result.source_name,
            overall_status=result.status.value,
            records_seen=result.records_seen,
            records_accepted=result.records_accepted,
            records_rejected=result.records_rejected,
            live_count=mode_counts["live"],
            fixture_count=mode_counts["fixture"],
            research_count=mode_counts["research"],
            cached_count=result.cached_count,
            items=result.items,
            source_statuses=result.source_statuses,
            next_cursor=result.next_cursor,
            cursor_safe=result.cursor_safe,
            provenance=result.provenance,
            errors=result.errors,
            started_at=result.started_at or "",
            finished_at=result.finished_at or "",
        )
