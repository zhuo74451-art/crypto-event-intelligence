"""CuratedApiReader — reads curated feed items from a remote HTTP API.

Main endpoint: GET /api/integration/curated

Business rules:
  - Default call sends NO source/exclude_source/content_type filters
  - Default does NOT send include_special_line (server default applies)
  - Default does NOT send include_raw_json
  - Each item retains its own source/source_kind/source_category — NOT all "curated"
  - is_featured is metadata only — does not increase factual trust
  - Pagination is bounded (max_pages, max_items, total, empty-page)
  - Empty batch with HTTP 200 + empty items = ok (not degraded)
  - Public contract fields via ReaderBatchResult (no private attrs)
"""

from __future__ import annotations

import json
import os
import math
import re as _re
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

_DEFAULT_MAX_RESPONSE_BYTES = 10 * 1024 * 1024
_DEFAULT_USER_AGENT = "CEI-W3-CuratedApiReader/1.0"
_SAFE_URL_RE = _re.compile(r"^https?://", _re.IGNORECASE)

_SOURCE_KIND_MAP: dict[str, FeedSourceType] = {
    "telegram": FeedSourceType.TELEGRAM,
    "news": FeedSourceType.NEWS,
    "flash": FeedSourceType.FLASH,
}
_CONTENT_TYPE_TO_SOURCE: dict[str, FeedSourceType] = {
    "flash": FeedSourceType.FLASH,
    "news": FeedSourceType.NEWS,
    "telegram": FeedSourceType.TELEGRAM,
    "twitter": FeedSourceType.NEWS,
    "article": FeedSourceType.NEWS,
    "announcement": FeedSourceType.NEWS,
}


# ── Time helpers ───────────────────────────────────────────────────────────────

def _parse_utc(ts: Any) -> Optional[datetime]:
    """Parse a timestamp string into a timezone-aware UTC datetime.

    Supports Z, +00:00, +08:00, and fractional seconds.
    Returns None for unparseable values.
    """
    if not ts or not isinstance(ts, str):
        return None
    try:
        # Normalize Z to +00:00
        normalized = ts.replace("Z", "+00:00").strip()
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _format_utc(dt: datetime) -> str:
    """Format a datetime as UTC ISO 8601 with Z suffix."""
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Config ─────────────────────────────────────────────────────────────────────

