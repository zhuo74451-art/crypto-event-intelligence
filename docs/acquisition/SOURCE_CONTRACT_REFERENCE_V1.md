# Source Contract Reference (V1)

> **Document Version:** 1.0  
> **Scope:** `SourceContract` schema — full field-by-field reference  
> **Status:** Ratified

---

## 1. Overview

A `SourceContract` is the declarative configuration object that defines **what** external data source to acquire, **how** to connect to it, **how** to interpret its responses, and **what policies** govern its acquisition lifecycle. Think of it as a "data source driver configuration."

Every acquisition run begins by loading a `SourceContract` from the registry.

---

## 2. Full Field Reference

### 2.1 Identity Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `UUID` | Yes | Unique identifier for this source contract |
| `name` | `string` | Yes | Human-readable name (e.g., "Binance BTC/USDT Ticker") |
| `description` | `string` | No | Free-text description of what this source provides |
| `version` | `string` | Yes | Semantic version of the contract schema (e.g., "1.0.0") |
| `created_at` | `DateTime` | Yes | When this contract was first registered |
| `updated_at` | `DateTime` | Yes | When this contract was last modified |

```json
{
  "id": "a1b2c3d4-...",
  "name": "Binance BTC/USDT Ticker",
  "description": "Real-time BTC/USDT price from Binance REST API",
  "version": "1.0.0",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

### 2.2 Connection Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `url` | `string` | Conditional | The URL to fetch. Required for `http`, `rss`, `rest` methods. |
| `method` | `string` | No | HTTP method (`GET`, `POST`). Default: `GET`. |
| `headers` | `map[string,string]` | No | HTTP headers to send. Values reference secret keys. |
| `body_template` | `string` | No | Request body template for POST requests (Jinja2 syntax). |
| `timeout_seconds` | `uint32` | No | Request timeout. Default: `30`. Max: `120`. |
| `retry_policy` | `RetryPolicy` | No | Retry configuration (see §2.10). |

```json
{
  "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
  "method": "GET",
  "headers": {
    "X-MBX-APIKEY": "${SECRET_BINANCE_API_KEY}"
  },
  "timeout_seconds": 30
}
```

### 2.3 Acquisition Method

| Field | Type | Required | Description |
|---|---|---|---|
| `acquisition_method` | `string` | Yes | How to fetch data. One of the values below. |

**Allowed values:**

| Value | Meaning | Typical Use |
|---|---|---|
| `http` | Single HTTP GET/POST request | REST APIs, JSON endpoints |
| `rss` | RSS/ATOM feed poll | News feeds, blog updates |
| `websocket` | Persistent WebSocket connection | Real-time price streams |
| `file` | Local or mounted file read | Log files, exported data |
| `changedetection` | Fetch via changedetection.io API | HTML pages with visual diffs |
| `archivebox` | Submit URL to ArchiveBox | Long-term archival |
| `poll` | Polling wrapper (internal) | Sources that need periodic re-fetch |

```json
{
  "acquisition_method": "http"
}
```

### 2.4 Timestamp Capability Fields

These fields declare what timestamp information the source is **capable** of providing. They influence the five-timestamp model resolution.

| Field | Type | Required | Description |
|---|---|---|---|
| `supports_published_at` | `bool` | No | Source provides a publish timestamp. Default: `false`. |
| `supports_updated_at` | `bool` | No | Source provides a last-modified timestamp. Default: `false`. |
| `trust_published_at` | `bool` | No | Whether to trust the source's publish timestamp. Default: `false`. |
| `trust_updated_at` | `bool` | No | Whether to trust the source's last-modified timestamp. Default: `false`. |
| `timezone` | `string` | No | IANA timezone of the source's timestamps (e.g., "America/New_York"). |

```json
{
  "supports_published_at": true,
  "supports_updated_at": true,
  "trust_published_at": true,
  "trust_updated_at": false,
  "timezone": "UTC"
}
```

**Why separate capability from trust?**

- A source may *send* timestamps but those timestamps may be unreliable (user-submitted content, clock-drifted servers).
- `trust_published_at = false` forces `effective_at` to fall back to `retrieved_at`.

### 2.5 Authority Tier

| Field | Type | Required | Description |
|---|---|---|---|
| `authority_tier` | `string` | Yes | Classification of source authority. |

**Allowed values and meaning:**

| Tier | Meaning | Examples |
|---|---|---|
| `primary` | Official, canonical source (first-party) | Exchange API, blockchain RPC, regulatory filing |
| `secondary` | Republished or aggregated (third-party) | CoinGecko, CryptoCompare, news aggregators |
| `tertiary` | Derivative, inferred, or user-generated | Social media mentions, forum posts, derived indicators |
| `unknown` | Cannot be classified | New or unverified sources |

```json
{
  "authority_tier": "primary"
}
```

### 2.6 Role

| Field | Type | Required | Description |
|---|---|---|---|
| `role` | `string` | Yes | Functional role this source plays in the pipeline. |

**Allowed values and meaning:**

| Role | Meaning | Example Sources |
|---|---|---|
| `price` | Price or market data | Exchange ticker, order book, OHLCV |
| `event` | Calendar or event data | Token launch calendar, governance vote |
| `news` | News or editorial content | CoinDesk, CryptoPanic, RSS feeds |
| `social` | Social media activity | Twitter/X, Reddit, Discord, Telegram |
| `onchain` | On-chain data | Blockchain RPC, explorer APIs |
| `metadata` | Token/project metadata | CoinMarketCap info, GitHub README |
| `regulatory` | Legal/regulatory filings | SEC EDGAR, central bank announcements |
| `macro` | Macroeconomic indicators | Fed rates, CPI data, traditional markets |
| `reference` | Reference/lookup data | Token address mappings, ABI definitions |

```json
{
  "role": "price"
}
```

### 2.7 Trust Assessment Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `trust_score` | `float` | No | 0.0 (untrustworthy) to 1.0 (fully trusted). Default: `0.5`. |
| `trust_rationale` | `string` | No | Why this trust score was assigned. |
| `trust_verified_at` | `DateTime` | No | When the trust assessment was last verified. |
| `requires_verification` | `bool` | No | Whether every observation needs manual verification. Default: `false`. |

```json
{
  "trust_score": 0.9,
  "trust_rationale": "Official Binance API, verified API key ownership",
  "trust_verified_at": "2025-01-20T08:00:00Z",
  "requires_verification": false
}
```

### 2.8 Evidence Policy Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `retain_raw_documents` | `bool` | No | Whether to persist raw HTTP bodies. Default: `true`. |
| `retain_headers` | `bool` | No | Whether to keep non-redacted headers. Default: `false`. |
| `evidence_ttl_days` | `uint32` | No | Days before evidence is eligible for archival/compaction. Default: `90`. |
| `archive_on_completion` | `bool` | No | Whether to submit raw documents to ArchiveBox. Default: `false`. |
| `content_hash_algorithm` | `string` | No | Hash algorithm for content integrity. Default: `"sha256"`. |

```json
{
  "retain_raw_documents": true,
  "retain_headers": false,
  "evidence_ttl_days": 90,
  "archive_on_completion": false,
  "content_hash_algorithm": "sha256"
}
```

### 2.9 Health Policy Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `health_check_interval_seconds` | `uint32` | No | How often to check source health. Default: `300`. |
| `staleness_threshold_seconds` | `uint32` | No | How long without update before source is considered stale. Default: `3600`. |
| `error_threshold` | `uint32` | No | Consecutive errors before source is marked degraded. Default: `3`. |
| `degraded_cooldown_seconds` | `uint32` | No | Cooldown before retrying a degraded source. Default: `600`. |
| `health_endpoint` | `string` | No | Optional separate URL for health checks. |

```json
{
  "health_check_interval_seconds": 300,
  "staleness_threshold_seconds": 3600,
  "error_threshold": 3,
  "degraded_cooldown_seconds": 600
}
```

### 2.10 Retry Policy

| Field | T
