# Acquisition Layer — Architecture Overview (V1)

> **Document Version:** 1.0  
> **Scope:** `crypto-event-intelligence` acquisition subsystem  
> **Status:** Ratified

---

## 1. Introduction

The **Acquisition Layer** is the first and most critical boundary in the event-intelligence pipeline. Its sole responsibility is to **fetch, verify, and persist raw evidence** from external sources — blockchain RPC nodes, REST APIs, RSS/ATOM feeds, HTML pages, WebSocket streams, and file-based archives — **without interpreting what that evidence means**.

Acquisition produces a tamper-evident, replayable record of *what was seen, when, and from where*. Downstream systems (classification, signal scoring, trading) consume this record but **never modify or delete it**.

### 1.1 Why a Separate Layer?

| Concern | Handled By Acquisition | Handled Elsewhere |
|---|---|---|
| Network I/O, retries, backoff | ✅ | ❌ |
| Credential management, header redaction | ✅ | ❌ |
| Content integrity (hashes, sizes) | ✅ | ❌ |
| Timestamp provenance | ✅ | ❌ |
| Bullish / bearish classification | ❌ | Classification pipeline |
| Signal score computation | ❌ | Scoring engine |
| Order placement | ❌ | Trading executor |

---

## 2. System Boundary

### 2.1 What Acquisition **DOES**

- Connect to external sources using configured credentials
- Fetch documents (JSON, HTML, plaintext, binary)
- Parse structured data into `NormalizedObservation` records
- Assign every observation a **five-timestamp model** (see §4)
- Persist raw documents and observations to the evidence store
- Support **replay** — re-fetch a historical source as if we were in the past
- Detect content changes via hash comparison
- Report health metrics (latency, error rate, staleness)
- Retract observations when a source explicitly deletes or amends content

### 2.2 What Acquisition Does **NOT** Do

| Prohibited Behaviour | Rationale |
|---|---|
| Assign bullish/bearish sentiment | That is the classification layer's job |
| Compute signal scores | Scoring requires classified signals |
| Execute trades or submit orders | Air-gapped by design |
| Modify historical observations | Immutable record; only new revisions appended |
| Delete evidence rows | Hard deletes would break replay guarantees |
| Run background daemons or cron | Acquisition is invoked on-demand or via scheduler |
| Call paid/rate-limited APIs without explicit budgets | Cost control is caller responsibility |
| Store secrets in source code | Secrets live in environment / vault only |

---

## 3. Core Concepts

### 3.1 Source Contract

A `SourceContract` is the declarative configuration that tells the acquisition engine **what** to fetch, **how** to fetch it, and **how** to interpret the response. It is the single source of truth for a given data source.

*See [SOURCE_CONTRACT_REFERENCE_V1.md](./SOURCE_CONTRACT_REFERENCE_V1.md) for the full field reference.*

### 3.2 Raw Document

The unprocessed byte stream returned by a transport (HTTP response body, file contents, WebSocket message payload). It is stored **exactly as received**, alongside its content hash and size.

```
RawDocument {
  id: UUID
  source_contract_id: UUID
  transport: "http" | "rss" | "websocket" | "file"
  body: bytes
  content_hash: SHA256
  content_length: uint64
  content_type: string
  retrieved_at: DateTime          # when acquisition received it
  headers: map (redacted)         # auth headers scrubbed
}
```

### 3.3 NormalizedObservation

A parsed, structured representation of a single *fact* extracted from a raw document. One raw document may produce zero, one, or many observations.

```
NormalizedObservation {
  id: UUID
  raw_document_id: UUID
  source_contract_id: UUID
  observation_type: "price" | "event" | "metadata" | "social_post" | "transaction"
  body: JSON                     # structured payload
  published_at: DateTime?        # source-asserted timestamp
  effective_at: DateTime         # business-effective timestamp
  updated_at: DateTime?          # source-asserted last-modified
  first_seen_at: DateTime        # when *we* first saw this observation
  retrieved_at: DateTime         # when *we* fetched its raw document
}
```

### 3.4 Revision

When a source updates or retracts a previously seen observation, acquisition appends a **Revision** — it never mutates the original observation.

```
Revision {
  id: UUID
  observation_id: UUID
  revision_type: "update" | "retraction" | "deletion_notice" | "reconfirmation"
  previous_body_hash: SHA256?
  new_body: JSON?
  new_body_hash: SHA256?
  observed_at: DateTime          # when we detected the change
  source_asserted_timestamp: DateTime?
  reason: string?
}
```

### 3.5 Replay

Replay is the ability to re-execute acquisition for a source contract **as if the current time were some past timestamp**. This is essential for:

- Backtesting strategies against historical data
- Filling gaps after an outage
- Auditing what acquisition *would have* seen at time T

*See [POINT_IN_TIME_REPLAY_V1.md](./POINT_IN_TIME_REPLAY_V1.md) for the detailed replay model.*

---

## 4. Five-Timestamp Model

Every observation carries **five distinct timestamps**. Understanding the differences is critical for correct downstream use.

| Timestamp | Source | Meaning | Nullable? |
|---|---|---|---|
| `published_at` | Source-asserted | When the source says the content was published | Yes (some sources don't provide it) |
| `effective_at` | Computed | The timestamp that downstream should treat as "when this fact is/was true" | No |
| `updated_at` | Source-asserted | When the source says it last modified this content | Yes |
| `first_seen_at` | System-assigned | The first time *we* ever observed this observation (immutable after first write) | No |
| `retrieved_at` | System-assigned | The moment we received the raw document payload | No |

### 4.1 Effective At Resolution

`effective_at` is resolved using this priority:

1. If `published_at` is present AND trustworthy (per source contract trust flags) → `published_at`
2. Else if `updated_at` is present AND trustworthy → `updated_at`
3. Else → `retrieved_at`

---

## 5. Pipeline Flow

```
                         ┌─────────────────┐
                         │  SourceContract  │
                         │  (configuration) │
                         └────────┬────────┘
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────┐
    │                    TRANSPORT                        │
    │  HTTP/RSS/WS/File  │  retries │  backoff │  auth    │
    └────────────────────────┬────────────────────────────┘
                             │
                             ▼
    ┌─────────────────────────────────────────────────────┐
    │                  RAW DOCUMENT                       │
    │  body bytes │ content_hash │ headers (redacted)     │
    └────────────────────────┬────────────────────────────┘
                             │
                             ▼
    ┌─────────────────────────────────────────────────────┐
    │                   EXTRACTION                        │
    │  Parse │ Validate │ Schema-check │ Normalize        │
    └────────────────────────┬────────────────────────────┘
                             │
                             ▼
    ┌─────────────────────────────────────────────────────┐
    │              NormalizedObservation(s)               │
    │  typed structured facts with 5-timestamps           │
    └────────────────────────┬────────────────────────────┘
                             │
                             ▼
    ┌─────────────────────────────────────────────────────┐
    │                    REVISION                         │
    │  Diff │ Detect change │ Append (never mutate)       │
    └────────────────────────┬────────────────────────────┘
                             │
                             ▼
    ┌─────────────────────────────────────────────────────┐
    │                    STORAGE                          │
    │  Evidence DB │ Archive │ A