@dataclass
class CuratedApiConfig:
    """Configuration for the CuratedApiReader.

    All parameters map directly to the curated API query parameters.
    Validated on construction via __post_init__.
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
    include_special_line: Optional[bool] = None
    include_raw_json: bool = False
    max_response_bytes: int = _DEFAULT_MAX_RESPONSE_BYTES
    user_agent: str = _DEFAULT_USER_AGENT

    def __post_init__(self) -> None:
        if isinstance(self.limit, bool):
            raise ValueError("limit must be a number, got bool: %s" % self.limit)
        if not 1 <= self.limit <= 500:
            raise ValueError("limit must be 1-500, got %s" % self.limit)
        if isinstance(self.max_pages, bool):
            raise ValueError("max_pages must be a number, got bool: %s" % self.max_pages)
        if not 1 <= self.max_pages <= 10:
            raise ValueError("max_pages must be 1-10, got %s" % self.max_pages)
        if isinstance(self.max_items, bool):
            raise ValueError("max_items must be a number, got bool: %s" % self.max_items)
        if not 1 <= self.max_items <= 5000:
            raise ValueError("max_items must be 1-5000, got %s" % self.max_items)
        if isinstance(self.timeout_seconds, bool):
            raise ValueError("timeout_seconds must be a finite number, got bool: %s" % self.timeout_seconds)
        if not isinstance(self.timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be a finite number, got %s: %s" % (type(self.timeout_seconds).__name__, self.timeout_seconds))
        if not math.isfinite(self.timeout_seconds):
            raise ValueError("timeout_seconds must be finite, got %s" % self.timeout_seconds)
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be >0, got %s" % self.timeout_seconds)
        if isinstance(self.max_response_bytes, bool):
            raise ValueError("max_response_bytes must be a number, got bool: %s" % self.max_response_bytes)
        if not isinstance(self.max_response_bytes, int) or self.max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be >0, got %s" % self.max_response_bytes)
        if not isinstance(self.base_url, str) or not _SAFE_URL_RE.match(self.base_url):
            raise ValueError(f"base_url must start with http:// or https://, got {self.base_url}")
        if self.include_special_line not in (None, True, False):
            raise ValueError(f"include_special_line must be None/True/False, got {self.include_special_line}")
        if not isinstance(self.include_raw_json, bool):
            raise ValueError(f"include_raw_json must be bool, got {type(self.include_raw_json).__name__}")


class CuratedApiReader(ReaderProtocol):
    """Read curated feed items from the remote API.

    All contract fields are exposed via ReaderBatchResult public fields:
      - next_cursor, cursor_safe, source_statuses, provider_name, metadata

    Args:
        config: CuratedApiConfig instance.
        source_label: Override source label.
        reference_time: Deterministic time for freshness.
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
        return FeedSourceType.UNKNOWN

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
        max_cursor_dt: Optional[datetime] = None
        cursor_has_invalid_time = False
        source_records: dict[str, dict] = {}
        pages_fetched = 0
        truncated = False
        remote_total: Optional[int] = None

        cfg = self._config
        offset = 0

        while True:
            # ── Bounds check ────────────────────────────────────────────────
            if pages_fetched >= cfg.max_pages:
                # Only truncated if there may be more data
                if remote_total is None or offset < remote_total:
                    truncated = True
                    errors.append(f"Truncated: reached max_pages={cfg.max_pages}")
                break
            if cfg.max_items > 0 and len(all_items) >= cfg.max_items:
                # Check if we've hit the total
                if remote_total is None or len(all_items) < remote_total:
                    truncated = True
                    errors.append(f"Truncated: reached max_items={cfg.max_items}")
                break
            if remote_total is not None and offset >= remote_total:
                # Normal completion — all pages read
                break

            # ── Fetch page ──────────────────────────────────────────────────
            page_result = self._fetch_page(cfg, offset)
            pages_fetched += 1

            if page_result.status == ReaderStatus.UNAVAILABLE:
                if len(all_items) == 0:
                    return self._build_result(
                        page_result.status, all_items, total_seen, total_rejected,
                        errors + page_result.errors, started_at, start_ms,
                        max_cursor_dt, cursor_has_invalid_time or True,
                        truncated or True, pages_fetched, source_records,
                    )
                errors.append(f"Page {pages_fetched} unavailable after {len(all_items)} items")
                truncated = True
                break

            if page_result.status == ReaderStatus.DEGRADED and len(page_result.items_data) == 0:
                # Parse-level failure — still check if we have partial items
                errors.extend(page_result.errors)
                if len(all_items) == 0:
                    return self._build_result(
                        page_result.status, all_items, total_seen, total_rejected,
                        errors, started_at, start_ms,
                        max_cursor_dt, cursor_has_invalid_time,
                        truncated, pages_fetched, source_records,
                    )
                truncated = True
                break

            if page_result.status == ReaderStatus.OK and not page_result.items_data:
                # Empty page is normal completion
                break

            remote_total = page_result.meta.get("total")

            # ── Process items ───────────────────────────────────────────────
            for item_data in page_result.items_data:
                total_seen += 1
                item, rejection = self._build_feed_item(item_data)
                if item is None:
                    total_rejected += 1
                    if rejection:
                        errors.append(rejection)
                    continue

                # Dedup by tweet_id across pages
                tid = str(item_data.get("tweet_id", ""))
                if tid and tid in seen_ids:
                    continue
                if tid:
                    seen_ids.add(tid)

                all_items.append(item)

                # Track per-source stats
                src_key = item.source_label or "unknown"
                if src_key not in source_records:
                    source_records[src_key] = {
                        "source": item.source_label,
                        "source_type": item.source_type.value,
                        "status": "ok",
                        "ok": True,
                        "accepted_count": 0,
                        "rejected_count": 0,
                        "detail": "",
                    }
                source_records[src_key]["accepted_count"] += 1

                # Cursor: parse published_at_backend
                raw_cursor = item_data.get("published_at_backend")
                cursor_dt = _parse_utc(raw_cursor)
                if cursor_dt is not None:
                    if max_cursor_dt is None or cursor_dt > max_cursor_dt:
                        max_cursor_dt = cursor_dt
                elif raw_cursor is not None:
                    cursor_has_invalid_time = True

                if cfg.max_items > 0 and len(all_items) >= cfg.max_items:
                    break

            # Check for empty items_data (parse succeeded but no items)
            if not page_result.items_data:
                break

            # Advance offset
            offset += cfg.limit

        # Determine status
        has_errors = bool(errors)
        if has_errors:
            status = ReaderStatus.DEGRADED
        elif truncated:
            status = ReaderStatus.DEGRADED
        else:
            status = ReaderStatus.OK

        cursor_safe = not truncated and not has_errors and not cursor_has_invalid_time
        next_cursor_str = _format_utc(max_cursor_dt) if max_cursor_dt else None

        return self._build_result(
            status, all_items, total_seen, total_rejected,
            errors, started_at, start_ms,
            max_cursor_dt, cursor_has_invalid_time,
            truncated, pages_fetched, source_records,
        )

    # ── HTTP fetch ─────────────────────────────────────────────────────────────

    def _fetch_page(self, cfg: CuratedApiConfig, offset: int) -> _PageResult:
        params: dict[str, str] = {
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

        # Stage must be "published"; missing stage is also degraded
        stage = data.get("stage")
        if not stage or stage != "published":
            return _PageResult(
                status=ReaderStatus.DEGRADED,
                errors=[f"Stage is '{stage}', not 'published'"] if stage
                        else ["Stage field missing from response"],
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

        return _PageResult(
            status=ReaderStatus.OK,
            items_data=items_raw,
            meta={"total": total, "offset": offset, "limit": cfg.limit},
        )

    # ── Item mapping ───────────────────────────────────────────────────────────

    def _build_feed_item(self, item_data: dict) -> tuple[Optional[FeedItem], Optional[str]]:
        """Convert raw API item to FeedItem. Returns (item, rejection_reason).

        Returns (None, reason) for rejected items. reason is used for error logs.
        """
        # Idempotency key: tweet_id is required
        tweet_id = item_data.get("tweet_id")
        if tweet_id is None:
            return None, "Rejected: missing tweet_id"

        tweet_id_str = str(tweet_id)
        source_raw = item_data.get("source", "unknown")
        source_label = item_data.get("source_label") or source_raw

        feed_id = make_feed_id(f"{source_raw}:{tweet_id_str}", "curated")

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
                return None, "Rejected: no title and no body to derive from"
        title_str = str(title).strip() if title else ""

        # Body with fallback
        body = (
            item_data.get("zh_body")
            or item_data.get("extracted_text")
            or item_data.get("raw_text")
            or self._get_nested(item_data, "delivery_payload", "body")
        )
        if not body:
            return None, "Rejected: no body content"
        body_str = str(body).strip() if body else ""

        # URL with safety check
        raw_url = item_data.get("canonical_url") or item_data.get("article_url")
        url: Optional[str] = None
        if raw_url and isinstance(raw_url, str):
            raw_url = raw_url.strip()
            if raw_url and _SAFE_URL_RE.match(raw_url):
                url = raw_url

        # Source type mapping
        source_kind = (item_data.get("source_kind") or "").lower()
        source_type = _SOURCE_KIND_MAP.get(source_kind)
        if source_type is None:
            raw_ct = item_data.get("content_type")
            ct = raw_ct.lower() if raw_ct else ""
            source_type = _CONTENT_TYPE_TO_SOURCE.get(ct, FeedSourceType.UNKNOWN)

        # Timestamps
        published_at = item_data.get("published_at") or item_data.get("tweet_created_at")
        published_at_backend = item_data.get("published_at_backend")
        freshness_ref = published_at or published_at_backend
        freshness = make_freshness(freshness_ref, reference_time=self._reference_time)
        ingested_at = published_at_backend

        # Pipeline stage check
        pipeline_stage = item_data.get("pipeline_stage")
        if pipeline_stage and pipeline_stage != "published":
            return None, f"Rejected: pipeline_stage={pipeline_stage}"

        # Upload status check
        backend_upload_status = item_data.get("backend_upload_status")
        if backend_upload_status and str(backend_upload_status).lower() in ("failed", "error"):
            return None, f"Rejected: backend_upload_status={backend_upload_status}"

        # Backend error check
        backend_error = item_data.get("backend_error")
        if backend_error and isinstance(backend_error, str) and backend_error.strip():
            return None, f"Rejected: backend_error={backend_error[:100]}"

        # Build metadata
        metadata: dict[str, Any] = {
            "tweet_id": tweet_id_str,
            "source": source_raw,
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
            "pipeline_stage": pipeline_stage,
            "filter_status": item_data.get("filter_status"),
            "dedupe_status": item_data.get("dedupe_status"),
            "bridge_status": item_data.get("bridge_status"),
            "publish_block_reason": item_data.get("publish_block_reason"),
            "backend_upload_status": backend_upload_status,
            "backend_error": backend_error,
            "event_fingerprint": item_data.get("event_fingerprint"),
            "transport": "curated_api",
        }
        if derived_title:
            metadata["derived_title"] = True

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
        item._metadata = metadata
        return item, None

    @staticmethod
    def _get_nested(data: dict, *keys: str) -> Any:
        current: Any = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current

    # ── Result builder ─────────────────────────────────────────────────────────

    def _build_result(
        self,
        status: ReaderStatus,
        items: list[FeedItem],
        seen: int,
        rejected: int,
        errors: list[str],
        started_at: str,
        start_ms: float,
        max_cursor_dt: Optional[datetime],
        cursor_has_invalid: bool,
        truncated: bool,
        pages: int,
        source_records: dict[str, dict],
    ) -> ReaderBatchResult:
        latency = _now_ms() - start_ms
        has_errors = bool(errors)
        cursor_safe = not truncated and not has_errors and not cursor_has_invalid

        next_cursor = _format_utc(max_cursor_dt) if max_cursor_dt else None
        cursor_invalid_count = 1 if cursor_has_invalid else 0

        # Build source_statuses list
        source_statuses = list(source_records.values())
        if not source_statuses:
            source_statuses = [{
                "source": "curated_api",
                "source_type": "unknown",
                "status": status.value,
                "ok": status.value == "ok",
                "accepted_count": len(items),
                "rejected_count": rejected,
                "detail": "aggregated — no per-source breakdown available" if not items else "",
            }]

        # Per-source degraded: keep successful sources ok, add aggregate
        if status == ReaderStatus.DEGRADED:
            has_individual_ok = any(ss.get("status") == "ok" for ss in source_statuses)
            if has_individual_ok:
                source_statuses.append({
                    "source": "curated_api",
                    "source_type": "unknown",
                    "status": "degraded",
                    "ok": False,
                    "accepted_count": len(items),
                    "rejected_count": rejected,
                    "detail": "aggregated transport-level degradation",
                })
            else:
                for ss in source_statuses:
                    ss["status"] = "degraded"
                    ss["ok"] = False

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
            next_cursor=next_cursor,
            cursor_safe=cursor_safe,
            source_statuses=source_statuses,
            provider_name="curated_api",
            metadata={
                "pages_fetched": pages,
                "truncated": truncated,
                "max_cursor_dt": _format_utc(max_cursor_dt) if max_cursor_dt else None,
                "cursor_has_invalid_time": cursor_has_invalid,
                "invalid_cursor_timestamp_count": cursor_invalid_count,
            },
        )


@dataclass
class _PageResult:
    """Internal result for a single HTTP page fetch."""
    status: ReaderStatus
    items_data: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
