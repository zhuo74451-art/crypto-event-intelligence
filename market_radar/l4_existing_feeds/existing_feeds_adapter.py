"""MVP+ Lane 4 — Existing Feeds Adapter.

Reads from existing data sources in the cei_signal_core pipeline:
  - Raw signals from data/raw_signals.csv
  - Watcher alerts from data/watcher_alerts_raw.csv
  - News items from data/raw_news_live_incremental.csv (if available)

Output: list[UnifiedFeedItem] per sealed contract.

Design:
  - One-shot: single read, no daemon/cron
  - All reads are local CSV/SQLite — no network calls
  - Graceful degradation: missing files → empty list
  - No secret/credential handling
"""

from __future__ import annotations

import csv
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.shared.contracts import (
    UnifiedFeedItem,
    FeedType,
    FeedSourceName,
    ExtractionMethod,
    SourceHealth,
    SourceStatus,
    DegradedInfo,
)

# ── Constants ─────────────────────────────────────────────────────────────────

VERSION = "mvp+v1.0-l4"
DATA_DIR = "data"  # Relative to project root


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    return str(val).strip()


# ── Data Sources ──────────────────────────────────────────────────────────────

RAW_SIGNALS_CSV = os.path.join(DATA_DIR, "raw_signals.csv")
WATCHER_ALERTS_CSV = os.path.join(DATA_DIR, "watcher_alerts_raw.csv")
NEWS_LIVE_CSV = os.path.join(DATA_DIR, "raw_news_live_incremental.csv")

# Field mappings for raw_signals.csv
SIGNAL_FIELDS = {
    "title": ["title", "headline", "event_title"],
    "body": ["description", "body", "content", "summary"],
    "url": ["url", "source_url", "link"],
    "source": ["source_name", "source", "feed"],
    "event_type": ["event_type", "category", "type"],
    "intensity": ["intensity", "severity", "priority", "impact"],
    "assets": ["assets_affected", "symbols", "assets", "coins"],
    "published_at": ["published_at", "timestamp", "date", "event_time"],
}

FEED_SOURCE_MAP: dict[str, FeedSourceName] = {
    "coindesk": FeedSourceName.COINDESK,
    "cointelegraph": FeedSourceName.COINTELEGRAPH,
    "decrypt": FeedSourceName.DECRYPT,
    "theblock": FeedSourceName.THE_BLOCK,
    "binance": FeedSourceName.BINANCE_ANNOUNCEMENTS,
    "telegram": FeedSourceName.TELEGRAM_ALPHA,
}


@dataclass
class L4Result:
    """Aggregated result from a single L4 run."""
    feed_items: list[UnifiedFeedItem] = field(default_factory=list)
    source_health: list[SourceHealth] = field(default_factory=list)
    sources_checked: int = 0
    sources_ok: int = 0
    sources_failed: int = 0
    total_items: int = 0
    run_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "lane": "L4",
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "sources_checked": self.sources_checked,
            "sources_ok": self.sources_ok,
            "sources_failed": self.sources_failed,
            "total_items": self.total_items,
            "item_count": len(self.feed_items),
            "error": self.error,
        }


