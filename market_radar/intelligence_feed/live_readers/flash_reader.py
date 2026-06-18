"""FlashReader — reads flash-style feed items from injected JSON/JSONL paths.

Contract (VERIFIED from FLASH_FIXTURES in feed_loader.py):
    Each source record must provide:
      - title: str
      - source_label: str
    Optional fields (never fabricated):
      - body: str | None
      - assets: list[str]
      - published_at: str | None  (UTC ISO 8601)
      - event_type: str | None
      - url: str | None

Input formats (injected path):
  - JSON:  list[dict]  — single JSON array of objects
  - JSONL: one JSON object per line, empty/skip lines tolerated

Design:
  - Single synchronous read_once() call
  - No daemon, no thread, no scheduler
  - Invalid rows are isolated and counted (not blocking the batch)
  - All fields use the same key names as FLASH_FIXTURES for compatibility
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.intelligence_feed.live_readers.protocol import (
    ReaderProtocol, ReaderBatchResult, ReaderStatus, _utc_now, _now_ms,
)
from market_radar.intelligence_feed.models import (
    FeedItem, FeedSourceType, FeedDataMode, make_feed_id, make_freshness,
)


class FlashReader(ReaderProtocol):
    """Read flash-style items from an injected JSON or JSONL file path.

    Args:
        source_path: Path to JSON or JSONL file.
        source_label: Override label (defaults to filename stem).
        limit: Max items to return (0 = no limit).
        reference_time: Deterministic time for freshness computation.
    """

    def __init__(
        self,
        source_path: str,
        source_label: Optional[str] = None,
        limit: int = 0,
        reference_time: Optional[datetime] = None,
    ):
        self._source_path = source_path
        self._label = source_label or os.path.splitext(os.path.basename(source_path))[0]
        self._limit = limit
        self._reference_time = reference_time

    @property
    def source_type(self) -> FeedSourceType:
        return FeedSourceType.FLASH

    @property
    def source_name(self) -> str:
        return f"flash:{self._label}"

    def read_once(self) -> ReaderBatchResult:
        started_at = _utc_now()
        start_ms = _now_ms()
        errors: list[str] = []

        if not os.path.isfile(self._source_path):
            return ReaderBatchResult(
                source_name=self.source_name,
                source_type=FeedSourceType.FLASH,
                status=ReaderStatus.UNAVAILABLE,
                errors=[f"File not found: {self._source_path}"],
                started_at=started_at,
                finished_at=_utc_now(),
            )

        raw_records: list[dict] = []
        try:
            raw_records = self._load_file()
        except (json.JSONDecodeError, OSError) as e:
            return ReaderBatchResult(
                source_name=self.source_name,
                source_type=FeedSourceType.FLASH,
                status=ReaderStatus.DEGRADED,
                errors=[f"Parse error: {e}"],
                started_at=started_at,
                finished_at=_utc_now(),
            )

        items: list[FeedItem] = []
        seen = 0
        rejected = 0

        for record in raw_records:
            seen += 1
            item = self._record_to_item(record)
            if item is None:
                rejected += 1
                continue
            items.append(item)
            if self._limit > 0 and len(items) >= self._limit:
                break

        latency = _now_ms() - start_ms

        status = ReaderStatus.OK if items else ReaderStatus.DEGRADED
        return ReaderBatchResult(
            source_name=self.source_name,
            source_type=FeedSourceType.FLASH,
            status=status,
            items=items,
            records_seen=seen,
            records_accepted=len(items),
            records_rejected=rejected,
            errors=errors,
            provenance=f"injected_path:{self._source_path}",
            started_at=started_at,
            finished_at=_utc_now(),
            data_mode=FeedDataMode.LIVE,
        )

    def _load_file(self) -> list[dict]:
        """Load records from JSON or JSONL file."""
        ext = os.path.splitext(self._source_path)[1].lower()
        with open(self._source_path, "r", encoding="utf-8") as f:
            if ext == ".jsonl":
                records: list[dict] = []
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        records.append(json.loads(stripped))
                    except json.JSONDecodeError:
                        # Skip malformed lines — don't block the batch
                        continue
                return records
            else:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
                return []

    def _record_to_item(self, record: dict) -> Optional[FeedItem]:
        """Convert a raw dict to FeedItem. Returns None if required fields missing."""
        title = record.get("title")
        if not title or not isinstance(title, str) or not title.strip():
            return None

        source_label = record.get("source_label") or self._label
        body = record.get("body")
        assets = record.get("assets", [])
        if not isinstance(assets, list):
            assets = [str(assets)] if assets else []
        published_at = record.get("published_at")
        url = record.get("url")
        event_type = record.get("event_type")

        # Build feed content for ID — use title + body + source_label
        id_content = (title or "") + ((body or "")[:200])
        feed_id = make_feed_id(id_content, source_label)
        freshness = make_freshness(published_at, reference_time=self._reference_time)

        return FeedItem(
            feed_id=feed_id,
            source_type=FeedSourceType.FLASH,
            source_label=source_label,
            data_mode=FeedDataMode.LIVE,
            title=title.strip(),
            body=str(body).strip() if body else None,
            url=url,
            assets=assets,
            published_at=published_at,
            freshness=freshness,
            event_type=event_type,
        )
