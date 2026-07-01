# Stage 2 External Foundation Comparison

**Status:** Active, pending compatibility spike

## Decision summary

| Responsibility | Preferred route | Current decision |
|---|---|---|
| Durable unattended workflow | DBOS Python | CONDITIONAL CANDIDATE |
| Distributed orchestration | Temporal | RESERVE |
| Batch evaluation and data flows | Prefect | REFERENCE |
| Structured semantic output | Pydantic AI and Pydantic | ADOPT after compatibility check |
| Lifecycle validation | python-statemachine | ADOPT after comparison with a table validator |
| Application persistence | SQLAlchemy and Alembic | ADOPT |
| Full event-sourcing framework | eventsourcing package | REJECT initially |
| Provenance vocabulary | W3C PROV concepts in relational records | ADAPT |
| Dataset lineage backend | OpenLineage | REJECT initially |
| Agent graph runtime | LangGraph | REJECT for core path |
| Traces and metrics | OpenTelemetry Python | ADOPT |
| Evaluation | local point-in-time runner and standard metrics | ADOPT minimal route |

## Important correction

Current DBOS documentation and package metadata describe a Postgres-backed runtime. The earlier assumption that current DBOS could use SQLite as its workflow database without additional infrastructure is not accepted.

DBOS remains the leading candidate because it offers durable workflows, recovery, waiting, scheduling and programmatic management without a separate orchestration server, but it requires a database service boundary that conflicts with the current no-background-service default unless separately approved.

No Postgres installation or background service is authorized during Stage 2.

## Python compatibility

The current stable releases of DBOS, Pydantic AI, python-statemachine and Alembic require Python 3.10 or later. The known Mac system Python 3.9.6 is insufficient.

Stage 2 may use an isolated Python 3.11 or 3.12 environment. It must not replace or modify the macOS system Python.

## Durable workflow candidates

### DBOS — conditional candidate

Strengths:

- durable workflows and steps;
- recovery from completed checkpoints;
- durable waits and scheduling;
- retries, timeouts and programmatic workflow management;
- no separate workflow orchestration server beyond Postgres.

Unresolved requirements:

- Postgres installation and operating burden;
- exact local-process startup and shutdown path;
- compatibility with application transactions and idempotency;
- recovery behavior under the project's injected failures;
- whether the value exceeds a smaller local scheduler and explicit job ledger.

DBOS is adopted only after a bounded compatibility spike and a later explicit decision on the database-service boundary.

### Temporal — reserve

Temporal remains the high-scale distributed alternative but requires a Temporal service, workers and more operational structure. It is not justified for the first internal slice.

### Prefect — reference

Prefect may support replay or bulk evaluation jobs. It does not currently own the per-thesis lifecycle because that decision requires evidence about persistent waits, exact transition ownership and recovery complexity.

### Minimal local runtime — mandatory comparison

The spike must compare DBOS against a smaller route:

- SQLAlchemy job and review-intent tables;
- one foreground scheduler process;
- idempotent claim-and-lock execution;
- explicit retry and checkpoint records;
- operator start, status, stop and resume commands.

This route is not assumed correct. It is the complexity baseline DBOS must beat.

## Semantic gateway

Pydantic AI is selected only as a thin gateway for validated structured outputs, provider abstraction, bounded retries, test models and usage accounting.

The accepted semantic topology remains two passes:

1. Thesis Synthesis;
2. Risk Challenge.

There is no free-form agent conversation, model-controlled state transition or autonomous tool loop.

## Lifecycle validation

`python-statemachine` is the preferred library candidate for legal-transition validation. The compatibility spike must compare it with a small table-driven validator. The application database remains authoritative in either route.

## Application persistence

SQLAlchemy and Alembic replace new raw SQLite schema strings.

The application domain may begin on SQLite with WAL for the isolated local slice, but the workflow runtime database is a separate decision. If DBOS is accepted, Postgres may become a shared or separate database only after transaction ownership and service operation are explicitly designed.

Required domain storage:

- append-only evidence, event, claim and thesis revisions;
- current-state projections;
- optimistic versions and idempotency constraints;
- review intents, notification decisions and resource usage;
- explicit provenance relationships.

## Provenance and observability

W3C PROV concepts are adapted into local relational records and hashes. No RDF, graph database or OpenLineage backend is needed initially.

OpenTelemetry traces and metrics are adopted for retrieval, model, transition, recovery and resource spans. Structured JSON application logs remain the initial logging route.

## Evaluation

A local deterministic evaluator owns project-specific replay, leakage, abstention, attention, lifecycle, recovery and resource metrics. Generic packages may compute statistics but do not define project semantics.

## Dependency and license rule

Before implementation, accepted versions must be pinned with hashes or a lock file, Python requirements and license records. Current candidate libraries use permissive licenses, but version and transitive dependency evidence must be captured by the compatibility spike.

## Reopen conditions

Reopen the foundation choice when:

- DBOS requires unacceptable background infrastructure or fails recovery tests;
- the minimal local runtime provides equivalent guarantees with lower complexity;
- Pydantic AI does not validate the chosen low-cost provider reliably;
- a table-driven transition validator is simpler than python-statemachine;
- later scale requires Temporal;
- selected dependencies conflict on Python or transitive requirements.
