"""Feed truth audit — classify sources, count live/cached/fixture/research, detect duplicates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import FeedItem, FeedDataMode, FeedSourceType, Freshness


@dataclass
class FeedTruth:
    """Breakdown of feed items by classification."""
    flash_live: int = 0
    news_live: int = 0
    telegram_live: int = 0
    cached: int = 0
    fixture: int = 0
    research_sample: int = 0
    research_excluded_rows: int = 0
    duplicates_removed: int = 0
    total_raw_rows: int = 0

    @property
    def live_total(self) -> int:
        return self.flash_live + self.news_live + self.telegram_live

    def as_dict(self) -> dict:
        return {
            "flash_live": self.flash_live,
            "news_live": self.news_live,
            "telegram_live": self.telegram_live,
            "cached": self.cached,
            "fixture": self.fixture,
            "research_sample": self.research_sample,
            "research_excluded_rows": self.research_excluded_rows,
            "duplicates_removed": self.duplicates_removed,
            "total_raw_rows": self.total_raw_rows,
            "live_total": self.live_total,
        }


def classify_data_mode(source_label: str, is_research: bool = False,
                       is_fixture: bool = False, is_live: bool = True) -> FeedDataMode:
    """Classify a feed item's data mode based on provenance."""
    if is_research:
        return FeedDataMode.RESEARCH_SAMPLE
    if is_fixture:
        return FeedDataMode.FIXTURE
    if is_live:
        return FeedDataMode.LIVE
    return FeedDataMode.CACHED


def classify_freshness(published_at: Optional[str]) -> Freshness:
    """Classify freshness from timestamp."""
    from .models import make_freshness
    return make_freshness(published_at)


def build_truth(items: list[FeedItem]) -> FeedTruth:
    """Build FeedTruth from a list of classified FeedItems."""
    truth = FeedTruth()
    seen_ids: set[str] = set()
    truth.total_raw_rows = len(items)

    for item in items:
        if item.feed_id in seen_ids:
            truth.duplicates_removed += 1
            continue
        seen_ids.add(item.feed_id)

        if item.data_mode == FeedDataMode.LIVE:
            if item.source_type == FeedSourceType.FLASH:
                truth.flash_live += 1
            elif item.source_type == FeedSourceType.NEWS:
                truth.news_live += 1
            elif item.source_type == FeedSourceType.TELEGRAM:
                truth.telegram_live += 1
        elif item.data_mode == FeedDataMode.CACHED:
            truth.cached += 1
        elif item.data_mode == FeedDataMode.FIXTURE:
            truth.fixture += 1
        elif item.data_mode == FeedDataMode.RESEARCH_SAMPLE:
            truth.research_sample += 1

    return truth


def deduplicate(items: list[FeedItem]) -> list[FeedItem]:
    """Remove duplicates, keeping first occurrence."""
    seen: set[str] = set()
    result: list[FeedItem] = []
    for item in items:
        if item.feed_id not in seen:
            seen.add(item.feed_id)
            result.append(item)
    return result
