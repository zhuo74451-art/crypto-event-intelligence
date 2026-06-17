"""Feed handler — fixture-only or live-public degraded feed mode.

Read-only: no credentials, no news API.
"""
from __future__ import annotations

from typing import Optional

from market_radar.integration.models import FeedResult, SourceRunStatus


def run_feed(mode: str) -> tuple[FeedResult, SourceRunStatus]:
    """Execute feed handler.

    In ``fixture`` mode: loads existing W3 fixture data.
    In ``live-public`` mode: reports feed not_connected — real feed readers
    (flash, news, TG) are not wired yet.
    """
    if mode == "fixture":
        return _fixture_mode()
    elif mode == "live-public":
        return _live_public_mode()
    else:
        return (
            FeedResult(data_mode=mode, live_count=0, fixture_count=0, research_count=0,
                       status="error", error=f"unknown mode: {mode}"),
            SourceRunStatus(source="feed", status="unavailable", ok=False,
                            error=f"unknown mode: {mode}"),
        )


def _fixture_mode() -> tuple[FeedResult, SourceRunStatus]:
    """Fixture mode: load W3 fixture data."""
    # Use the W3 fixture catalog data
    from market_radar.shared.adapter_contract import FixtureCatalog
    catalog = FixtureCatalog()

    items = []
    for family_key, fixture in catalog.fixtures.items():
        metrics = fixture.get("metrics", {})
        item = {
            "card_family": family_key,
            "title": fixture.get("asset_or_topic", ""),
            "source_refs": fixture.get("source_refs", []),
            "risk_notes": fixture.get("risk_notes", []),
        }
        # Extract assets from metrics where available
        assets = metrics.get("assets", [])
        if assets:
            item["assets"] = assets
        items.append(item)

    fixture_count = len(items)

    return (
        FeedResult(
            data_mode="fixture",
            live_count=0,
            fixture_count=fixture_count,
            research_count=0,
            items=items,
            status="ok",
        ),
        SourceRunStatus(
            source="feed",
            status="ok",
            ok=True,
            detail=f"fixture mode: {fixture_count} fixture items loaded, live_count=0",
        ),
    )


def _live_public_mode() -> tuple[FeedResult, SourceRunStatus]:
    """Live-public mode: feed readers not wired yet."""
    return (
        FeedResult(
            data_mode="live-public",
            live_count=0,
            fixture_count=0,
            research_count=0,
            items=[],
            status="degraded",
            error="feed readers not wired — existing flash/news/TG readers not connected",
        ),
        SourceRunStatus(
            source="feed",
            status="degraded",
            ok=False,
            detail="feed readers not wired",
            error="existing_feed_readers_not_wired — see limitation in evidence",
        ),
    )
