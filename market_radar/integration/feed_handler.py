"""Feed handler — delegates to an injected Feed Provider.

Read-only: the Integration layer never fetches HTTP, never parses Curated API JSON.
Provider injection allows W3 CuratedApiReader (or any other) to register later
without repeating the one-shot refactor.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from market_radar.integration.models import (
    FeedResult, SourceRunStatus, IntegrationConfig,
)
from market_radar.integration.feed_provider_protocol import (
    FeedProviderProtocol,
    FeedProviderInput,
    IntegrationFeedBatch,
    FeedCursorState,
)
from market_radar.operations.atomic_json import atomic_write_json


# ── Legacy interface (preserved for backward compat) ──────────────────

def run_feed(mode: str) -> tuple[FeedResult, SourceRunStatus]:
    """Legacy feed handler for fixture mode. Delegates to not_connected for live.

    This function exists for backward compatibility with existing tests.
    New callers should use create_not_connected_feed() or run_feed_with_provider().
    """
    if mode == "fixture":
        return _fixture_mode()
    return create_not_connected_feed()


def _fixture_mode() -> tuple[FeedResult, SourceRunStatus]:
    """Fixture mode: load W3 fixture catalog data."""
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
        assets = metrics.get("assets", [])
        if assets:
            item["assets"] = assets
        items.append(item)
    fixture_count = len(items)
    return (
        FeedResult(data_mode="fixture", live_count=0, fixture_count=fixture_count,
                   research_count=0, items=items, status="ok"),
        SourceRunStatus(source="feed", status="ok", ok=True,
                        detail=f"fixture mode: {fixture_count} fixture items"),
    )


# ── Cursor State I/O ──────────────────────────────────────────────────

def _cursor_path(state_dir: Path, config: IntegrationConfig) -> Path:
    return state_dir / config.feed_cursor_state_file


def _load_cursor(state_dir: Path, config: IntegrationConfig) -> Optional[FeedCursorState]:
    """Load persistent cursor state. Returns None on missing/corrupt."""
    path = _cursor_path(state_dir, config)
    if not path.exists():
        return None
    try:
        with open(str(path), "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return None
        return FeedCursorState(
            cursor_name=raw.get("cursor_name", config.feed_cursor_name),
            cursor_value=raw.get("cursor_value"),
            updated_at=raw.get("updated_at", ""),
            provider_name=raw.get("provider_name", ""),
            last_successful_run_id=raw.get("last_successful_run_id", ""),
            accepted_count=raw.get("accepted_count", 0),
        )
    except Exception:
        return None


def _save_cursor(
    state_dir: Path,
    config: IntegrationConfig,
    batch: IntegrationFeedBatch,
    run_id: str,
    accepted_count: int,
    cursor_value: Optional[str],
) -> Optional[str]:
    """Atomically persist cursor state. Returns error string or None."""
    if batch.overall_status == "unavailable":
        return None  # Rule 4: failed/unavailable → no advance
    if batch.overall_status == "degraded" and not batch.cursor_safe:
        return None  # Rule 3: degraded + not safe → no advance
    if cursor_value is None:
        return None  # Rule 5: no next_cursor → no advance

    # Load existing for rollback check
    existing = _load_cursor(state_dir, config)
    if existing and existing.cursor_value is not None:
        # Rule 7: reject regression
        if cursor_value < existing.cursor_value:
            return "cursor regression rejected: new < old"

    state = FeedCursorState(
        cursor_name=config.feed_cursor_name,
        cursor_value=cursor_value,
        updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        provider_name=batch.provider_name,
        last_successful_run_id=run_id,
        accepted_count=accepted_count,
    )
    try:
        atomic_write_json(state.as_dict(), str(_cursor_path(state_dir, config)))
    except Exception as e:
        return f"cursor write failed: {e}"
    return None


# ── Main Feed Handler ────────────────────────────────────────────────

def create_not_connected_feed() -> tuple[FeedResult, SourceRunStatus]:
    """Return a degraded feed when no provider is configured."""
    feed = FeedResult(
        data_mode="live-public",
        live_count=0, fixture_count=0, research_count=0,
        items=[], status="degraded",
        error="existing_feed_readers_not_wired — see limitation in evidence",
    )
    src = SourceRunStatus(
        source="feed",
        status="degraded",
        ok=False,
        error="not_connected",
        detail="feed readers not wired",
    )
    return feed, src


def run_feed_with_provider(
    provider: FeedProviderProtocol,
    config: IntegrationConfig,
    state_dir: Path,
    run_id: str,
) -> tuple[FeedResult, SourceRunStatus, Optional[IntegrationFeedBatch],
           Optional[str], Optional[dict], list[SourceRunStatus]]:
    """Execute feed via injected provider with cursor management.

    Returns:
        (feed_result, source_status, raw_batch_or_None, cursor_error_or_None,
         feed_summary_dict_or_None, sub_sources)
    """
    # Load cursor — use persisted state first, then feed_initial_since as bootstrap
    cursor_state = _load_cursor(state_dir, config)
    if cursor_state and cursor_state.cursor_value:
        since_cursor = cursor_state.cursor_value
    elif config.feed_initial_since:
        since_cursor = config.feed_initial_since
    else:
        since_cursor = None
    cursor_before = since_cursor

    # Build input
    inp = FeedProviderInput(
        since_cursor=since_cursor,
        limit=config.feed_limit,
        max_items=config.feed_max_items,
        timeout_seconds=config.feed_timeout_seconds,
        run_id=run_id,
        no_send=True,
        mode=config.mode,
    )

    # Call provider once
    try:
        batch = provider(inp)
    except Exception as e:
        err_msg = f"feed provider raised: {type(e).__name__}: {e}"
        feed = FeedResult(
            data_mode=config.mode,
            live_count=0, fixture_count=0, research_count=0,
            items=[], status="degraded",
            error=err_msg,
        )
        src = SourceRunStatus(
            source="feed", status="degraded", ok=False,
            error=err_msg,
        )
        return feed, src, None, None, None, []

    # Determine feed-level status from batch
    if batch.overall_status == "ok":
        feed_status = "ok"
        feed_ok = True
    elif batch.overall_status == "unavailable":
        feed_status = "unavailable"
        feed_ok = False
    else:
        feed_status = "degraded"
        feed_ok = False

    feed = FeedResult(
        data_mode=config.mode,
        live_count=batch.live_count,
        fixture_count=batch.fixture_count,
        research_count=batch.research_count,
        items=[item.to_dict() if hasattr(item, 'to_dict') else
               {"feed_id": item.feed_id, "title": item.title,
                "source_type": item.source_type.value if hasattr(item.source_type, 'value') else str(item.source_type),
                "source_label": item.source_label,
                "data_mode": item.data_mode.value if hasattr(item.data_mode, 'value') else str(item.data_mode)}
               for item in batch.items[:config.feed_max_items]],
        status=feed_status,
        error="; ".join(batch.errors) if batch.errors else None,
    )

    src_detail_parts = []
    if batch.records_seen:
        src_detail_parts.append(f"{batch.records_seen} seen")
    if batch.records_accepted:
        src_detail_parts.append(f"{batch.records_accepted} accepted")
    if batch.errors:
        src_detail_parts.append(f"{len(batch.errors)} errors")

    src = SourceRunStatus(
        source="feed",
        status=feed_status,
        ok=feed_ok,
        detail=", ".join(src_detail_parts) if src_detail_parts else None,
        error=batch.errors[0] if batch.errors else None,
    )

    # Cursor persistence
    cursor_error = _save_cursor(
        state_dir, config, batch, run_id,
        accepted_count=batch.records_accepted,
        cursor_value=batch.next_cursor,
    )

    # Generate sub-source health entries
    sub_sources = []
    for ss in batch.source_statuses:
        sub_sources.append(SourceRunStatus(
            source=ss.get("source", "feed:unknown"),
            status=ss.get("status", "degraded"),
            ok=ss.get("ok", False),
            latency_ms=ss.get("latency_ms"),
            error=ss.get("error"),
            detail=ss.get("detail"),
        ))

    # Build feed_summary for report
    feed_summary = {
        "provider_name": batch.provider_name,
        "overall_status": batch.overall_status,
        "records_seen": batch.records_seen,
        "records_accepted": batch.records_accepted,
        "records_rejected": batch.records_rejected,
        "live_count": batch.live_count,
        "fixture_count": batch.fixture_count,
        "research_count": batch.research_count,
        "cached_count": batch.cached_count,
        "source_statuses": batch.source_statuses,
        "cursor_before": cursor_before,
        "cursor_after": batch.next_cursor,
        "cursor_advanced": batch.next_cursor is not None and batch.next_cursor != cursor_before,
        "initial_since": config.feed_initial_since,
        "errors": batch.errors,
    }

    return feed, src, batch, cursor_error, feed_summary, sub_sources
