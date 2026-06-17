# Feed Provider Integration Contract — R06

## Purpose

Define how any Feed Reader (including W3 CuratedApiReader) registers as a
`FeedProviderProtocol` so the Integration one-shot can consume live feed data
without repeating the refactor.

---

## Provider Input (`FeedProviderInput`)

| Field | Type | Description |
|-------|------|-------------|
| `since_cursor` | `Optional[str]` | Cursor from previous run. `None` on first run. |
| `limit` | `int` | Max records to fetch in this call. Default 100. |
| `max_items` | `int` | Max items to accept. Default 500. |
| `timeout_seconds` | `float` | Bounded timeout for the Provider's own HTTP/IO. |
| `run_id` | `str` | Current Integration run ID for provenance. |
| `no_send` | `bool` | Always `True` — Provider must not send. |
| `mode` | `str` | `"fixture"` or `"live-public"`. |

---

## Provider Output (`IntegrationFeedBatch`)

| Field | Type | Description |
|-------|------|-------------|
| `provider_name` | `str` | Short label, e.g. `"curated_api"`. |
| `overall_status` | `str` | `"ok"` / `"degraded"` / `"unavailable"`. |
| `records_seen` | `int` | Total records examined. |
| `records_accepted` | `int` | Records that passed validation. |
| `records_rejected` | `int` | Records that failed validation. |
| `live_count` | `int` | Items with `FeedDataMode.LIVE`. |
| `fixture_count` | `int` | Items with `FeedDataMode.FIXTURE`. |
| `research_count` | `int` | Items with `FeedDataMode.RESEARCH_SAMPLE`. |
| `cached_count` | `int` | Items served from cache. |
| `items` | `list[FeedItem]` | Accepted items using **W3 FeedItem** type. |
| `source_statuses` | `list[dict]` | Per-source health: `{"source", "status", "ok", "latency_ms", "error", "detail"}`. |
| `next_cursor` | `Optional[str]` | Opaque cursor for the next incremental fetch. |
| `cursor_safe` | `bool` | `True` = safe to advance cursor even when degraded. |
| `provenance` | `str` | Provenance tag for Workbench. |
| `errors` | `list[str]` | Non-fatal error messages. |
| `started_at` / `finished_at` | `str` | ISO timestamps. |

---

## FeedItem Requirements

Provider must return `market_radar.intelligence_feed.models.FeedItem` instances.
The Integration layer forwards them unchanged to Workbench.

Integration does NOT:
- Re-parse items
- Re-generate `feed_id`
- Change `source_label` or `source_type`
- Change `data_mode`
- Store full item bodies in the run report

---

## Cursor Rules

| # | Rule |
|---|------|
| 1 | First run with no state → `since_cursor=None` |
| 2 | Provider returns `next_cursor` → atomically persisted |
| 3 | Provider degraded + `cursor_safe=true` → may advance |
| 4 | Provider failed/unavailable → **do not advance** |
| 5 | No `next_cursor` → **do not advance** |
| 6 | Exception during run → **do not overwrite** previous cursor |
| 7 | New cursor < old cursor → reject, record error |
| 8 | Same cursor → idempotent, allowed |
| 9 | Corrupt cursor state → start from `None`, record degraded |
| 10 | Persist via `atomic_write_json` |

---

## Status Truth Matrix

| Provider Status | Source Status | Overall Effect |
|----------------|--------------|----------------|
| `ok` (≥1 source ok) | `ok` | Feed contributes to `completed` |
| `ok` (0 items, normal empty) | `ok` | Not degraded |
| `degraded` (partial sources) | `degraded` | Overall → `degraded` |
| `unavailable` (all sources down) | `unavailable` | Overall → `degraded` |
| Provider not configured | `degraded`, reason=not_connected | Overall → `degraded` |
| Provider raises | `degraded`, reason=exception | Overall → `degraded` |

---

## Multi-Source Semantics

- Provider may contain multiple internal sources (e.g. `news:jin10`, `telegram:channel_a`).
- Each internal source is recorded independently in `source_health`.
- One internal source failing does NOT fail the entire Provider.
- Integration never collapses multiple sources into a single `feed=ok`.

---

## Curated API Contract

When W3 CuratedApiReader registers as a Provider:

1. Wrap as a `FeedProviderProtocol` callable.
2. Input `since_cursor` → pass to the Reader's cursor parameter.
3. Output `IntegrationFeedBatch` using the Reader's results.
4. Curated API is **not** the only feed source — Provider abstraction allows multiple.
5. Integration never parses Curated API JSON directly.
6. Integration never stores full article bodies in the run report.
7. Default: one call per run, no loop, no retry, no scheduler.
8. No sending, no daemon, no background threads.

---

## W3 Integration Window

When `CuratedApiReader` is ready:

```python
from market_radar.intelligence_feed.reader import CuratedApiReader
from market_radar.integration.feed_provider_protocol import (
    FeedProviderInput, IntegrationFeedBatch,
)

def curated_provider(inp: FeedProviderInput) -> IntegrationFeedBatch:
    reader = CuratedApiReader(timeout=inp.timeout_seconds)
    result = reader.fetch(since=inp.since_cursor, limit=inp.limit)
    return IntegrationFeedBatch(
        provider_name="curated_api",
        overall_status="ok" if result.ok else "degraded",
        records_seen=result.total,
        records_accepted=len(result.items),
        items=result.items,
        next_cursor=result.next_cursor,
        ...
    )

# In one_shot:
result = run_one_shot(config, feed_provider=curated_provider)
```

No changes to `one_shot.py` required beyond passing the provider.

---

## Bounds

- `limit`: 1–500
- `max_items`: 1–5000
- `timeout_seconds`: > 0, finite
- `cursor_name`: non-empty string
- `no_send`: always `True`
- Items in Workbench: max 100
