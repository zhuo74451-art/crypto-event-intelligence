# Curated API Reader R02

## Overview

The CuratedApiReader reads published, curated feed items from:

```
GET http://43.98.174.247:8001/api/integration/curated
```

This is the **primary production-ready feed entry point** for the W3 intelligence feed. It returns already-filtered, organized, and backend-published flash news, news articles, and Telegram messages.

---

## Interface Boundaries

| Endpoint | Role | Default Entry |
|----------|------|---------------|
| `/api/integration/curated` | **Primary** — published, filtered, ready-to-read items | ✅ Yes |
| `/api/integration/published` | Old interface — NOT the default entry | ❌ No |
| `/api/integration/ready` | Draft/unpublished data — must NOT enter live Feed | ❌ No |
| `/api/integration/items/{tweet_id}` | Debug/supplementary single-item lookup | 🔧 Optional |

---

## Server-Side Defaults (Current)

| Behavior | Default |
|----------|---------|
| Source filtering | None — all sources returned |
| Featured/special filtering | None — not excluded |
| `include_special_line` | Server default (client does NOT send by default) |
| `include_raw_json` | Not requested (large fields excluded) |

**Client default call sends NO source, exclude_source, content_type, include_special_line, or include_raw_json parameters.**

---

## Idempotency

Idempotency key: **tweet_id**

FeedItem.`original_id` always stores `tweet_id`. Feed ID is generated deterministically from `source + ":" + tweet_id`.

Rules:
- When `tweet_id` exists: it is the sole idempotency key
- When `tweet_id` is missing: item is **rejected**
- No UUID fallback, no array index fallback

---

## Incremental Cursor

Cursor field: **published_at_backend**

This is the backend's actual publish-success timestamp. The reader computes:
- `next_cursor = max(published_at_backend)` across all accepted items
- Only returned when the reader reaches `ok` or acceptable `degraded` status
- Not persisted by the reader (Integration layer handles storage)

---

## Title Fallback Chain

1. `zh_title`
2. `raw_title`
3. `delivery_payload.title`
4. `zh_short_title`
5. `delivery_payload.short_title`
6. Truncated body (max 80 chars, marked `derived_title=True`)
7. If all empty → **rejected** (no AI, no fabrication)

## Body Fallback Chain

1. `zh_body`
2. `extracted_text`
3. `raw_text`
4. `delivery_payload.body`
5. If all empty → **rejected** (title cannot masquerade as body)

## URL Fallback Chain

1. `canonical_url`
2. `article_url`

URL must pass `^https?://` safety check. Non-http URLs (`javascript:`, `data:`) are rejected.

---

## Source Mapping

| `source_kind` | `FeedSourceType` |
|---------------|------------------|
| `telegram` | TELEGRAM |
| `news` | NEWS |
| `flash` | FLASH |
| `webhook` | Via content_type → UNKNOWN fallback |
| other/unknown | UNKNOWN |

**Important**: Items from the curated API retain their individual source types. The reader does NOT label all items as "curated".

---

## Pagination

- Uses `offset`-based pagination
- Default page size: `limit=100` (max 500)
- Stops when: empty page, `offset >= total`, `max_pages` reached, or `max_items` reached
- Same `tweet_id` across pages → deduplicated
- No infinite loop protection (each page advances offset or stops)

---

## Error & Degradation Semantics

| Condition | Status | Items Returned |
|-----------|--------|----------------|
| HTTP 2xx, valid JSON, valid stage | OK | All valid items |
| HTTP 5xx | UNAVAILABLE | None |
| HTTP 4xx | DEGRADED | None |
| Timeout | UNAVAILABLE | None |
| Non-JSON response | DEGRADED | None |
| Oversized response (>10MB) | DEGRADED | None |
| Stage != "published" | DEGRADED | None |
| Page 1 OK, Page 2 fails | DEGRADED | Page 1 items |
| Single bad item | — | Other items, rejected counted |

---

## Security

- `db_path` is explicitly discarded — never enters output, logs, or FeedItem
- URLs validated against `^https?://` regex — non-http rejected
- Content passes through workbench renderer's CSP/escaping
- No credentials, no POST/PUT/DELETE
- Only `urllib` (stdlib) for HTTP — no `requests`, `httpx`, `aiohttp`

---

## Integration Guide (for downstream)

```python
from market_radar.intelligence_feed.live_readers import (
    CuratedApiReader, CuratedApiConfig,
    FlashReader, NewsReader, TelegramReader,
    read_all_once,
)

# Default read (no filters)
reader = CuratedApiReader()
result = reader.read_once()

# Aggregate with other readers
summary = read_all_once([
    CuratedApiReader(),
    FlashReader("/path/to/flash.json"),
    NewsReader("/path/to/news.csv"),
])

# Incremental read
config = CuratedApiConfig(since="2026-06-17T08:00:00+00:00")
result = CuratedApiReader(config).read_once()
# next_cursor = result._next_cursor
```

---

## Known Limitations

- CACHED data_mode not in FeedDataMode enum — use LIVE + health metadata
- No streaming or long-polling — one-shot synchronous only
- Pagination is offset-based, not cursor-based
- Response times can be slow (~9s per 100 items observed)
- Production timeout may need tuning (>15s for 2 pages)