def _read_csv_safe(filepath: str) -> list[dict[str, str]]:
    """Safely read a CSV file. Returns empty list if file doesn't exist or is unreadable."""
    if not os.path.isfile(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [row for row in reader if any(v.strip() for v in row.values())]
    except (OSError, csv.Error):
        return []


def _find_field(row: dict, candidates: list[str]) -> str:
    """Find the first non-empty field from candidates in row."""
    for key in candidates:
        val = row.get(key, "")
        if val and val.strip():
            return val.strip()
    return ""


def _classify_feed_type(row: dict) -> FeedType:
    """Classify feed type based on row content."""
    source = row.get("source_name", row.get("source", row.get("feed", ""))).lower()
    intensity = row.get("intensity", row.get("severity", row.get("priority", ""))).lower()

    if "alert" in source or "urgent" in source or intensity in ("critical", "high"):
        return FeedType.FLASH
    if "news" in source or any(k in row for k in ("event_type", "category")):
        return FeedType.NEWS
    if "telegram" in source or "tg" in source:
        return FeedType.TELEGRAM
    return FeedType.NEWS


def _classify_source(source_str: str) -> FeedSourceName:
    """Map a raw source string to a FeedSourceName."""
    source_lower = source_str.lower().strip()
    for key, value in FEED_SOURCE_MAP.items():
        if key in source_lower:
            return value
    return FeedSourceName.UNKNOWN


def _parse_items_from_csv(filepath: str, feed_type: FeedType) -> list[UnifiedFeedItem]:
    """Parse UnifiedFeedItems from a CSV file."""
    rows = _read_csv_safe(filepath)
    items: list[UnifiedFeedItem] = []
    now = _utc_now()

    for i, row in enumerate(rows):
        title = _find_field(row, SIGNAL_FIELDS["title"])
        if not title:
            continue

        source_str = _find_field(row, SIGNAL_FIELDS["source"])
        source_name = _classify_source(source_str)

        assets_str = _find_field(row, SIGNAL_FIELDS["assets"])
        assets = [a.strip() for a in assets_str.split(",") if a.strip()] if assets_str else []

        items.append(UnifiedFeedItem(
            feed_id=f"{feed_type.value}_{i}_{uuid.uuid4().hex[:6]}",
            feed_type=feed_type,
            source_name=source_name,
            title=title,
            body=_find_field(row, SIGNAL_FIELDS["body"]) or None,
            url=_find_field(row, SIGNAL_FIELDS["url"]) or None,
            event_type=_find_field(row, SIGNAL_FIELDS["event_type"]) or None,
            intensity=_find_field(row, SIGNAL_FIELDS["intensity"]) or None,
            assets_affected=assets,
            published_at=_find_field(row, SIGNAL_FIELDS["published_at"]) or now,
            ingested_at=now,
            extraction_method=ExtractionMethod.RULE_BASED_KEYWORD,
            original_id=row.get("id", row.get("event_id", "")),
            data_origin="live",
        ))

    return items


def run(project_root: Optional[str] = None) -> L4Result:
    """Run L4: read existing feed data from local CSV files.

    Args:
        project_root: Optional override for project root directory.
                      Defaults to current working directory.

    Returns:
        L4Result with feed items and per-source health.
    """
    run_id = uuid.uuid4().hex[:12]
    started_at = _utc_now()
    root = project_root or os.getcwd()

    items: list[UnifiedFeedItem] = []
    health: list[SourceHealth] = []
    sources_checked = 0
    sources_ok = 0
    sources_failed = 0

    csv_sources = [
        (os.path.join(root, RAW_SIGNALS_CSV), FeedType.NEWS, "raw_signals"),
        (os.path.join(root, WATCHER_ALERTS_CSV), FeedType.FLASH, "watcher_alerts"),
        (os.path.join(root, NEWS_LIVE_CSV), FeedType.NEWS, "news_live"),
    ]

    now = _utc_now()

    for filepath, feed_type, source_label in csv_sources:
        sources_checked += 1
        if not os.path.isfile(filepath):
            health.append(SourceHealth(
                source_name=source_label,
                source_group="news" if feed_type == FeedType.NEWS else "telegram",
                status=SourceStatus.DEGRADED,
                last_error_at=now,
                success_count=0,
                error_count=1,
                degraded_info=DegradedInfo(
                    error_type="FILE_NOT_FOUND",
                    occurred_at=now,
                    retryable=True,
                    message_summary=f"CSV file not found: {os.path.basename(filepath)}",
                ),
            ))
            sources_failed += 1
            continue

        parsed = _parse_items_from_csv(filepath, feed_type)
        items.extend(parsed)

        health.append(SourceHealth(
            source_name=source_label,
            source_group="news" if feed_type == FeedType.NEWS else "telegram",
            status=SourceStatus.OK,
            last_success_at=now,
            success_count=1,
            error_count=0,
        ))
        sources_ok += 1

    completed_at = _utc_now()
    return L4Result(
        feed_items=items,
        source_health=health,
        sources_checked=sources_checked,
        sources_ok=sources_ok,
        sources_failed=sources_failed,
        total_items=len(items),
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
    )


def main():
    """CLI entry: run L4 once and print summary."""
    result = run()
    print(f"L4 Run: {result.run_id}")
    print(f"  Sources: {result.sources_ok}/{result.sources_checked} OK")
    print(f"  Feed items found: {result.total_items}")
    for item in result.feed_items[:5]:
        d = item.as_dict()
        print(f"    {d['feed_id'][:20]:20s} | {d['feed_type']:10s} | {d['title'][:50]:50s}")
    if result.total_items > 5:
        print(f"    ... and {result.total_items - 5} more")
    if result.error:
        print(f"  ERROR: {result.error}")
    return 0


if __name__ == "__main__":
    main()
