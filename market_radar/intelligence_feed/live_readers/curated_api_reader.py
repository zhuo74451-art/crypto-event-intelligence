"""CuratedApiReader — reads curated feed items from a remote HTTP API.

Main endpoint: GET /api/integration/curated

Business rules:
  - Default call sends NO source/exclude_source/content_type filters
  - Default does NOT send include_special_line (server default applies)
  - Default does NOT send include_raw_json
  - Each item retains its own source/source_kind/source_category — NOT all "curated"
  - is_featured is metadata only — does not increase factual trust
  - Pagination is bounded (max_pages, max_items, total, empty-page)

Design:
  - Single synchronous read_once() call with bounded pagination
  - Uses urllib only (no requests, no external HTTP deps)
  - Invalid items isolated without blocking the batch
  - tweet_id is the idempotency key
  - published_at_backend is the cursor field
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from market_radar.intelligence_feed.live_readers.protocol import (
    ReaderProtocol, ReaderBatchResult, ReaderStatus, _utc_now, _now_ms,
)
from market_radar.intelligence_feed.models import (
    FeedItem, FeedSourceType, FeedDataMode, make_feed_id, make_freshness,
)

# Default maximum response size: 10 MB
_DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024
_DEFAULT_USER_AGENT = "CEI-W3-CuratedApiReader/1.0"


# ── Source kind mapping ────────────────────────────────────────────────────────

_SOURCE_KIND_MAP: dict[str, FeedSourceType] = {
    "telegram": FeedSourceType.TELEGRAM,
    "news": FeedSourceType.NEWS,
    "flash": FeedSourceType.FLASH,
    # webhook → mapped by content_type/source_category; falls to UNKNOWN
}

_CONTENT_TYPE_TO_SOURCE: dict[str, FeedSourceType] = {
    "flash": FeedSourceType.FLASH,
    "news": FeedSourceType.NEWS,
    "telegram": FeedSourceType.TELEGRAM,
    "twitter": FeedSourceType.NEWS,
    "article": FeedSourceType.NEWS,
    "announcement": FeedSourceType.NEWS,
}


@dataclass
class CuratedApiConfig:
    """Configuration for the CuratedApiReader.

    All parameters map directly to the curated API query parameters.
    """
    base_url: str = "http://43.98.174.247:8001/api/integration/curated"
    limit: int = 100
    max_pages: int = 5
    max_items: int = 500
    timeout_seconds: int = 10
    since: Optional[str] = None
    source: Optional[str] = None
    exclude_source: Optional[str] = None
    content_type: Optional[str] = None
    q: Optional[str] = None
    include_special_line: Optional[bool] = None  # None = don't send param
    include_raw_json: bool = False
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES
    user_agent: str = _DEFAULT_USER_AGENT


class CuratedApiReader(ReaderProtocol):
    """Read curated feed items from the remote API.

    Args:
        config: CuratedApiConfig instance with connection and filter settings.
        source_label: Override source label (default: "curated_api").
        reference_time: Deterministic time for freshness computation.
    """

    def __init__(
        self,
        config: Optional[CuratedApiConfig] = None,
        source_label: Optional[str] = None,
        reference_time: Optional[datetime] = None,
    ):
        self._config = config or CuratedApiConfig()
        self._label = source_label or "curated_api"
        self._reference_time = reference_time

    @property
    def source_type(self) -> FeedSourceType:
        return FeedSourceType.UNKNOWN  # Aggregated — individual items carry real types

    @property
    def source_name(self) -> str:
        return f"curated_api:{self._label}"

    # ── Public entry point ─────────────────────────────────────────────────────

    def read_once(self) -> ReaderBatchResult:
        started_at = _utc_now()
        start_ms = _now_ms()
        errors: list[str] = []
        all_items: list[FeedItem] = []
        seen_ids: set[str] = set()
        total_seen = 0
        total_rejected = 0
        max_published_at_backend: Optional[str] = None

        cfg = self._config
        offset = 0
        pages_fetched = 0
        remote_total: Optional[int] = None

        while True:
            # Bounds check
            if pages_fetched >= cfg.max_pages:
                errors.append(f"Stopped: reached max_pages={cfg.max_pages}")
                break
            if cfg.max_items > 0 and len(all_items) >= cfg.max_items:
                errors.append(f"Stopped: reached max_items={cfg.max_items}")
                break
            if remote_total is not None and offset >= remote_total:
                break

            # Fetch one page
            page_result = self._fetch_page(cfg, offset, started_at)
            if page_result.status == ReaderStatus.UNAVAILABLE:
                if len(all_items) == 0:
                    return self._finalize(
                        page_result.status, [], total_seen, total_rejected,
                        errors + page_result.errors, started_at, start_ms,
                    )
                else:
                    # Partial success: return degraded with collected items
                    errors.append(f"Page {pages_fetched + 1} unavailable after {len(all_items)} accepted items")
                    break

            if page_result.status == ReaderStatus.DEGRADED and len(page_result.items_data) == 0:
                if len(all_items) == 0:
                    return self._finalize(
                        page_result.status, [], total_seen, total_rejected,
                        errors + page_result.errors, started_at, start_ms,
                    )
                errors.extend(page_result.errors)
                break

            pages_fetched += 1
            remote_total = page_result.meta.get("total")

            # Process items
            for item_data in page_result.items_data:
                total_seen += 1
                item = self._build_feed_item(item_data)
                if item is None:
                    total_rejected += 1
                    continue

                # Dedup by tweet_id across pages
                tid = str(item_data.get("tweet_id", ""))
                if tid and tid in seen_ids:
                    continue
                if tid:
                    seen_ids.add(tid)

                all_items.append(item)

                # Track max published_at_backend for cursor
                pub_back = item_data.get("published_at_backend")
                if pub_back and isinstance(pub_back, str):
                    if max_published_at_backend is None or pub_back > max_published_at_backend:
                        max_published_at_backend = pub_back

                if cfg.max_items > 0 and len(all_items) >= cfg.max_items:
                    break

            # Check for empty page
            if not page_result.items_data:
                break

            # Advance offset
            offset += cfg.limit

        latency = _now_ms() - start_ms

        # Partial success with errors → degraded, not ok
        has_errors = bool(errors)
        status = ReaderStatus.DEGRADED if has_errors else \
                 ReaderStatus.OK if all_items else ReaderStatus.DEGRADED
        result = ReaderBatchResult(
            source_name=self.source_name,
            source_type=FeedSourceType.UNKNOWN,
            status=status,
            items=all_items,
            records_seen=total_seen,
            records_accepted=len(all_items),
            records_rejected=total_rejected,
            errors=errors,
            provenance="transport=curated_api",
            started_at=started_at,
            finished_at=_utc_now(),
            data_mode=FeedDataMode.LIVE,
        )
        # Attach metadata for cursor
        result._next_cursor = max_published_at_backend  # type: ignore[attr-defined]
        result._pages = pages_fetched  # type: ignore[attr-defined]
        result._meta = {  # type: ignore[attr-defined]
            "pages_fetched": pages_fetched,
            "max_published_at_backend": max_published_at_backend,
        }
        return result

    # ── HTTP fetch ─────────────────────────────────────────────────────────────

    def _fetch_page(self, cfg: CuratedApiConfig, offset: int, trace_id: str) -> _PageResult:
        """Fetch a single page from the curated API."""
        params = {
            "limit": str(min(cfg.limit, 500)),
            "offset": str(offset),
        }
        if cfg.since:
            params["since"] = cfg.since
        if cfg.source is not None:
            params["source"] = cfg.source
        if cfg.exclude_source is not None:
            params["exclude_source"] = cfg.exclude_source
        if cfg.content_type is not None:
            params["content_type"] = cfg.content_type
        if cfg.q is not None:
            params["q"] = cfg.q
        if cfg.include_special_line is True:
            params["include_special_line"] = "1"
        elif cfg.include_special_line is False:
            params["include_special_line"] = "0"
        # include_raw_json defaults to False; only send when True
        if cfg.include_raw_json:
            params["include_raw_json"] = "1"

        query = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        url = f"{cfg.base_url}?{query}"

        req = urllib.request.Request(url, headers={"User-Agent": cfg.user_agent})

        try:
            resp = urllib.request.urlopen(req, timeout=cfg.timeout_seconds)
        except urllib.error.HTTPError as e:
            return _PageResult(
                status=ReaderStatus.UNAVAILABLE if e.code >= 500 else ReaderStatus.DEGRADED,
                errors=[f"HTTP {e.code} from {cfg.base_url}"],
            )
        except urllib.error.URLError as e:
            return _PageResult(
                status=ReaderStatus.UNAVAILABLE,
                errors=[f"URL error: {e.reason}"],
            )
        except OSError as e:
            return _PageResult(
                status=ReaderStatus.UNAVAILABLE,
                errors=[f"Network error: {e}"],
            )

        # Check response size
        try:
            raw = resp.read(cfg.max_response_bytes + 1)
        except OSError as e:
            return _PageResult(
                status=ReaderStatus.DEGRADED,
                errors=[f"Read error: {e}"],
            )

        if len(raw) > cfg.max_response_bytes:
            return _PageResult(
                status=ReaderStatus.DEGRADED,
                errors=[f"Response exceeds max_response_bytes={cfg.max_response_bytes}"],
            )

        # Parse JSON
        try:
            data = json.loads(raw.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return _PageResult(
                status=ReaderStatus.DEGRADED,
                errors=[f"JSON parse error: {e}"],
            )

        if not isinstance(data, dict):
            return _PageResult(
                status=ReaderStatus.DEGRADED,
                errors=["Response is not a JSON object"],
            )

        # Validate stage
        stage = data.get("stage")
        if stage and stage != "published":
            return _PageResult(
                status=ReaderStatus.DEGRADED,
                errors=[f"Stage is '{stage}', not 'published'"],
            )

        items_raw = data.get("items")
        if not isinstance(items_raw, list):
            return _PageResult(
                status=ReaderStatus.DEGRADED,
                errors=["items is missing or not an array"],
            )

        total = data.get("total")
        if total is not None:
            try:
                total = int(total)
            except (ValueError, TypeError):
                total = None

        # Discard db_path
        _ = data.get("db_path")  # explicitly not used

        return _PageResult(
            status=ReaderStatus.OK,
            items_data=items_raw,
            meta={"total": total, "offset": offset, "limit": cfg.limit},
        )

    # ── Item mapping ───────────────────────────────────────────────────────────

    def _build_feed_item(self, item_data: dict) -> Optional[FeedItem]:
        """Convert a raw API item dict to a FeedItem. Returns None if rejected."""
        # Idempotency key: tweet_id is required
        tweet_id = item_data.get("tweet_id")
        if tweet_id is None:
            return None

        tweet_id_str = str(tweet_id)
        source = item_data.get("source", "unknown")
        source_label = item_data.get("source_label") or source

        # Stable feed_id from source + tweet_id
        feed_id = make_feed_id(f"{source}:{tweet_id_str}", "curated")

        # Title with fallback
        title = (
            item_data.get("zh_title")
            or item_data.get("raw_title")
            or self._get_nested(item_data, "delivery_payload", "title")
            or item_data.get("zh_short_title")
            or self._get_nested(item_data, "delivery_payload", "short_title")
        )
        derived_title = False
        if not title:
            # Generate safe truncated display title from body
            body_for_title = (
                item_data.get("zh_body")
                or item_data.get("extracted_text")
                or item_data.get("raw_text")
                or self._get_nested(item_data, "delivery_payload", "body")
            )
            if body_for_title and isinstance(body_for_title, str):
                title = body_for_title[:80] + ("…" if len(body_for_title) > 80 else "")
                derived_title = True
            else:
                return None  # No title and no body to derive from — reject
        title_str = str(title).strip() if title else ""

        # Body with fallback
        body = (
            item_data.get("zh_body")
            or item_data.get("extracted_text")
            or item_data.get("raw_text")
            or self._get_nested(item_data, "delivery_payload", "body")
        )
        if not body:
            return None  # No body content — reject
        body_str = str(body).strip() if body else ""

        # URL with fallback — must pass safety check
        import re as _re
        _safe_url_re = _re.compile(r"^https?://", _re.IGNORECASE)
        raw_url = item_data.get("canonical_url") or item_data.get("article_url")
        url: Optional[str] = None
        if raw_url and isinstance(raw_url, str):
            raw_url = raw_url.strip()
            if raw_url and _safe_url_re.match(raw_url):
                url = raw_url

        # Source type via source_kind mapping
        source_kind = (item_data.get("source_kind") or "").lower()
        source_type = _SOURCE_KIND_MAP.get(source_kind)
        if source_type is None:
            raw_ct = item_data.get("content_type")
            content_type = raw_ct.lower() if raw_ct else ""
            source_type = _CONTENT_TYPE_TO_SOURCE.get(content_type, FeedSourceType.UNKNOWN)

        # Timestamps
        published_at = item_data.get("published_at") or item_data.get("tweet_created_at")
        published_at_backend = item_data.get("published_at_backend")

        # Freshness computed from published_at if available, else backend
        freshness_ref = published_at or published_at_backend
        freshness = make_freshness(freshness_ref, reference_time=self._reference_time)

        # Ingested_at: use published_at_backend if available
        ingested_at = published_at_backend

        # Build metadata
        metadata: dict[str, Any] = {
            "tweet_id": tweet_id_str,
            "source": source,
            "source_category": item_data.get("source_category"),
            "source_kind": source_kind,
            "content_type": item_data.get("content_type"),
            "source_id": item_data.get("source_id"),
            "author_username": item_data.get("author_username"),
            "raw_author": item_data.get("raw_author"),
            "tweet_created_at": item_data.get("tweet_created_at"),
            "published_at": item_data.get("published_at"),
            "fetched_at": item_data.get("fetched_at"),
            "received_at": item_data.get("received_at"),
            "published_at_backend": published_at_backend,
            "hermes_category": item_data.get("hermes_category"),
            "editorial_categories": item_data.get("editorial_categories"),
            "is_featured": item_data.get("is_featured"),
            "pipeline_stage": item_data.get("pipeline_stage"),
            "filter_status": item_data.get("filter_status"),
            "dedupe_status": item_data.get("dedupe_status"),
            "bridge_status": item_data.get("bridge_status"),
            "publish_block_reason": item_data.get("publish_block_reason"),
            "backend_upload_status": item_data.get("backend_upload_status"),
            "backend_error": item_data.get("backend_error"),
            "event_fingerprint": item_data.get("event_fingerprint"),
            "transport": "curated_api",
        }
        if derived_title:
            metadata["derived_title"] = True

        # Classification rules
        pipeline_stage = item_data.get("pipeline_stage")
        if pipeline_stage and pipeline_stage != "published":
            return None  # Only accept published items

        backend_upload_status = item_data.get("backend_upload_status")
        if backend_upload_status and str(backend_upload_status).lower() in ("failed", "error"):
            return None  # Explicitly failed uploads

        # Build FeedItem
        item = FeedItem(
            feed_id=feed_id,
            source_type=source_type,
            source_label=source_label,
            data_mode=FeedDataMode.LIVE,
            title=title_str,
            body=body_str,
            url=url,
            assets=[],
            published_at=published_at,
            ingested_at=ingested_at,
            freshness=freshness,
            original_id=tweet_id_str,
        )
        # Store metadata
        item._metadata = metadata  # type: ignore[attr-defined]
        return item

    def _get_nested(self, data: dict, *keys: str) -> Any:
        """Safely get a nested dict value."""
        current: Any = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current

    def _finalize(
        self,
        status: ReaderStatus,
        items: list[FeedItem],
        seen: int,
        rejected: int,
        errors: list[str],
        started_at: str,
        start_ms: float,
    ) -> ReaderBatchResult:
        latency = _now_ms() - start_ms
        return ReaderBatchResult(
            source_name=self.source_name,
            source_type=FeedSourceType.UNKNOWN,
            status=status,
            items=items,
            records_seen=seen,
            records_accepted=len(items),
            records_rejected=rejected,
            errors=errors,
            provenance="transport=curated_api",
            started_at=started_at,
            finished_at=_utc_now(),
            data_mode=FeedDataMode.LIVE,
        )


@dataclass
class _PageResult:
    """Internal result for a single HTTP page fetch."""
    status: ReaderStatus
    items_data: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
