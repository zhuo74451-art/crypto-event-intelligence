# Stage 2 Foundation Compatibility Spike

**Status:** Ready for bounded execution  
**Nature:** audit evidence, not product implementation

## Purpose

Resolve the remaining generic-foundation uncertainty before compiling the first product slice.

The spike compares:

1. current candidate dependencies in an isolated supported Python environment;
2. DBOS workflow value and infrastructure requirements;
3. a minimal local durable-review ledger;
4. Pydantic AI structured-output behavior without paid model calls;
5. python-statemachine against a table-driven validator;
6. SQLAlchemy, Alembic and OpenTelemetry compatibility.

## Hard boundaries

- no product behavior;
- no change to the active cognition pipeline;
- no merge or modification of Draft PR #16;
- no paid API or real model call;
- no public output;
- no wallet, trading or publishing capability;
- no Postgres installation or service start;
- no daemon, cron, login item or persistent background process;
- no modification of macOS system Python;
- all experiment files remain under `experiments/stage2_foundation_spike/` and its focused tests;
- current project requirements remain unchanged until the audit accepts dependencies.

## Runtime prerequisite

Use an existing Python 3.11 or 3.12 executable in an isolated virtual environment. Current candidate packages require Python 3.10 or later.

If no supported user-space Python exists, stop with `PYTHON_RUNTIME_REQUIRED`. Do not use `sudo` or replace `/usr/bin/python3`.

## Dependency evidence

Install current stable candidate versions only inside the experiment environment and record:

- exact package versions;
- Python version and architecture;
- resolved dependency tree;
- package licenses where available;
- installation warnings and conflicts;
- a reproducible requirements lock or freeze file.

Candidates:

- DBOS;
- Pydantic and Pydantic AI;
- SQLAlchemy and Alembic;
- python-statemachine;
- OpenTelemetry API and SDK;
- pytest.

## Experiment A — Pydantic semantic gateway

Using only Pydantic AI test or function models:

- validate `ThesisSynthesisResult` and `RiskChallengeResult` schemas;
- reject missing evidence references and invalid enums;
- exercise one bounded repair attempt;
- verify usage and retry limits are observable;
- prove that the model result cannot choose a lifecycle transition or external action.

No network model call is allowed.

## Experiment B — persistence and migration

Using a temporary SQLite database:

- define minimal Evidence, Event, Thesis, ThesisRevision and ReviewIntent tables;
- enforce foreign keys, unique idempotency keys and optimistic thesis versions;
- create and apply one Alembic migration;
- prove rollback on a failed revision transaction;
- reopen the database and recover current state from append-only revisions.

This schema is disposable experiment evidence, not the accepted production schema.

## Experiment C — lifecycle validator

Implement the accepted legal state graph twice:

- with python-statemachine;
- with a compact table-driven validator.

Compare:

- code size;
- illegal-transition detection;
- startup validation;
- test readability;
- dependency and maintenance cost.

Record `LIBRARY`, `TABLE`, or `UNRESOLVED`; do not choose by preference alone.

## Experiment D — minimal local durable-review runtime

Create a foreground-only proof using the experiment database:

- persist a review intent with `due_at` and idempotency key;
- claim one due item atomically;
- record step checkpoints and retry count;
- stop after a simulated failure;
- close and reopen the process;
- resume from the last committed checkpoint;
- cancel and resume through explicit commands;
- prevent duplicate execution of the same review.

No sleeping background process is required. Tests advance a controlled clock.

## Experiment E — DBOS feasibility

Without installing or starting Postgres:

- install and import DBOS in the isolated environment;
- record the current database and infrastructure requirements from installed metadata and official configuration surfaces;
- determine whether a meaningful durable workflow test can run without an external Postgres service;
- inspect status, cancel, resume, wait and recovery APIs available in the installed version;
- compare the required operational surface with Experiment D.

Allowed results:

- `DBOS_READY_WITHOUT_NEW_SERVICE`;
- `DBOS_REQUIRES_POSTGRES_AUTHORIZATION`;
- `DBOS_INCOMPATIBLE`;
- `DBOS_UNRESOLVED`.

The spike must not fake workflow success when no durable database exists.

## Experiment F — observability

Using an in-memory OpenTelemetry exporter:

- emit one retrieval span;
- emit both semantic-pass spans;
- emit one arbitration and transition span;
- attach run, event, thesis, revision, retry and resource attributes;
- verify no evidence body or secret is exported by default.

## Required tests

- structured-output acceptance and rejection;
- bounded repair and fallback;
- migration upgrade and rollback;
- optimistic-version conflict;
- legal and illegal transitions in both validators;
- restart and checkpoint recovery;
- duplicate review prevention;
- cancel and resume;
- DBOS feasibility classification;
- trace correlation and data-minimization checks.

## Required report

`FOUNDATION_SPIKE_REPORT.md` must contain:

- environment and exact versions;
- pass or blocker for each experiment;
- dependency conflict and license table;
- measured code and operational complexity;
- DBOS versus minimal-runtime comparison;
- state-machine validator decision;
- Pydantic AI gateway decision;
- accepted, rejected and unresolved dependencies;
- recommendation for the first complete slice;
- exact files created;
- tests and commands;
- explicit statement that no product behavior was implemented.

## Exit decisions

The spike ends in one of:

- `FOUNDATIONS_ACCEPTED`;
- `MINIMAL_RUNTIME_PREFERRED`;
- `POSTGRES_DECISION_REQUIRED`;
- `PYTHON_RUNTIME_REQUIRED`;
- `DEPENDENCY_CONFLICT`;
- `FOUNDATION_REDESIGN_REQUIRED`.

Stop after the report. Do not start the first product slice.
