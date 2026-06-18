# Live Feed Source Contract Audit R01

**Audit Date:** 2026-06-17
**Repository:** zhuo74451-art/crypto-event-intelligence
**Branch:** workbench/mvpplus-feeds-market-ui-v2
**Auditor:** W3 Lane — Feed / Market / Workbench Owner

---

## Classification

| Status | Meaning |
|--------|---------|
| VERIFIED | Real code, schema, or data evidence exists in this repository |
| INFERRED | Can be reasonably deduced but not directly verified in repo |
| MISSING | No sufficient information exists in this repository |

---

## 1. Flash Source Contract

### Source Identity

| Field | Status | Evidence |
|-------|--------|----------|
| `FeedSourceType.FLASH` | VERIFIED | `market_radar/intelligence_feed/models.py:13` — `FLASH = "flash"` |
| source_label convention | VERIFIED | `feed_loader.py:46-74` — labels: `hl_watcher`, `onchain_watcher` |
| No live input path | MISSING | Only `FLASH_FIXTURES` exist; no verified live flash DB/JSONL path |

### Expected Data Shape (from FLASH_FIXTURES)

```python
{
    "title": str,                 # e.g. "Whale Matrixport Related increased BTC long +$12.5M"
    "body": str | None,           # Human-readable description
    "source_label": str,          # e.g. "hl_watcher", "onchain_watcher"
    "assets": list[str],          # e.g. ["BTC"], ["USDT", "BTC"]
    "published_at": str | None,   # UTC ISO 8601 or None
    "data_mode": str,             # "fixture" or "research_sample"
    "event_type": str | None,     # Optional classification
    "url": str | None,            # Optional source URL
}
```

### Supported Input Formats (for Reader)

| Format | Status | Evidence |
|--------|--------|----------|
| JSON array | VERIFIED | `FLASH_FIXTURES` is a `list[dict]`; identical format |
| JSONL per-line | INFERRED | Repo uses JSONL in `results/` and `data/`; natural fit |
| SQLite read-only | MISSING | No flash-specific SQLite DB exists |

### Classification: VERIFIED field contract; MISSING live input path.

---

## 2. News Source Contract

### Source Identity

| Field | Status | Evidence |
|-------|--------|----------|
| `FeedSourceType.NEWS` | VERIFIED | `models.py:14` — `NEWS = "news"` |
| source_label convention | VERIFIED | `feed_loader.py:86-126` — labels: `coindesk`, `theblock`, `cointelegraph`, `research_db` |
| RSS adapter | VERIFIED | `free_api_adapters.py:310-313` — RSS URLs for The Block, etc. |
| CSV column mapping | VERIFIED | `data/raw_news_column_mapping.json` — complete column contract |
| Live CSV files | VERIFIED | `data/raw_news_live_incremental.csv`, `data/raw_news_real_*.csv` |
| Binance article API | VERIFIED | `free_api_adapters.py:524-540` — public API returning `{title, id, type}` |

### Expected Data Shape (from NEWS_FIXTURES + raw_news_column_mapping)

```python
{
    "title": str,                 # Article title
    "content": str | None,        # Article body/content
    "source": str,                # Source name (maps to source_label)
    "url": str | None,            # source_url — may be empty, never fabricated
    "published_at": str | None,   # UTC ISO 8601
    "source_published_at": str,   # Original source timestamp
    "source_timezone": str,       # Original timezone
    "language": str,              # Language code
    "author": str | None,         # Author name
    "category": str,              # Category label
    "tags": str,                  # Comma-separated tags
    "data_mode": str,             # "fixture" or "research_sample"
}
```

### Supported Input Formats (for Reader)

| Format | Status | Evidence |
|--------|--------|----------|
| JSON array | VERIFIED | `NEWS_FIXTURES` is a `list[dict]` |
| JSONL per-line | INFERRED | Fits the repo's established JSONL pattern |
| CSV columns | VERIFIED | `raw_news_column_mapping.json` with 12 columns; CSV files exist |
| RSS XML | VERIFIED | `free_api_adapters.py:473-522` — `_fetch_rss()` returning `list[dict]` |

### Classification: VERIFIED field contract; VERIFIED CSV/JSON/RSS input formats.

---

## 3. Telegram Source Contract

### Source Identity

| Field | Status | Evidence |
|-------|--------|----------|
| `FeedSourceType.TELEGRAM` | VERIFIED | `models.py:15` — `TELEGRAM = "telegram"` |
| Send chain | VERIFIED | `sender_contract.py`, `telegram_publisher.py` — full send pipeline |
| Honest fixture | VERIFIED | `TELEGRAM_FIXTURES = []` in `feed_loader.py:128` |

### Send-Tracking SQLite (`data/local_news_flow_tg_sent_state.sqlite`)

| Column | Type | Status |
|--------|------|--------|
| `content_hash` | TEXT | VERIFIED |
| `sent_at` | TEXT | VERIFIED |
| `chat_id` | TEXT | VERIFIED |
| `msg_id` | TEXT | VERIFIED |
| `status` | TEXT | VERIFIED |
| `error` | TEXT | VERIFIED |

