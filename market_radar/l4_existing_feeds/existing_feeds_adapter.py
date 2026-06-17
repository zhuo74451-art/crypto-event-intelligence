"""MVP+ L4v2 — Existing Feeds Adapter + Feed Truth Audit.

Reads from real existing data sources in the repository.
Strictly distinguishes LIVE data from research samples and fixtures.

### Feed Truth Audit ###
Live feeds (counted as real):
  1. data/raw_signals.csv          — Hyperliquid watcher position snapshots  (~326 rows)
  2. data/watcher_alerts_raw.csv   — Etherscan on-chain transfer alerts      (~20 rows)
  3. data/raw_news_live_incremental.csv — News items                        (~51 rows)

Excluded (not counted as live):
  - data/event_candidates_*.csv         — Research review candidates (44 files)
  - data/events_*.csv                   — Research/backtest datasets
  - data/*_test.csv                     — Test outputs (27 files)
  - data/fixtures/**                    — Explicit fixture data (8 files)

Output: list[UnifiedFeedItem] with stream_type, source_label, data_mode.
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

VERSION = "mvp+v1.0-l4v2"
DATA_DIR = "data"

# ── Live feed sources (truth audit verified) ─────────────────────────────────
LIVE_SOURCES = [
    {"file": "raw_signals.csv",          "feed_type": FeedType.FLASH,   "label": "hl_watcher_signals",     "counted": True},
    {"file": "watcher_alerts_raw.csv",   "feed_type": FeedType.FLASH,   "label": "onchain_watcher_alerts", "counted": True},
    {"file": "raw_news_live_incremental.csv", "feed_type": FeedType.NEWS, "label": "news_live",            "counted": True},
]

FIXTURE_SOURCES = [
    {"file": os.path.join("fixtures", "market_radar_v112f_whale_positions.json"),
     "feed_type": FeedType.ONCHAIN, "label": "fixture_whale_positions", "counted": False},
]

# CSV field mapping
COMMON_FIELDS = {
    "title": ["title", "headline"],
    "body": ["description", "body", "content"],
    "url": ["url", "source_url", "link"],
    "source": ["source_name", "source", "feed"],
    "event_type": ["event_type", "category", "type"],
    "intensity": ["intensity", "severity", "priority"],
    "assets": ["assets_affected", "symbols", "asset", "assets", "coins"],
    "published_at": ["published_at", "timestamp", "date", "event_time", "observed_at_utc"],
}

FEED_SOURCE_MAP = {
    "coindesk": FeedSourceName.COINDESK,
    "cointelegraph": FeedSourceName.COINTELEGRAPH,
    "decrypt": FeedSourceName.DECRYPT,
    "theblock": FeedSourceName.THE_BLOCK,
    "binance": FeedSourceName.BINANCE_ANNOUNCEMENTS,
    "telegram": FeedSourceName.TELEGRAM_ALPHA,
    "hyperliquid": FeedSourceName.HYPERLIQUID_FEED,
    "etherscan": FeedSourceName.UNKNOWN,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_str(val: Any, default: str = "") -> str:
    if val is None: return default
    return str(val).strip()


def _find_field(row: dict, candidates: list[str]) -> str:
    for key in candidates:
        val = row.get(key, "")
        if val and val.strip():
            return val.strip()
    return ""


def _classify_source(source_str: str) -> FeedSourceName:
    source_lower = source_str.lower().strip()
    for key, value in FEED_SOURCE_MAP.items():
        if key in source_lower: return value
    return FeedSourceName.UNKNOWN


def _parse_items_from_csv(
    filepath: str,
    feed_type: FeedType,
    source_label: str,
    stream_type: str,
    counted: bool,
    project_root: str,
) -> tuple[list[UnifiedFeedItem], int]:
    """Parse items from a CSV file. Returns (items, skipped_count)."""
    fullpath = os.path.join(project_root, filepath) if not os.path.isabs(filepath) else filepath
    if not os.path.isfile(fullpath):
        return [], 0

    try:
        with open(fullpath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = [row for row in reader]
    except (OSError, csv.Error):
        return [], 0

    items: list[UnifiedFeedItem] = []
    now = _utc_now()
    skipped = 0

    for i, row in enumerate(rows):
        title = _find_field(row, COMMON_FIELDS["title"])
        # For raw_signals, the title is long but valuable
        if not title:
            skipped += 1
            continue

        source_str = _find_field(row, COMMON_FIELDS["source"])
        source_name = _classify_source(source_str)

        assets_str = _find_field(row, COMMON_FIELDS["assets"])
        assets = [a.strip() for a in assets_str.split(",") if a.strip()] if assets_str else []

        published_at = _find_field(row, COMMON_FIELDS["published_at"]) or ""
        body = _find_field(row, COMMON_FIELDS["body"]) or None
        url = _find_field(row, COMMON_FIELDS["url"]) or None
        event_type = _find_field(row, COMMON_FIELDS["event_type"]) or None
        intensity_str = _find_field(row, COMMON_FIELDS["intensity"]) or None

        # Preserve original raw reference for audit
        raw_ref = row.get("dedupe_key", row.get("signal_id", row.get("alert_id", row.get("raw_id", ""))))

        items.append(UnifiedFeedItem(
            feed_id=f"{source_label}_{i}_{uuid.uuid4().hex[:6]}",
            feed_type=feed_type,
            source_name=source_name,
            title=title,
            body=body,
            url=url,
            event_type=event_type,
            intensity=intensity_str,
            assets_affected=assets,
            published_at=published_at or now,
            ingested_at=now,
            extraction_method=ExtractionMethod.RULE_BASED_KEYWORD,
            original_id=raw_ref,
            data_origin="live" if counted else "cached",
        ))

    return items, skipped


@dataclass
class FeedTruthResult:
    """Feed truth audit breakdown."""
    flash_count: int = 0
    news_count: int = 0
    tg_count: int = 0
    live_count: int = 0
    cached_count: int = 0
    fixture_count: int = 0
    duplicate_count: int = 0
    research_excluded: int = 0

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class L4Result:
    feed_items: list[UnifiedFeedItem] = field(default_factory=list)
    source_health: list[SourceHealth] = field(default_factory=list)
    truth: FeedTruthResult = field(default_factory=FeedTruthResult)
    sources_checked: int = 0
    sources_ok: int = 0
    sources_failed: int = 0
    total_items: int = 0
    total_skipped: int = 0
    run_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {"lane": "L4", "run_id": self.run_id,
            "started_at": self.started_at, "completed_at": self.completed_at,
            "sources_checked": self.sources_checked, "sources_ok": self.sources_ok,
            "sources_failed": self.sources_failed,
            "total_items": self.total_items, "total_skipped": self.total_skipped,
            "item_count": len(self.feed_items),
            "truth": self.truth.as_dict(), "error": self.error}


def _read_csv_lines(filepath: str) -> int:
    """Count data rows in a CSV file (excl. header)."""
    if not os.path.isfile(filepath): return 0
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            return sum(1 for _ in f) - 1
    except Exception:
        return 0


def run(project_root: Optional[str] = None) -> L4Result:
    """Run L4: read existing live feed data with truth audit."""
    run_id = uuid.uuid4().hex[:12]
    started_at = _utc_now()
    root = project_root or os.getcwd()
    now = _utc_now()

    items: list[UnifiedFeedItem] = []
    health: list[SourceHealth] = []
    truth = FeedTruthResult()
    sources_checked = 0; sources_ok = 0; sources_failed = 0
    total_skipped = 0

    # ── Process LIVE sources ──
    for src in LIVE_SOURCES:
        filepath = os.path.join(root, DATA_DIR, src["file"])
        sources_checked += 1

        raw_count = _read_csv_lines(filepath)
        parsed, skipped = _parse_items_from_csv(
            filepath, src["feed_type"], src["label"],
            "live", src["counted"], root,
        )

        total_skipped += skipped

        if parsed:
            items.extend(parsed)
            sources_ok += 1
            if src["counted"]:
                truth.live_count += len(parsed)
            else:
                truth.cached_count += len(parsed)
            if src["feed_type"] == FeedType.FLASH:
                truth.flash_count += len(parsed)
            elif src["feed_type"] == FeedType.NEWS:
                truth.news_count += len(parsed)
            elif src["feed_type"] == FeedType.TELEGRAM:
                truth.tg_count += len(parsed)

            health.append(SourceHealth(
                source_name=f"live:{src['label']}",
                source_group="news" if src["feed_type"] == FeedType.NEWS else "telegram",
                status=SourceStatus.OK,
                last_success_at=now, success_count=1, error_count=0,
            ))
        else:
            sources_failed += 1
            health.append(SourceHealth(
                source_name=f"live:{src['label']}",
                source_group="news" if src["feed_type"] == FeedType.NEWS else "telegram",
                status=SourceStatus.DEGRADED if raw_count > 0 else SourceStatus.FAILED,
                degraded_info=DegradedInfo(
                    error_type="PARSE_FAILED",
                    occurred_at=now, retryable=True,
                    message_summary=f"{src['file']}: {raw_count} raw rows, 0 parsed",
                ),
            ))

    # ── Count research files excluded ──
    data_path = os.path.join(root, DATA_DIR)
    if os.path.isdir(data_path):
        research_patterns = ["event_candidates_", "events_", "_test", "backtest_",
                             "v0" , "v05", "v06", "v08", "v13", "v14"]
        for fname in os.listdir(data_path):
            if not fname.endswith(".csv"):
                continue
            fpath = os.path.join(data_path, fname)
            if not os.path.isfile(fpath):
                continue
            if any(fname.startswith(p) or p in fname for p in research_patterns):
                truth.research_excluded += _read_csv_lines(fpath)
        # Also count fixture JSON
        fixtures_dir = os.path.join(data_path, "fixtures")
        if os.path.isdir(fixtures_dir):
            for fname in os.listdir(fixtures_dir):
                if fname.endswith(".json") or fname.endswith(".csv"):
                    truth.fixture_count += 1

    # ── Process fixture sources ──
    for src in FIXTURE_SOURCES:
        filepath = os.path.join(root, DATA_DIR, src["file"])
        if os.path.isfile(filepath):
            truth.fixture_count += 1
        health.append(SourceHealth(
            source_name=f"fixture:{src['label']}",
            source_group="fixture",
            status=SourceStatus.DEGRADED,
            degraded_info=DegradedInfo(
                error_type="FIXTURE_MODE",
                occurred_at=now, retryable=False,
                message_summary="Fixture data for testing only — not counted as live",
            ),
        ))

    completed_at = _utc_now()
    return L4Result(
        feed_items=items, source_health=health, truth=truth,
        sources_checked=sources_checked, sources_ok=sources_ok,
        sources_failed=sources_failed,
        total_items=len(items), total_skipped=total_skipped,
        run_id=run_id, started_at=started_at, completed_at=completed_at,
    )


def main():
    result = run()
    print(f"L4v2 Run: {result.run_id}")
    print(f"  Sources: {result.sources_ok}/{result.sources_checked} OK")
    print(f"  Items: {result.total_items} (skipped: {result.total_skipped})")
    t = result.truth
    print(f"  Feed Truth: flash={t.flash_count} news={t.news_count} tg={t.tg_count}")
    print(f"  Data Mode: live={t.live_count} cached={t.cached_count} fixture={t.fixture_count}")
    print(f"  Research excluded: {t.research_excluded} rows")
    print(f"  Duplicates: {t.duplicate_count}")
    for item in result.feed_items[:5]:
        d = item.as_dict()
        print(f"    {d['feed_id'][:20]:20s} | {d['feed_type']:10s} | {d['title'][:50]:.50s}")
    if result.total_items > 5:
        print(f"    ... and {result.total_items - 5} more")
    return 0


if __name__ == "__main__":
    main()
