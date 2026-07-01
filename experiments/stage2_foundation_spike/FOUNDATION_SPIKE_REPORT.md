# Foundation Compatibility Spike — Final Report

## Environment

- **Python:** 3.12.9 (arm64)
- **OS:** macOS 14.1 (Sonoma), Darwin 23.1.0
- **Architecture:** arm64
- **Virtual Environment:** `.venv-stage2-spike`

## Exact Dependency Versions

| Package | Version | License |
|---------|---------|---------|
| dbos | 2.26.0 | MIT |
| pydantic | 2.13.4 | MIT |
| pydantic-ai | 2.2.0 | MIT |
| sqlalchemy | 2.0.51 | MIT |
| alembic | 1.18.5 | MIT |
| python-statemachine | 3.2.0 | MIT |
| opentelemetry-api | 1.42.1 | Apache-2.0 |
| opentelemetry-sdk | 1.42.1 | Apache-2.0 |
| pytest | 9.1.1 | MIT |
| httpx | 0.28.1 | BSD |
| psycopg | 3.3.4 | LGPL-3.0 |
| cryptography | 49.0.0 | Apache-2.0 / BSD |

Dependency check: **pass** — no broken requirements.

## Executed Evidence

### F04 — Pydantic Semantic Gateway: **pass**

- `ThesisSynthesisResult` and `RiskChallengeResult` parse correctly
- Missing evidence references rejected (ValidationError) when status requires them
- Empty evidence_refs allowed for INSUFFICIENT/BLOCKED (no fabricated evidence)
- Invalid claim classes, enum values rejected
- ActionType enum contains only safe audit actions (LOG, FLAG, REVIEW, ESCALATE, SILENCE) — no trade, publish, wallet, or execute
- Bounded repair (1 attempt) with deterministic fallback works
- Zero network calls: Agent uses `TestModel` (offline-only)
- **Agent execution produces observable usage metadata**: `RunUsage` with `requests >= 1` and token counts > 0 (verified by test)

### F05 — Persistence and Lifecycle: **pass**

**Persistence:**
- SQLAlchemy ORM models: Evidence, Event, Thesis, ThesisRevision, ReviewIntent
- Tables created via `Base.metadata.create_all`
- Foreign keys enforced (verified by `IntegrityError`)
- Unique idempotency keys enforced
- Transaction rollback confirmed
- Database close/reopen recovers state
- Append-only revisions: `thesis_revisions` rows are never updated or deleted (SQLAlchemy `before_update`/`before_delete` event blocks modification)
- Compare-and-swap thesis update via `UPDATE ... WHERE version = :expected` — `StaleVersionError` on conflict

**Alembic Migration (real):**
- Alembic `op.create_table` / `op.drop_table` demonstrated
- `alembic_version` table created on upgrade
- `alembic.command.upgrade("head")` and `alembic.command.downgrade("base")` both verified
- Invalid migration propagates exception (no silent swallow)

**Lifecycle (11 states):**

| State | Legal Transitions |
|-------|-------------------|
| DISCOVERED | QUALIFYING, REJECTED, ISOLATED |
| QUALIFYING | CANDIDATE, REJECTED, ISOLATED, EXPIRED |
| CANDIDATE | ACTIVE, DORMANT, REJECTED, EXPIRED, ISOLATED |
| ACTIVE | ACTIVE, DORMANT, INVALIDATED, EXPIRED, ARCHIVED |
| DORMANT | ACTIVE, INVALIDATED, EXPIRED, ARCHIVED |
| INVALIDATED | ARCHIVED, REOPEN_REVIEW |
| EXPIRED | ARCHIVED, REOPEN_REVIEW |
| ARCHIVED | REOPEN_REVIEW |
| REOPEN_REVIEW | ACTIVE, CANDIDATE, ARCHIVED, REJECTED, ISOLATED |
| REJECTED | REOPEN_REVIEW |
| ISOLATED | QUALIFYING, REJECTED |

Two implementations demonstrated:
1. **python-statemachine** `ThesisStateMachine` — ~90 lines, demonstrates real library API (import, State definition, `.to()` transitions)
2. **TableValidator** — ~30 lines, compact dict-of-sets, zero dependencies

