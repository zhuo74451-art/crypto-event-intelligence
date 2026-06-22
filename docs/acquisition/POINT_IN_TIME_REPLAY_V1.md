# Point-in-Time Replay (V1)

> **Document Version:** 1.0  
> **Scope:** Replay engine, time-travel semantics, backtesting correctness  
> **Status:** Ratified

---

## 1. What is Point-in-Time Replay?

Point-in-time replay is the ability to **re-execute acquisition for a source contract as if the current wall clock were a specified past timestamp**. It answers the question:

> *"If we had run acquisition at time T, what observations would we have stored?"*

This is **not** a simulation. Replay uses the same transport adapters, extraction logic, and revision engine as live acquisition. The only difference is that the system clock is logically replaced with the replay timestamp.

### 1.1 Why Replay Matters

| Use Case | Description |
|---|---|
| **Backtesting** | Run a trading strategy against data that acquisition *would* have produced at each decision point |
| **Gap Filling** | If acquisition was down 14:00–15:00 UTC, replay that window to recover missing observations |
| **Audit** | Verify what the system knew at the time of a specific trade or alert |
| **Regression Test** | Replay a known source and confirm output matches historical snapshots |

---

## 2. Core Concepts

### 2.1 Two Views of History

There are fundamentally two ways to look at past data:

| View | Definition | Use Case |
|---|---|---|
| **Current Best Reconstruction** (`as_of_now`) | The most recent revision of every observation, assembled as of today | Dashboards, reports, current state |
| **Knowledge As Known Then** (`as_known_at_T`) | The set of observations and revisions that existed *at time T*, frozen | Backtesting, audit, regulatory compliance |

**The acquisition layer stores data to support both views.** Downstream consumers must choose which view is appropriate.

### 2.2 Why We Can't Overwrite History

A common anti-pattern is to **update** an observation when new data arrives:

```sql
-- BAD: Overwrites history
UPDATE observations SET body = '{"price": 50000}' WHERE id = 'obs-123';
```

This destroys the ability to replay. Instead, acquisition uses an **append-only** model:

```sql
-- GOOD: Appends a revision
INSERT INTO revisions (observation_id, revision_type, new_body, observed_at)
VALUES ('obs-123', 'update', '{"price": 50000}', '2025-01-15T10:05:00Z');

-- The original observation remains untouched.
```

**Key rule:** Once an observation's `first_seen_at` is written, it is **immutable**. Only revisions are appended.

### 2.3 How `first_seen_at` Works with Revisions

| Scenario | `first_seen_at` | Revisions |
|---|---|---|
| Observation first seen at T0 | `T0` | None (original) |
| Updated at T1 | `T0` (unchanged) | 1 revision (type: `update`, observed_at: `T1`) |
| Updated again at T2 | `T0` (unchanged) | 2 revisions (observed_at: `T1`, `T2`) |
| Retracted at T3 | `T0` (unchanged) | 3 revisions (including retraction at `T3`) |

`first_seen_at` is the **anchor timestamp** for replay. When replaying at time T, we see an observation if and only if `first_seen_at <= T`.

### 2.4 How Retractions Work

A retraction is a revision of type `retraction` that marks an observation as **no longer considered valid** by the source. The observation body is **not deleted** — it is annotated with a retraction revision.

```
Observation "BTC price = 50000" created at 10:00:00
    └── Revision "retraction" at 10:05:00 (source corrected to 49500)
         └── Revision "update" at 10:05:01 (new body: {"price": 49500})
```

When replaying at time T:

- If T < retraction time → the **original** (or last update before retraction) is visible
- If T >= retraction time but T < next update → the observation is **hidden** (retracted state)
- If T >= next update time → the **new** body is visible

Retractions are **source-asserted**. A source may say "delete that tweet" or "correct that price." We preserve the fact that the retraction happened.

### 2.5 How Deleted Content Is Preserved

When a source removes content entirely (e.g., a deleted tweet, a removed blog post), acquisition:

