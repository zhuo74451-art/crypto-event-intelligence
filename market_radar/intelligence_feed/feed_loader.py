"""Feed loader — loads feed items from fixtures/samples, no network access.

This ticket uses only injected fixture data. No CSV parsing, no network I/O.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .models import (
    FeedItem, FeedSourceType, FeedDataMode, Freshness,
    make_feed_id, make_freshness,
)
from .truth_audit import FeedTruth, build_truth, deduplicate, classify_data_mode


@dataclass
class FeedResult:
    """Result from a feed load operation."""
    items: list[FeedItem] = field(default_factory=list)
    truth: FeedTruth = field(default_factory=FeedTruth)
    sources_ok: int = 0
    sources_failed: int = 0
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "items_count": len(self.items),
            "truth": self.truth.as_dict(),
            "sources_ok": self.sources_ok,
            "sources_failed": self.sources_failed,
            "error": self.error,
        }


# ── Fixture data ─────────────────────────────────────────────────────────────

FLASH_FIXTURES: list[dict] = [
    {
        "title": "Whale Matrixport Related increased BTC long +$12.5M",
        "body": "Address 0x6c85...f6 added $12.5M to existing BTC long, now $62.5M total.",
        "source_label": "hl_watcher",
        "assets": ["BTC"],
        "published_at": None,
        "data_mode": "fixture",
    },
    {
        "title": "USDT $180M minted on Tron Treasury",
        "body": "Tron Treasury minted 180M USDT. Circulation increase detected.",
        "source_label": "onchain_watcher",
        "assets": ["USDT"],
        "published_at": "2026-06-16T14:30:00Z",
        "data_mode": "fixture",
    },
    {
        "title": "Binance hot wallet $500M USDT transfer to unknown address",
        "body": "Large whale movement detected: 500M USDT from Binance to unknown wallet.",
        "source_label": "onchain_watcher",
        "assets": ["USDT", "BTC"],
        "published_at": "2026-06-16T12:00:00Z",
        "data_mode": "fixture",
    },
    {
        "title": "Whale loraclexyz flipped HYPE short to long, +$8M",
        "body": "Direction flip detected on HYPE: $8M position flipped from short to long.",
        "source_label": "hl_watcher",
        "assets": ["HYPE"],
        "published_at": "2026-06-16T10:15:00Z",
        "data_mode": "fixture",
    },
    {
        "title": "Research: BTC accumulation pattern analysis",
        "body": "Historical analysis of BTC accumulation patterns during ETF inflow periods.",
        "source_label": "research_db",
        "assets": ["BTC"],
        "published_at": "2026-06-01T00:00:00Z",
        "data_mode": "research_sample",
    },
]

NEWS_FIXTURES: list[dict] = [
    {
        "title": "SEC delays decision on spot ETH ETF options",
        "body": "The SEC has postponed its decision on options trading for spot ETH ETFs.",
        "source_label": "coindesk",
        "assets": ["ETH"],
        "published_at": "2026-06-16T15:00:00Z",
        "data_mode": "fixture",
    },
    {
        "title": "Hyperliquid surpasses $5B in daily DEX volume",
        "body": "Hyperliquid DEX reached $5B daily volume for the first time.",
        "source_label": "theblock",
        "assets": ["HYPE"],
        "published_at": "2026-06-16T13:45:00Z",
        "data_mode": "fixture",
    },
    {
        "title": "Bitcoin hash rate reaches new ATH of 800 EH/s",
        "body": "Bitcoin network hash rate hit a new all-time high of 800 exahashes per second.",
        "source_label": "cointelegraph",
        "assets": ["BTC"],
        "published_at": "2026-06-16T11:30:00Z",
        "data_mode": "fixture",
    },
    {
        "title": "SOL developer activity up 40% in Q2 2026",
        "body": "Solana developer ecosystem grew 40% QoQ with new DeFi protocols launching.",
        "source_label": "coindesk",
        "assets": ["SOL"],
        "published_at": "2026-06-16T09:00:00Z",
        "data_mode": "fixture",
    },
    {
        "title": "Historical: BTC ETF approval impact study",
        "body": "Academic study on BTC ETF approval market impact across 12 months.",
        "source_label": "research_db",
        "assets": ["BTC", "ETH"],
        "published_at": "2026-05-15T00:00:00Z",
        "data_mode": "research_sample",
    },
]

TELEGRAM_FIXTURES: list[dict] = []  # Empty — honest reporting

FIXTURE_ITEMS: list[dict] = [
    {
        "title": "FIXTURE: Sample whale position data",
        "source_label": "fixture_whale",
        "assets": ["BTC", "ETH"],
        "published_at": "2026-06-15T00:00:00Z",
        "data_mode": "fixture",
    },
]


def _build_item(raw: dict, source_type: FeedSourceType) -> FeedItem:
    """Convert a raw dict to a FeedItem with deterministic ID."""
    title = raw.get("title", "")
    body = raw.get("body")
    source_label = raw.get("source_label", "unknown")
    assets = raw.get("assets", [])
    published_at = raw.get("published_at")  # None → stays None
    data_mode_str = raw.get("data_mode", "live")

    data_mode = FeedDataMode(data_mode_str)
    feed_id = make_feed_id(title or body or "", source_label)
    freshness = make_freshness(published_at)
    event_type = raw.get("event_type")
    url = raw.get("url")

    return FeedItem(
        feed_id=feed_id,
        source_type=source_type,
        source_label=source_label,
        data_mode=data_mode,
        title=title or "",
        body=body,
        url=url,
        assets=assets,
        published_at=published_at,
        freshness=freshness,
        event_type=event_type,
    )


def load_feed(project_root: Optional[str] = None) -> FeedResult:
    """Load feed items from fixture data.

    No network access. No CSV file I/O (unless explicitly provided).
    Returns classified FeedItems with truth audit.
    """
    all_items: list[FeedItem] = []

    # Flash
    for raw in FLASH_FIXTURES:
        all_items.append(_build_item(raw, FeedSourceType.FLASH))

    # News
    for raw in NEWS_FIXTURES:
        all_items.append(_build_item(raw, FeedSourceType.NEWS))

    # Telegram (honestly empty)
    for raw in TELEGRAM_FIXTURES:
        all_items.append(_build_item(raw, FeedSourceType.TELEGRAM))

    # Fixture items
    for raw in FIXTURE_ITEMS:
        mode = raw.get("data_mode", "fixture")
        st = FeedSourceType.FLASH if raw.get("type") == "flash" else FeedSourceType.NEWS
        item = _build_item(raw, st)
        item.data_mode = FeedDataMode.FIXTURE
        all_items.append(item)

    # Deduplicate
    unique = deduplicate(all_items)
    duplicates = len(all_items) - len(unique)

    # Build truth
    truth = build_truth(unique)
    truth.total_raw_rows = len(all_items)

    # Count sources that are genuinely live (not fixture/research)
    live_sources = 0
    for item in unique:
        if item.data_mode == FeedDataMode.LIVE:
            live_sources += 1
    return FeedResult(
        items=unique,
        truth=truth,
        sources_ok=live_sources,
        sources_failed=0,
    )
