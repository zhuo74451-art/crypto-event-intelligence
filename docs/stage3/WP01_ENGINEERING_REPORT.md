# WP-01 Engineering Report — Production Foundation

## Environment

- **Python:** 3.12.9 (arm64)
- **OS:** macOS 14.1 (Sonoma), Darwin 23.1.0
- **Virtual Environment:** `.venv-stage2-spike`

## Implemented Responsibility

### 1. Package Boundaries (`market_radar/cognition_v2/`)

Eight sub-packages with enforced dependency direction:

```
market_radar/cognition_v2/
  domain/       — validated Pydantic contracts
  application/  — application service interfaces (scaffold)
  persistence/  — SQLAlchemy models, Alembic migration, helpers
  lifecycle/    — table-driven 11-state lifecycle service
  replay/       — historical manifest, leakage blocking, split-order
  observability/ — structured logging, OpenTelemetry bootstrap
  operator/     — bounded CLI commands (no scheduler/daemon)
  cli/          — CLI entrypoint
```

Domain imports no persistence, operator, or SDK code. Verified by boundary tests.

### 2. Canonical Domain Contracts

**19 Pydantic contracts** implemented in `domain/contracts.py`:

Source: `SourceIdentity`, `SourcePermission`
Evidence: `EvidenceRecord`, `EvidenceRef`
Events: `EventRecord`, `EventRevision`
Theses: `ThesisRecord`, `ThesisRevision`
Claims: `ClaimRecord`, `ExposureLink`, `CounterEvidence`
Reviews: `ReviewIntent`, `AttentionAllocation`, `NotificationDecision`
Provenance: `ProvenanceEdge`
Replay: `HistoricalCaseManifest`, `OutcomeWindow`
Lifecycle: `LifecycleTransitionRequest`
Validation: `FutureEvidenceBlocker`

All contracts preserve: publication/effective/first-seen/retrieval/assessment times, source authority, fact permission, claim classes, evidence-status bands, horizons. No numeric confidence, no trade/wallet/publish/order fields. SUPPORTED/STRONG require evidence references; INSUFFICIENT/BLOCKED may have empty refs.

### 3. Production Persistence

**18 SQLAlchemy models** with matching Alembic baseline migration:

- Sources, source health, evidence, events, event revisions, theses, thesis revisions, claims, exposure links, counter-evidence, review intents, attention allocations, notification decisions, provenance edges, historical cases, outcome windows, run records, configuration versions.

Key guarantees verified by tests:
- SQLite foreign keys and WAL mode
- Unique idempotency keys
- Unique (thesis_id, version) and (event_id, version)
- Transaction rollback
- Close/reopen recovery
- Optimistic compare-and-swap with `StaleVersionError`
- Append-only revision version constraint
- Real Alembic upgrade creates schema and `alembic_version` table
- Migration failure propagates

### 4. Canonical Lifecycle

**11-state table-driven lifecycle** implemented in `lifecycle/service.py`:

- `LifecycleValidator` — validates all legal edges, rejects illegal jumps, checks self-loop restriction
- `LifecycleService` — validates transition requests (state match, version match, legal transition, non-empty reason)
- Tests cover all 31 legal transitions plus 8 representative illegal jumps

### 5. Replay-Ready Historical Contracts

Implemented in `replay/contracts.py`:

- `ManifestBuilder` — deterministic case IDs, evidence manifest hashing, outcome window construction
- `LeakageValidator` — future-evidence detection and filtering
- `SplitOrderIntegrity` — BUILD/DEVELOPMENT/BLIND ordering validation
- `CorrectionRelations` — correction/retraction/contradiction chain tracking

### 6. Observability

Implemented in `observability/telemetry.py`:

- Structured JSON logging with safe-key filtering
- OpenTelemetry bootstrap with in-memory test exporter
- `CorrelationContext` for run/thesis/event/case correlation IDs
- `exportable_attributes()` — excludes evidence bodies, secrets, and private paths
- Data minimization verified: no evidence body or secret leaked to spans

### 7. Bounded Operator Commands

Implemented in `operator/commands.py`:

- `db-init`, `db-migrate`, `db-status` — database lifecycle
- `schema-doctor` — expected vs actual table comparison
- `lifecycle-validate` — graph completeness check
- `inspect` — read-only thesis inspection
- `validate-manifest` — manifest JSON validation
- No scheduler, daemon, network provider, UI, or public output

## Test Evidence

| Test Area | Tests | Status |
|-----------|-------|--------|
| Domain contracts (Pydantic validation, prohibited fields) | 42 | pass |
| Persistence (FK, uniqueness, rollback, CAS, revisions) | 14 | pass |
| Alembic migration (upgrade creates schema) | 1 | pass |
| Lifecycle (all legal edges, illegal jumps, service) | 16 | pass |
| Replay (manifest determinism, leakage, split-order) | 10 | pass |
| Observability (spans, correlation, data minimization) | 7 | pass |
| Package boundaries (dependency direction) | 4 | pass |
| **WP-01 focused tests** | **94** | **pass** |
| Existing `tests/` suite (regression) | 154 | pass |
| **Total** | **248** | **pass** |

## Commands and Results

```bash
python -m pytest tests/cognition_v2/ -q
94 passed in 0.42s

python -m pytest tests/ -q
248 passed in 1.23s

git diff --check
pass
```

## Known Limits

- Application services (`application/`) are scaffold-only; business logic implemented in persistence helpers and lifecycle service.
- Replay manifest builder uses synthetic test data only. The 1,500-case corpus is deferred to WP-02.
- SQLite-specific features (WAL mode) are configured but not performance-tested.
- Operator commands are synchronous and single-thread. No multi-process support.
- Telemetry uses in-memory exporter only. Remote OTLP export is not configured.

## Unsupported Claims

This package does not support:

- The cognitive system is operational or improves market judgment
- Historical data quality is adequate
- The product is ready for live Shadow or owner-facing use
- Any trading performance exists
- The minimal runtime is sufficient under high concurrency

## Files Changed

- `market_radar/cognition_v2/` — new package (domain, persistence, lifecycle, replay, observability, operator, cli)
- `tests/cognition_v2/` — 94 new focused tests
- `docs/stage3/WP01_ENGINEERING_REPORT.md` — this report
- `docs/stage3/WP01_SCHEMA_MAP.md` — schema documentation
- `docs/stage3/WP01_PORT_REGISTER.yaml` — old asset classification

## Prohibited Actions Check

- Real or paid model calls: **0**
- API credentials: **0**
- Postgres or DBOS: **no**
- Daemon/cron/background process: **0**
- Live Shadow: **no**
- Trading/wallet/publication: **no**
- UI, vector, graph database: **no**
- Eight strategy evaluators or world model: **no**
- PR #16 modified or merged: **no**
- Executor merge: **no**
- WP-02 started: **no**
