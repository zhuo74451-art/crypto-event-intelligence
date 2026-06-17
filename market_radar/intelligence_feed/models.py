"""Feed item models — source type, data mode, freshness, and the core FeedItem."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class FeedSourceType(str, Enum):
    FLASH = "flash"
    NEWS = "news"
    TELEGRAM = "telegram"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


class FeedDataMode(str, Enum):
    LIVE = "live"
    CACHED = "cached"
    FIXTURE = "fixture"
    RESEARCH_SAMPLE = "research_sample"
    UNKNOWN = "unknown"


class Freshness(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass
class FeedItem:
    """A single normalized feed item with full provenance.

    Rules:
      - feed_id: deterministic content-based hash (never UUID/random)
      - published_at: None if missing (never replaced with current time)
      - data_mode: live/cached/fixture/research_sample
      - research_sample excluded from live feed counts
    """
    feed_id: str                            # deterministic content hash
    source_type: FeedSourceType             # flash / news / telegram
    source_label: str                       # human-readable source name
    data_mode: FeedDataMode                 # live / cached / fixture / research_sample

    title: str
    body: Optional[str] = None
    url: Optional[str] = None
    assets: list[str] = field(default_factory=list)

    published_at: Optional[str] = None      # UTC ISO 8601 or None
    ingested_at: Optional[str] = None       # UTC ISO 8601
    freshness: Freshness = Freshness.UNKNOWN

    event_type: Optional[str] = None
    intensity: Optional[str] = None
    dedup_group: Optional[str] = None       # for duplicate grouping
    original_id: Optional[str] = None       # source's own ID

    def as_dict(self) -> dict:
        return {
            "feed_id": self.feed_id,
            "source_type": self.source_type.value,
            "source_label": self.source_label,
            "data_mode": self.data_mode.value,
            "title": self.title,
            "body": self.body,
            "url": self.url,
            "assets": self.assets,
            "published_at": self.published_at,
            "ingested_at": self.ingested_at,
            "freshness": self.freshness.value,
            "event_type": self.event_type,
            "intensity": self.intensity,
        }


def make_feed_id(content: str, source_label: str) -> str:
    """Deterministic content-based feed ID (never random)."""
    raw = f"{source_label}:{content}"
    return "fi_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def make_freshness(published_at: Optional[str], max_stale_hours: int = 48) -> Freshness:
    """Determine freshness from published_at timestamp."""
    if published_at is None:
        return Freshness.UNKNOWN
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = (now - dt).total_seconds()
        if delta < 0:
            return Freshness.FRESH  # future timestamp = presumed fresh
        if delta < max_stale_hours * 3600:
            return Freshness.FRESH
        return Freshness.STALE
    except (ValueError, TypeError):
        return Freshness.UNKNOWN
