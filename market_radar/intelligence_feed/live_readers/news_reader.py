"""NewsReader — reads news-style feed items from injected JSON/JSONL/CSV paths.

Contract (VERIFIED from NEWS_FIXTURES + raw_news_column_mapping.json):
    Each source record must provide:
      - title: str
    Optional fields (never fabricated):
      - content / body: str | None
      - source / source_label: str
      - url: str | None          (never fabricated; None → no URL)
      - published_at: str | None (UTC ISO 8601)
      - language, author, category, tags

Input formats (injected path):
  - JSON:  list[dict]  — single JSON array of objects
  - JSONL: one JSON object per line
  - CSV:   rows with column mapping (title, content, url, published_at)

Design:
  - Single synchronous read_once() call
  - No daemon, no thread, no scheduler
  - Invalid rows isolated without blocking the batch
  - No fabricated URLs — source_url="" or None → url=None on FeedItem
"""

from __future__ import annotations

import csv
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


class NewsReader(ReaderProtocol):
    """Read news items from an injected JSON, JSONL, or CSV file path.

    Args:
        source_path: Path to data file.
        source_label: Override label (defaults to filename stem).
        limit: Max items to return (0 = no limit).
        reference_time: Deterministic time for freshness computation.
        csv_column_map: Optional mapping for CSV columns
                        (default: standard raw_news column mapping).
    """

    DEFAULT_CSV_MAP = {
        "title": "title",
        "content": "content",
        "body": "content",
        "source": "source",
        "source_label": "source",
        "url": "url",
        "source_url": "url",
        "published_at": "published_at",
        "language": "language",
        "author": "author",
        "category": "category",
        "tags": "tags",
    }

    def __init__(
        self,
        source_path: str,
        source_label: Optional[str] = None,
        limit: int = 0,
        reference_time: Optional[datetime] = None,
        csv_column_map: Optional[dict[str, str]] = None,
    ):
        self._source_path = source_path
        self._label = source_label or os.path.splitext(os.path.basename(source_path))[0]
        self._limit = limit
        self._reference_time = reference_time
        self._csv_map = csv_column_map or self.DEFAULT_CSV_MAP

    @property
    def source_type(self) -> FeedSourceType:
        return FeedSourceType.NEWS

    @property
    def source_name(self) -> str:
        return f"news:{self._label}"

    def read_once(self) -> ReaderBatchResult:
        started_at = _utc_now()
        start_ms = _now_ms()
        errors: list[str] = []

        if not os.path.isfile(self._source_path):
            return ReaderBatchResult(
                source_name=self.source_name,
                source_type=FeedSourceType.NEWS,
                status=ReaderStatus.UNAVAILABLE,
                errors=[f"File not found: {self._source_path}"],
                started_at=started_at,
                finished_at=_utc_now(),
            )

        raw_records: list[dict] = []
        try:
            raw_records = self._load_file()
        except (json.JSONDecodeError, OSError, csv.Error) as e:
            return ReaderBatchResult(
                source_name=self.source_name,
                source_type=FeedSourceType.NEWS,
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
            source_type=FeedSourceType.NEWS,
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
        ext = os.path.splitext(self._source_path)[1].lower()
        if ext == ".csv":
            return self._load_csv()
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
                        continue
                return records
            else:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
                return []

    def _load_csv(self) -> list[dict]:
        records: list[dict] = []
        with open(self._source_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(dict(row))
        return records

    def _record_to_item(self, record: dict) -> Optional[FeedItem]:
        title = self._get_field(record, "title")
        if not title or not isinstance(title, str) or not title.strip():
            return None

        source_label = self._get_field(record, "source_label") or self._get_field(record, "source") or self._label
        body = self._get_field(record, "body") or self._get_field(record, "content")
        url = self._get_field(record, "url") or self._get_field(record, "source_url")
        published_at = self._get_field(record, "published_at")
        language = self._get_field(record, "language")
        author = self._get_field(record, "author")
        category = self._get_field(record, "category")
        tags = self._get_field(record, "tags")

        # Do NOT fabricate URLs
        if url is not None and isinstance(url, str):
            url = url.strip()
            if not url:
                url = None

        # Build feed content for ID — use title + body excerpt
        id_content = (title or "") + ((body or "")[:200])
        feed_id = make_feed_id(id_content, source_label)
        freshness = make_freshness(published_at, reference_time=self._reference_time)

        # Build event_type from category if available
        event_type = category or None

        return FeedItem(
            feed_id=feed_id,
            source_type=FeedSourceType.NEWS,
            source_label=source_label,
            data_mode=FeedDataMode.LIVE,
            title=title.strip(),
            body=str(body).strip() if body else None,
            url=url,
            assets=[],
            published_at=published_at,
            freshness=freshness,
            event_type=event_type,
        )

    def _get_field(self, record: dict, key: str) -> Any:
        """Resolve field via csv_column_map, falling back to direct key access."""
        mapped = self._csv_map.get(key, key)
        return record.get(mapped) or record.get(key)