**Lifecycle Choice:** TABLE — the table-driven validator is simpler, has zero library dependency, and the transition rules are visible in one glance. The python-statemachine library is importable and its API is demonstrated; the library is listed as **CONDITIONAL** if a future slice needs runtime lifecycle enforcement beyond validation.

### F06 — Minimal Runtime and DBOS: **pass**

**Minimal Runtime (SQLAlchemy-based):**
- Persist reviews with unique idempotency keys
- Claim due reviews atomically via conditional `UPDATE review_intents SET status='CLAIMED' WHERE id=:id AND status='PENDING'`
- Checkpoint with step tracking, retry count, and error history
- Cancel and resume preserves checkpoint_step, retry_count, last_error
- Duplicate prevention via unique idempotency key constraint
- Close and reopen recovers state
- Retry exhaustion commits FAILED status before raising `RetryExhaustedError`
- **Synchronized claim race**: two threads, separate runtime instances, same database, `threading.Barrier` synchronization; exactly one claims the review every iteration (verified over 10 repetitions)
- Conditional `PENDING -> CLAIMED` guard retained

**DBOS Feasibility:**
- Installed version: DBOS 2.26.0
- Hard dependency: psycopg[binary]>=3.1 (Postgres required)
- No SQLite or in-memory fallback exists
- DBOS requires a running Postgres service

**DBOS Classification:** DBOS_REQUIRES_POSTGRES_AUTHORIZATION

**DBOS vs Minimal Runtime Comparison:**

| Dimension | DBOS | Minimal Runtime |
|-----------|------|----------------|
| Guarantees | Exactly-once workflow execution | Best-effort with checkpoint recovery |
| Custom Code | DBOS decorators + workflow functions | Pure Python + SQLAlchemy |
| Services | Postgres service required | Zero services (SQLite file) |
| Status/Stop/Recovery | Built-in workflow management | Manual checkpoint-based |
| Testability | Needs Postgres for tests | SQLite in-memory, fully contained |
| Owner Burden | Postgres maintenance, connection mgmt | Only file-based storage |

### F07 — OpenTelemetry: **pass**

- Correlated spans for retrieval, semantic pass A+B, arbitration, transition, and recovery
- Run, event, thesis, revision, retry, and resource attributes attached
- Data minimization verified: no evidence bodies or secrets in exported spans
- In-memory exporter used, no backend contacted

## Test Results

```text
154 passed
```

## Accepted Dependencies

- **SQLAlchemy + Alembic** — ADOPT for application persistence
- **Pydantic AI** — ADOPT as structured semantic gateway (Agent + TestModel path, zero network calls, observable usage metadata)
- **OpenTelemetry** — ADOPT for observability (in-memory exporter, no backend)
- **python-statemachine** — CONDITIONAL: library API demonstrated; TableValidator chosen for first slice
- **DBOS** — CONDITIONAL: requires Postgres authorization; minimal runtime preferred for first slice

## Deferred or Not-Run Comparisons

These statements are not proven by the spike and require future work:

- python-statemachine runtime state persistence (library was demonstrated at import/validation level only; the spike does not run a long-lived SM instance)
- DBOS exactly-once guarantee vs minimal runtime checkpoint recovery in a production-like workload
- OpenTelemetry collector/export pipeline (only in-memory exporter tested)
- Real concurrent load beyond two-thread claim race
- Multi-process database contention with WAL mode
- Performance or latency comparison between validators

## Recommendation for First Complete Slice

Use SQLAlchemy + minimal local runtime + table-driven lifecycle validator + Pydantic AI gateway + OpenTelemetry. Defer DBOS until a Postgres service boundary is explicitly authorized and designed.

## Changed Files

- `experiments/stage2_foundation_spike/` — all spike experiment files
- `tests/stage2_foundation_spike/` — focused tests (154 total)
- `.python312/` — local Python 3.12.9 installation (ignored from Git via `.venv-stage2-spike`)

## Product Behavior Statement

No product behavior was implemented. No changes were made to any existing product code, tests, or PR #16. No Postgres was installed or started. No real model or paid API calls were made. No background processes were created. No daemon, cron job, login item, or persistent background process was started.