1. Detects the HTTP 404 or empty response
2. Stores a **deletion_notice** revision on all observations from that raw document
3. Preserves the original raw document and observations **forever** (or until TTL expiry)

```python
# Pseudocode: handling source deletion
def handle_deletion(raw_doc, existing_observations):
    for obs in existing_observations:
        append_revision(
            observation_id=obs.id,
            revision_type="deletion_notice",
            new_body=None,           # content is gone
            observed_at=now(),
            reason="Source returned 404 - content removed"
        )
    # Raw document is still in storage!
```

This means you can always **replay and see what was deleted**, which is critical for audit trails.

---

## 3. Replay Mechanics

### 3.1 Time Machine Function

The core replay primitive is a **time machine** that wraps the acquisition pipeline:

```
replay(source_contract_id, target_timestamp) -> List[NormalizedObservation]
```

Implementation:

```python
def replay(source_contract_id: UUID, target_ts: datetime) -> list[NormalizedObservation]:
    # 1. Load the source contract as it existed at target_ts (if versioned)
    contract = load_contract_at(target_ts)

    # 2. Set the time machine clock
    with time_machine(target_ts) as frozen_time:

        # 3. Execute transport (with frozen time, conditional requests use target_ts)
        raw_doc = transport.fetch(contract)

        # 4. Extract observations (parse as we would at target_ts)
        observations = extraction.extract(raw_doc, contract)

        # 5. For each observation, determine what we *would have known* at target_ts
        result = []
        for obs in observations:
            known_state = get_observation_state_at(obs.id, target_ts)
            result.append(known_state)

        return result
```

### 3.2 Seam Points

Replay works correctly only if we control these **seam points**:

| Seam | Live Acquisition | Replay |
|---|---|---|
| `now()` | Wall clock | Frozen to target timestamp |
| `conditional_headers` | `If-Modified-Since: <now>` | `If-Modified-Since: <target_ts>` |
| `rate_limit_state` | Current counters | Reset (or simulated) |
| `revision_time` | Wall clock | Target timestamp |

---

## 4. Examples

### 4.1 Correct Replay — Backtesting a Price Signal

**Scenario:** Backtest a strategy that buys when BTC price exceeds $50,000. The decision point is 2025-01-15 10:00:00 UTC.

```python
# Correct: Replay as of the decision timestamp
observations = replay(
    source_contract_id="binance-btc-ticker",
    target_ts=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
)
# Returns the observation that existed AT 10:00:00
# If price was updated at 10:00:05, the update is NOT included
```

### 4.2 Incorrect Replay — Using Current Data for Past Decisions

```python
# WRONG: Using current-best-reconstruction for a past decision
latest_price = db.query("""
    SELECT body FROM observations
    WHERE source_contract_id = 'binance-btc-ticker'
    ORDER BY first_seen_at DESC LIMIT 1
""")
# This returns the MOST RECENT price, which may not have existed at decision time
```

### 4.3 Correct Replay — Auditing What We Knew

**Scenario:** Regulatory audit requires proving what price was shown to a user at 14:32:00 UTC.

```python
# Correct: Replay with exact timestamp
known_at_audit_time = replay(
    source_contract_id="binance-btc-ticker",
    target_ts=datetime(2025, 3, 1, 14, 32, 0, tzinfo=UTC)
)

# The result includes only observations where first_seen_at <= 14:32:00
# AND filters out any revisions that happened after 14:32:00
```

### 4.4 Correct Replay — Retraction Handling

**Scenario:** Source published "Token X listed on Exchange Y" at 09:00, retracted at 09:30. What did we know at 09:15? At 09:45?

```python
# At 09:15 — retraction hasn't happened yet
state_at_0915 = replay(source_id, datetime(2025, 1, 1, 9, 15))
# => Observation is VISIBLE (listing announcement is live)

# At 09:45 — retraction has happened
state_at_0945 = replay(source_id, datetime(2025, 1, 1, 9, 4
