# Stage 3 WP-01 Execution Contract

**Executor:** Reasonix  
**Mode:** Auto  
**Goal mode:** disabled  
**Issue:** #27  
**Branch:** `feat/stage3-wp01-production-foundation`  
**Canonical fingerprint:** `894c4d577a6b190217ae7661aebe0fd4f504df6c4cdcb7228b582bf92bdc27a7`

## Result

Build the production `market_radar/cognition_v2/` domain, persistence, lifecycle, observability and replay-ready foundation for the complete internal system. This package is an internal checkpoint in a complete delivery train, not a demo MVP.

## Read first

1. `PROJECT_MAINLINE.md`
2. `project/CANONICAL_STATE.yaml`
3. `project/STAGE2_EXIT.md`
4. `project/COMPLETE_ENGINEERING_DELIVERY_TRAIN.md`
5. `project/INTEGRATION_POLICY.md`
6. `project/PROJECT_PLAN.md`
7. `project/STAGE2_ACTIVE_PATH_MAP.md`
8. `project/RISK_ABSTENTION_CONSTITUTION.md`
9. `project/THESIS_LIFECYCLE.md`
10. Issue #27

## P00 — Safe synchronization

Work only from `/Users/zhuo/Desktop/市场信号/crypto-event-intelligence`.

Inspect repository, branch, remotes, status and remote SHAs. Do not reset, clean, stash, rebase or overwrite owner files. Stop with `LOCAL_STATE_REVIEW_REQUIRED` for tracked local changes or unexplained untracked product paths. Check out and fast-forward only `feat/stage3-wp01-production-foundation`. Verify the canonical fingerprint.

## P01 — Runtime and dependency lock

Use existing user-space Python 3.12. Do not modify system Python.

Pin compatible production and development dependencies for Pydantic, SQLAlchemy, Alembic, OpenTelemetry, pytest and required async test support. Record exact versions, dependency check and direct licenses. Pydantic AI may be recorded for later use but must not be called. Do not add DBOS or Postgres to the active package.

## P02 — Production package boundaries

Create:

```text
market_radar/cognition_v2/
  domain/
  application/
  persistence/
  lifecycle/
  replay/
  observability/
  operator/
```

Domain imports no SQLAlchemy, provider SDK, operator or UI code. Application depends on domain interfaces. Persistence and observability are adapters. Operator commands call application services. Add architecture/import-boundary tests. Do not turn old `market_radar/cognition/` into the new core.

## P03 — Canonical contracts

Implement validated Pydantic contracts for:

- EvidenceRecord, SourceIdentity, SourcePermission;
- EventRecord, EventRevision;
- ClaimRecord, ThesisRecord, ThesisRevision;
- ExposureLink, CounterEvidence;
- ReviewIntent, AttentionAllocation, NotificationDecision;
- HistoricalCaseManifest, OutcomeWindow, ProvenanceEdge.

Required semantics:

- publication, effective, first-seen, retrieval and assessment times;
- source authority, fact permission and hashes;
- canonical claim classes, horizons, evidence-status bands and thesis states;
- explicit abstention and missing-input reasons;
- SUPPORTED/STRONG require evidence references;
- BLOCKED/INSUFFICIENT may have no evidence references with explicit reasons;
- no numeric confidence;
- no trade, wallet, publication, order, position, leverage or model-owned transition field;
- critical identity, time and permission fields cannot silently default.

## P04 — Production persistence and Alembic

Implement SQLAlchemy models and a real Alembic baseline migration for:

- sources and source health;
- evidence and artifacts;
- events and immutable event revisions;
- theses and immutable thesis revisions;
- claims, exposures and counterevidence;
- review intents and checkpoints;
- attention and notification decisions;
- provenance edges;
- historical case manifests and outcome windows;
- run/configuration/schema/rule/model version records.

Guarantees:

- SQLite foreign keys and WAL configured;
- unique idempotency keys;
- unique event/thesis revision versions;
- current projections separate from append-only revisions;
- single-statement compare-and-swap;
- update/delete rejection for committed revisions;
- transaction rollback and close/reopen recovery;
- `alembic upgrade head` from empty temporary SQLite creates the schema;
- migration failure fails tests;
- downgrade works or an explicit irreversible-migration contract is tested.

## P05 — Lifecycle service

Implement the accepted 11-state table graph from `project/THESIS_LIFECYCLE.md`.