### Expected Message Shape (inferred from send + publisher code)

```python
{
    "message_id": int | str,      # Telegram message ID (verified in publisher)
    "chat_id": int | str,         # Chat/channel ID
    "text": str | None,           # Message text content
    "date": str | int,            # Unix timestamp or ISO string
    "title": str | None,          # Optional message title
    "source_label": str,          # "telegram_channel" or channel name
}
```

### Supported Input Formats (for Reader)

| Format | Status | Evidence |
|--------|--------|----------|
| SQLite read-only | VERIFIED | `local_news_flow_tg_sent_state.sqlite` exists with known schema |
| JSONL logged messages | INFERRED | `published_history.jsonl` has TG publish records |
| Telegram Desktop DB | MISSING | No `tdata/` or `D877F783D5D3EF8C` path in repo |

### Classification: VERIFIED send state SQLite; INFERRED message shape; MISSING incoming message DB.

---

## 4. Cross-Cutting Contracts

### FeedItem (existing W3 model — VERIFIED)

| Field | Type | Required | Source |
|-------|------|----------|--------|
| `feed_id` | str | yes | `make_feed_id(title+body, source_label)` — deterministic SHA256 |
| `source_type` | FeedSourceType | yes | Enum: FLASH / NEWS / TELEGRAM / UNKNOWN |
| `source_label` | str | yes | Human-readable source name |
| `data_mode` | FeedDataMode | yes | LIVE / CACHED / FIXTURE / RESEARCH_SAMPLE / UNKNOWN |
| `title` | str | yes | Content title |
| `body` | Optional[str] | no | Content body |
| `url` | Optional[str] | no | Source URL (never fabricated) |
| `assets` | list[str] | yes | Related asset symbols |
| `published_at` | Optional[str] | no | UTC ISO 8601 (None = unknown) |
| `ingested_at` | Optional[str] | no | UTC ISO 8601 |
| `freshness` | Freshness | yes | FRESH / STALE / UNKNOWN |
| `event_type` | Optional[str] | no | Event classification |
| `dedup_group` | Optional[str] | no | Duplicate grouping hint |
| `original_id` | Optional[str] | no | Source system's own ID |

### Provenance & Data Mode Rules (VERIFIED)

| Rule | Source |
|------|--------|
| `data_mode=live` only for real reader success | `truth_audit.py:73-79` |
| `data_mode=fixture` for all test/sample data | `truth_audit.py:82-83` |
| `data_mode=research_sample` for research data | `truth_audit.py:84-85` |
| `data_mode=cached` not in FeedDataMode enum | `models.py:23-28` — only LIVE/FIXTURE/RESEARCH_SAMPLE/UNKNOWN |
| Fixture never counts as live | `truth_audit.py:73-85` — separate counters |
| Research_sample excluded from live counts | `truth_audit.py:84-85` |
| Future timestamp → UNKNOWN | `models.py:112-114` |
| `published_at=None` → stays None | `models.py:57` — never replaced with current time |
| `feed_id` is deterministic, not random | `models.py:84-87` — `fi_` + SHA256 |
| `source_url` must not be fabricated | Implicit in field contract; no default value |

### FeedDataMode Gap (VERIFIED / MISSING)

```
FeedDataMode (current): LIVE | FIXTURE | RESEARCH_SAMPLE | UNKNOWN
```

**MISSING:** `CACHED` is not in the enum despite being referenced in `_BADGE_STYLES` in `renderer.py:92`. Per ticket rules:
> 不得擅自扩大 Enum
> 使用现有最接近且诚实的模式
> 在 ReaderHealth / metadata 中明确 cached

**Decision:** Use `FeedDataMode.LIVE` for live reader output, document cache metadata in `ReaderHealth`. Do NOT add CACHED to enum.

---

## 5. Files Outside Owned Paths (for this ticket)

No files outside allowed paths (`market_radar/intelligence_feed/**`, `tests/mvpplus/feeds_market_ui/**`, `docs/feeds_market_ui/**`, `scripts/mvpplus/feeds_market_ui/**`, `artifacts/evidence/w3_*.json`) are modified.

---

## 6. Summary

| Source | Field Contract | Live Input Path | Reader Feasible |
|--------|---------------|----------------|-----------------|
| Flash | VERIFIED | MISSING (injected path) | ✅ — JSON/JSONL reader with injected path |
| News | VERIFIED | VERIFIED (CSV/JSON/RSS) | ✅ — CSV/JSON/JSONL reader with injected path |
| Telegram | INFERRED | VERIFIED (SQLite) | ✅ — SQLite read-only reader with injected path |

**Verdict:** Sufficient contracts exist. Proceeding with Reader implementation.

All readers will:
- Accept input paths via constructor injection
- Never hardcode production paths
- Use only verified field contracts
- Output standard `FeedItem` instances
- Mark `data_mode=LIVE` only for real successful reads
