# Bounded Shadow Foundation — R01

## What it is

A **bounded shadow runner** is a synchronous, finite-loop executor for
one-shot callables. It is *not* a daemon, scheduler, cron job, or
background service.

| Property | Value |
|----------|-------|
| Execution | Synchronous (blocking) |
| Max runs | Hard-capped at 10 |
| Default runs | 2 |
| Stop mechanism | StopMarker + policy rules |
| Auditing | SQLite run-history (parent + child rows) |
| Concurrency guard | W5 FileLock |
| Network | None |
| Send | Never (`no_send` locked True) |
| Background threads | None |

---

## Bounded Shadow vs Daemon / Scheduler

| Aspect | Bounded Shadow | Daemon / Scheduler |
|--------|---------------|--------------------|
| Lifetime | Finite (process exits after max_runs) | Indefinite (runs until killed) |
| Loop | `while ordinal <= max_runs` | `while True` or cron trigger |
| Concurrency | Single process, FileLock | May fork/multi-thread |
| State | SQLite per state_dir | May share global state |
| Network | No | Typically yes |

---

## Lifecycle

```
Config validation
    │
    ▼
Create state_dir
    │
    ▼
Check StopMarker ──── set ──► early return (stopped)
    │
    ▼
Acquire FileLock ──── fail ──► return (failed/lock not acquired)
    │
    ▼
Initialize SQLite
    │
    ▼
Insert parent run-history row
    │
    ▼
┌─── Loop ordinal = 1..max_runs ──────────────────────┐
│    │                                                  │
│    ├─ Check StopMarker ── set ──► break (stopped)    │
│    ├─ Call injected one-shot callable                 │
│    ├─ Normalise result (completed/degraded/failed)    │
│    ├─ Write child run record                          │
│    ├─ Apply stop-policy rules                         │
│    ├─ Policy stop? ── yes ──► break                  │
│    ├─ Last round? ── yes ──► break                   │
│    ├─ Check StopMarker (pre-sleep)                    │
│    ├─ Sleep (injectable)                              │
│    └─ Check StopMarker (post-sleep)                   │
│                                                       │
└───────────────────────────────────────────────────────┘
    │
    ▼
Update parent run-history (final status)
    │
    ▼
Release FileLock
    │
    ▼
Return BoundedShadowResult
```

---

## Finite-run guarantee

- `max_runs` minimum = 1
- `max_runs` maximum = 10
- `max_runs` default = 2
- `None` or `0` are rejected at construction
- The loop iterates at most `max_runs` times
- No `while True` anywhere in the runner

---

## Policy state machine

### Child status → parent status

```
Callable result    →    Counter          →    Decision
──────────────────────────────────────────────────────────
completed          →    completed_runs+1 →    continue
degraded           →    degraded_runs+1  →    continue (if continue_on_degraded=True)
                                             stop (if continue_on_degraded=False)
failed             →    failed_runs+1    →    stop (if stop_on_failure=True)
                                             continue (if stop_on_failure=False)
callable raises    →    failed_runs+1    →    same as failed (according to stop_on_failure)
```

### Final parent status rules (deterministic, tested)

| Condition | Status |
|-----------|--------|
| Any `failed` run | `failed` |
| No failures but any `degraded` | `degraded` |
| Stopped by marker, no failures | `stopped` |
| 0 attempted runs (pre-race stop) | `stopped` |
| All completed, no stops | `completed` |

---

## StopMarker behaviour

- Created as a file in `state_dir / stop_marker_name` (default: `STOP`)
- Checked at 4 points:
  1. Before lock acquisition (pre-race check)
  2. Before each round
  3. Before sleep (between rounds)
  4. After sleep (before next round)
- StopMarker is **not** a failure — `stopped_by_marker=True`
- Completed rounds are preserved
- Rounds not attempted are counted in `skipped_runs`

---

## FileLock behaviour

- Lock file: `state_dir / lock_name` (default: `bounded_shadow.lock`)
- Only one bounded-shadow instance per `state_dir`
- Lock acquired before any callable invocation
- Lock released in `finally` — guaranteed even on exception
- Lock failure → `BoundedShadowResult.lock_acquired=False`, no callable runs

---

## Run-history structure

### Parent row (`run_history`)

| Column | Value |
|--------|-------|
| `run_id` | UUID hex (shadow_run_id) |
| `runner_label` | `"bounded_shadow"` (configurable) |
| `status` | `completed` / `degraded` / `failed` / `stopped` |
| `summary_json` | Config, counters, child record summary |
| `error` | Last error (if any) |

### Child wrapper row (`run_history`)

| Column | Value |
|--------|-------|
| `run_id` | Child's own run_id |
| `runner_label` | `"bounded_shadow_child"` |
| `status` | `completed` / `degraded` / `failed` |
| `summary_json` | `parent_shadow_run_id`, `ordinal`, `no_send` |

The child row is a wrapper — it is NOT the Integration's own run record.
Parent/child linkage is via `summary_json.parent_shadow_run_id` and
`summary_json.ordinal`.

---

## `no_send` guarantee

- `BoundedShadowConfig.no_send` defaults to `True`
- Setting `no_send=False` raises `ValueError` at construction
- There is no environment variable or hidden flag to bypass this
- The callable receives `no_send=True` on every invocation
- This is enforced at runtime by a guard at the start of `run_bounded_shadow`

---

## Integration injection

When Integration is ready to use the bounded shadow, it provides a
`ShadowCallable`-conforming callable:

```python
from market_radar.operations.bounded_shadow import (
    BoundedShadowConfig,
    BoundedShadowResult,
    ShadowCallableResult,
    run_bounded_shadow,
)

def my_one_shot(ordinal, shared_state_dir, no_send, parent_shadow_run_id):
    # ... Integration work here ...
    return ShadowCallableResult(
        child_run_id=uuid.uuid4().hex,
        status="completed",
        summary={"records_processed": 42},
    )

config = BoundedShadowConfig(state_dir="/tmp/my_state")
result: BoundedShadowResult = run_bounded_shadow(config, my_one_shot)
```

### Why this task does NOT import Integration

1. **Separation of concerns** — the runner is generic infrastructure.
2. **Testability** — all tests use fake callables; no Integration needed.
3. **Avoid coupling** — Integration should depend on operations, not vice versa.
4. **Safety** — prevents accidental network/send calls during testing.

---

## Operational stop

Stop a running bounded shadow by creating the stop marker file:

```bash
echo stop > /path/to/state_dir/STOP
```

The runner checks this file before each round and before/after sleep.
If the runner is between rounds (sleeping), it checks after waking.

---

## Known limitations

- **Same-process only** — FileLock prevents concurrent instances but does not
  coordinate across machines.
- **No progress reporting** — the runner blocks the calling thread until all
  rounds complete.
- **No retry** — a failed callable is counted but not retried within the same
  `run_bounded_shadow` call.
- **SQLite concurrency** — uses WAL mode but may content with other callables
  writing to the same DB.
- **No external summary artifact** — the default output is the in-memory
  `BoundedShadowResult`; optional summary JSON requires explicit injection.
- **Clock resolution** — on Windows, `time.time_ns()` is used for temp-file
  uniqueness but the `_ts()` helper rounds to microseconds for ISO-8601.
