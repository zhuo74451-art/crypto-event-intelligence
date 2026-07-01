# WP-01 Engineering Report — Production Foundation

## Status

Accepted and merged through PR #28.

- Reviewed source Head: `c730216beb5c8f13fabee6138ae91e04037c7060`
- Merge commit: `b67724614b8d1e3275623442fadda5d69995f186`
- Python: 3.12.9 arm64
- Real or paid model calls: 0
- Postgres or DBOS: not used
- Background processes: 0

## Implemented responsibility

### Production package boundaries

`market_radar/cognition_v2/` contains explicit domain, application, persistence, lifecycle, replay, observability, operator and CLI boundaries. Domain contracts do not depend on persistence, operator, UI or provider SDK code.

### Canonical domain contracts

The package defines validated contracts for sources, evidence, events, event revisions, claims, theses, thesis revisions, exposures, counterevidence, review intents, attention allocations, notification decisions, provenance, historical case manifests and outcome windows.

Important rules include:

- event state is separate from thesis lifecycle state;
- source authority, fact permission and historical point-in-time fields are explicit;
- SUPPORTED and STRONG claims require evidence references;
- BLOCKED and INSUFFICIENT claims require structured abstention or missing-input reasons;
- no numeric confidence, trading, wallet, order, position, leverage or model-owned transition fields enter the active contract.

### Production persistence

SQLAlchemy models and the Alembic baseline cover sources, source health, evidence, events, immutable event revisions, theses, immutable thesis revisions, claims, exposures, counterevidence, reviews, checkpoints, attention, notification decisions, provenance, historical cases, outcome windows and version records.

Verified guarantees include:

- SQLite foreign keys and WAL configuration;
- unique idempotency keys and revision versions;
- immutable committed event and thesis revisions;
- optimistic compare-and-swap;
- transactional rollback and close/reopen recovery;
- Alembic upgrade and downgrade;
- Alembic-created schema parity with ORM metadata;
- bidirectional detection of missing or extra tables, columns, foreign keys and unique constraints;
- exact foreign-key target comparison.

### Transactional thesis lifecycle

The table-driven 11-state lifecycle service performs legal-edge validation, expected-state and expected-version checks, deterministic request fingerprinting, idempotent replay, immutable revision creation and current-projection compare-and-swap in one transaction.

Tests cover legal and illegal edges, stale writers, conflicting idempotency reuse, injected rollback, file-database reopen and execution against a database created only by Alembic.

### Replay-ready historical contracts

The package provides deterministic case IDs and input hashes, explicit evidence-availability validation, frozen BUILD / DEVELOPMENT / BLIND boundaries, canonical 1h / 6h / 24h / 3d / 7d outcome windows, and persisted event and correction-chain identities.

`CorrectionChainSplitValidator` uses explicit persisted identity fields only:

- missing `event_identity_id` means event-identity comparison is unavailable;
- missing `correction_chain_id` means the case is not part of a correction chain;
- no Case ID fallback is used as identity or chain authority;
- event identities and correction chains cannot cross frozen splits;
- declared chain roots must exist and remain consistent;
- BLIND cases, event identities and correction chains cannot enter tuning input through alternate case IDs.

The persisted split-audit tests initialize file databases through Alembic, dispose and reopen them without `Base.metadata.create_all()`, reconstruct manifests from stored rows and verify valid and invalid cases with exact diagnostics.

### Observability and operator controls

The package includes structured JSON logging, in-memory OpenTelemetry tests, correlation identifiers and default exclusion of evidence bodies, credentials, private paths and raw model content.

Bounded operator commands cover database initialization, migration, status, schema doctor, lifecycle validation, manifest validation and read-only inspection. No scheduler, daemon, live provider or public output is included.

## Test evidence

The accepted execution receipt reported:

```text
WP-01 focused tests: 174 passed
Stage 2 regression: 154 passed
Full repository suite: 3334+ passed, 32 pre-existing environment/dependency failures
git diff --check: pass
```

The exact Head had no GitHub Actions status checks, so acceptance was based on independent source inspection plus host-observable execution receipts. The 32 full-suite failures were reported as matching the same existing Telegram and market-resilience environment failures on `main`; they were not represented as new WP-01 regressions.

## Known limits

- The historical corpus itself is not built; WP-02 owns the 1,500+ case data factory.
- Application orchestration beyond lifecycle and persistence remains incomplete.
- SQLite concurrency and performance are not yet production-load tested.
- Telemetry uses an in-memory exporter only.
- No semantic provider is called and no cognition-quality claim is supported.
- The package is not ready for live Shadow or owner-facing production operation.

## Integration judgment

WP-01 is accepted as the production domain, persistence, lifecycle and replay-ready foundation for Stage 3. It is materially better than the prior mainline, does not modify the old cognition core or PR #16, and is the required base for WP-02 historical evidence construction.
