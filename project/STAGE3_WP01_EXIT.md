# Stage 3 WP-01 Exit — Production Engineering Foundation

**Status:** Accepted  
**PR:** #28  
**Reviewed Head:** `c730216beb5c8f13fabee6138ae91e04037c7060`  
**Merge Commit:** `b67724614b8d1e3275623442fadda5d69995f186`

## Accepted result

WP-01 establishes the production `market_radar/cognition_v2/` foundation:

- canonical Pydantic contracts;
- separate event and thesis states;
- SQLAlchemy models and Alembic migrations;
- bidirectional migration/ORM schema parity;
- immutable event and thesis revisions;
- optimistic compare-and-swap;
- transactional 11-state thesis lifecycle transitions;
- deterministic idempotency request fingerprints;
- point-in-time historical evidence contracts;
- deterministic case and manifest hashing;
- BUILD / DEVELOPMENT / BLIND split controls;
- strict persisted event-identity and correction-chain isolation;
- BLIND tuning exclusion;
- canonical outcome windows;
- structured logging and OpenTelemetry bootstrap;
- bounded database, doctor, validation and inspect commands.

## Evidence

The accepted execution receipt reported:

```text
WP-01 focused tests: 174 passed
Stage 2 regressions: 154 passed
Full repository suite: 3334+ passed with 32 matching pre-existing environment/dependency failures
git diff --check: pass
```

Exact source inspection confirmed the critical responsibilities rather than relying on test names alone.

## Boundaries retained

- no real or paid model calls;
- no Postgres or DBOS;
- no daemon or persistent background process;
- no trading, wallet, public publication or advice path;
- no UI;
- no modification or merge of Draft PR #16;
- no claim that market cognition quality is proven.

## What WP-01 does not prove

- the historical corpus is sufficiently broad or clean;
- public historical sources can reconstruct every required point-in-time fact;
- outcome windows are complete across all affected assets;
- the system improves judgment against baselines;
- SQLite is sufficient under later multi-process load;
- the system is ready for live Shadow.

## Next package

WP-02 builds the historical evidence and point-in-time data factory, including a reproducible corpus of at least 1,500 qualified cases across six event families and multiple market regimes.
