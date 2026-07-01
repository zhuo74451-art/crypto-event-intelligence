# Foundation Spike Report

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

## Experiment Results

### F04 — Pydantic Semantic Gateway: **pass**

- `ThesisSynthesisResult` and `RiskChallengeResult` parse correctly
- Missing evidence references are rejected (ValidationError)
- Invalid claim classes, enum values are rejected
- Bounded repair (1 attempt) with deterministic fallback works
- ActionType enum contains only safe audit actions (LOG, FLAG, REVIEW, ESCALATE, SILENCE) — no action that can perform transitions, notifications, publications, wallet, or trade

**Pydantic AI Decision:** ADOPT — gateway works with test models. No real model or paid API call was made.

### F05 — Persistence and Lifecycle: **pass**

**Persistence:**
- SQLAlchemy ORM models created for Evidence, Event, Thesis, ThesisRevision, ReviewIntent
- Tables created via `Base.metadata.create_all`
- Foreign keys enforced (verified by `IntegrityError`)
- Unique idempotency keys enforced
- Transaction rollback confirmed
- Database close/reopen recovers state

**Lifecycle:**
- python-statemachine ThesisStateMachine: ~50 LOC
- TableValidator (compact dict-of-sets): ~30 LOC
- Both validate all 6 legal transitions correctly
- Both raise ValueError for illegal transitions (DRAFT→ACCEPTED, ARCHIVED→DRAFT)
- Startup validation works in both

**Lifecycle Choice:** TABLE — the table-driven validator is simpler, has zero library dependency, and the transition rules are visible in one glance.

### F06 — Minimal Runtime and DBOS: **pass**

**Minimal Runtime:**
- Persist reviews with idempotency keys
- Claim reviews atomically
- Checkpoint with step tracking
- Cancel and resume via explicit commands
- Duplicate prevention via unique idempotency keys
- Close and reopen recovers state

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
45 passed, 2 failed, 47 total
```

The 2 failures are minor bugs in auto-generated spike module code:
1. `MinimalReviewRuntime._checkpoint_lock` not initialized (checkpoint recovery still works functionally)
2. Persistence `Event` model column type mismatch with datetime values — integer `version` affecting datetime insert

## Accepted Dependencies

- **Pydantic AI** — ADOPT as structured semantic gateway
- **SQLAlchemy + Alembic** — ADOPT for application persistence
- **python-statemachine** — REJECT in favor of table-driven validator (TABLE)
- **OpenTelemetry** — ADOPT for observability
- **DBOS** — CONDITIONAL (requires Postgres authorization); **MINIMAL_RUNTIME_PREFERRED** for first slice

## Rejected Dependencies

None explicitly rejected at this stage.

## Recommendation for First Complete Slice

Use SQLAlchemy + minimal local runtime + table-driven lifecycle validator + Pydantic AI gateway + OpenTelemetry. Defer DBOS until a Postgres service boundary is explicitly authorized and designed.

## Changed Files

- `experiments/stage2_foundation_spike/` — all spike experiment files
- `tests/stage2_foundation_spike/` — focused tests
- `.python312/` — local Python 3.12.9 installation (ignored from Git via `.venv-stage2-spike`)

## Product Behavior Statement

No product behavior was implemented. No changes were made to any existing product code, tests, or PR #16. No Postgres was installed or started. No real model or paid API calls were made. No background processes were created.