A transition requires expected state, expected version, reason, relevant evidence/rule references and idempotency key. Append-only revision creation and current projection update occur in one transaction.

Test every legal edge, representative illegal skips, stale-version rejection, idempotent replay and prohibition of model-controlled transitions.

## P06 — Replay-ready historical contracts

Implement:

- deterministic historical case IDs;
- BUILD / DEVELOPMENT / BLIND split labels;
- event-family and market-regime labels;
- immutable evidence-manifest hashes;
- correction, retraction and contradiction relations;
- outcome windows at 1h, 6h, 24h, 3d and 7d;
- future-evidence leakage blocking;
- split-order integrity;
- deterministic serialization and hashing.

Use synthetic fixtures only. Do not collect the 1,500-case corpus yet.

## P07 — Observability and bounded operator commands

Add structured JSON logging and OpenTelemetry bootstrap with an in-memory test exporter.

Telemetry may include IDs, timing, versions and counts. It must exclude evidence bodies, credentials, private absolute paths, raw prompts, raw model outputs and owner-identifying content.

Provide bounded commands for database initialize/migrate/status, schema doctor, lifecycle validation, manifest validation and read-only inspection. No scheduler, daemon, network provider, UI or public output.

## P08 — Port register and regression safety

Create `docs/stage3/WP01_PORT_REGISTER.yaml` and classify old assets as RETAIN, ADAPT, REPLACE, UNTOUCHED or QUARANTINED. Cover curated feed provider, public market adapters, source health, event grouping, EventStore, orchestrator, world model, strategy evaluators, arbitration, bounded shadow and operator workbench.

Do not modify or merge PR #16.

Run focused tests plus the full existing repository test suite. A pre-existing environment blocker must be reproduced against `main` and documented exactly; do not hide it.

## P09 — Reports and Git

Create:

- `docs/stage3/WP01_ENGINEERING_REPORT.md`
- `docs/stage3/WP01_SCHEMA_MAP.md`
- `docs/stage3/WP01_PORT_REGISTER.yaml`

The report separates implemented responsibility, test evidence, reused code, known limits, unsupported claims and exact commands/results.

Before commits run `git diff --check`, inspect stats and diff. Use focused commits. Push only the existing branch. After the first remote commit, create or update one Draft PR to `main` linked to Issue #27.

## Prohibited

- real or paid model calls;
- credentials;
- Postgres or DBOS;
- daemon, cron, login item or persistent background process;
- live Shadow;
- trading, wallet, order, public publishing or advice;
- UI, vector database or graph database;
- eight strategy evaluators or universal world model;
- modification or merge of PR #16;
- executor merge;
- starting WP-02.

## Final verification

Run focused WP-01 tests, full `tests/`, `git diff --check`, status, and fetch the exact remote branch SHA.

Stop with:

```text
terminal_state: <WP01_ACCEPTED_CANDIDATE|LOCAL_STATE_REVIEW_REQUIRED|DEPENDENCY_CONFLICT|WP01_REDESIGN_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 27
branch: feat/stage3-wp01-production-foundation
base: main
start_head: <sha>
final_remote_head: <40-char sha-or-unchanged>
draft_pr: <number-or-none>
python: <version>
dependency_check: <pass/fail/not-run>
package_boundary_tests: <result>
domain_contract_tests: <result>
real_alembic_upgrade: <pass/fail>
revision_immutability: <pass/fail>
optimistic_compare_and_swap: <pass/fail>
canonical_lifecycle_edges: <pass/fail>
idempotent_transition: <pass/fail>
future_leakage_blocking: <pass/fail>
split_order_integrity: <pass/fail>
manifest_determinism: <pass/fail>
otel_data_minimization: <pass/fail>
focused_tests: <result>
full_tests: <result-or-main-blocker>
git_diff_check: <pass/fail>
product_paths_changed: <list>
old_cognition_core_modified: <no-or-list>
pr_16_draft_unmerged: <pass/fail>
real_model_calls: 0
paid_api_calls: 0
postgres_installed_or_started: no
background_processes_created: 0
reports:
  - docs/stage3/WP01_ENGINEERING_REPORT.md
  - docs/stage3/WP01_SCHEMA_MAP.md
  - docs/stage3/WP01_PORT_REGISTER.yaml
blockers: <none-or-list>
```

Do not merge. GPT independently reviews and directly merges only the accepted exact remote Head.
