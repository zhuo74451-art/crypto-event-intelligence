# Stage 2 Architecture Decision

**Status:** Semantic architecture accepted; durable runtime pending spike

## Accepted architecture

The six Stage 1 roles are accountability boundaries, not six separate model agents.

```text
Approved Inputs
  -> Deterministic Evidence Gate
  -> Deterministic Event and Candidate Builder
  -> Semantic Pass A: Thesis Synthesis
  -> Semantic Pass B: Risk Challenge
  -> Deterministic Arbitration
  -> Deterministic Lifecycle Transition
  -> Durable Review Scheduling
  -> Material Notification or Silence
```

## Deterministic ownership

- Evidence Gate owns identity, permission, time, provenance, hashes, duplicate and conflict rules.
- Candidate Builder owns exact event linkage, prior-thesis retrieval, point-in-time context and missing-input maps.
- Arbitration owns hard gates, claim narrowing, disagreement preservation and allowlisted attention actions.
- Lifecycle and Resource service owns legal transitions, versions, review intent, no-change decay, caps, retries and notifications.
- The durable runtime owns execution progress, waits, cancellation, resume and recovery; it never owns thesis truth.

## Semantic ownership

### Thesis Synthesis

One structured pass may propose materiality, mechanism, exposure, horizon, expectation, priced-in interpretation, next evidence and invalidation conditions.

It cannot grant fact permission, override missing evidence, choose a final state or cause an external action.

### Risk Challenge

One structured pass must produce counterevidence, alternatives, hidden assumptions, exposure and horizon mismatch, priced-in and crowding risk, claim narrowing and falsification.

It cannot veto through unsupported opinion.

The same model may perform both passes initially with separate contracts. Model diversity is an experiment, not a dependency.

## Rejected topology

No free-form agent-to-agent conversation, autonomous tool loop, model-controlled transition, message broker, graph database, vector database, separate agent server or distributed worker pool is allowed in the first slice without new evidence.

## Durable runtime decision

DBOS is the leading candidate, not yet an accepted dependency.

Current official material describes a Postgres-backed runtime. Stage 2 therefore compares:

### Candidate A — DBOS plus Postgres

Potential value:

- durable workflow steps and waits;
- recovery, retry, cancellation and status;
- less custom scheduling code.

Unresolved cost:

- Postgres installation and lifecycle;
- background-service and stop behavior;
- transaction and idempotency boundaries;
- local operating burden.

### Candidate B — minimal local durable runtime

Components:

- SQLAlchemy job and review-intent tables;
- one foreground scheduler process;
- claim-and-lock execution;
- explicit step checkpoints, retry records and wake-up times;
- exact start, status, stop and resume commands.

Candidate B must not become an improvised daemon. It is acceptable only if its recovery guarantees are explicit, tested and materially simpler than DBOS.

The compatibility spike chooses between them or keeps both unresolved. It may not install or start Postgres without separate authorization.

## Accepted first-slice components

- isolated Python 3.11 or 3.12 environment;
- Pydantic and Pydantic AI after structured-output compatibility evidence;
- SQLAlchemy and Alembic for application state;
- python-statemachine or a simpler table validator after comparison;
- OpenTelemetry traces and metrics;
- existing read-only acquisition providers behind adapters;
- two semantic pass definitions;
- one application database.

## First complete slice

One event family must pass through:

- approved evidence;
- event resolution;
- thesis creation or claim-level abstention;
- persisted revision;
- one scheduled follow-up;
- restart recovery;
- material notification or silence;
- point-in-time replay.

It excludes strategy evaluators, universal world-model construction, trading, public publication and public UI.

## Reopen conditions

Reopen the architecture if:

- one semantic pass performs equally well at lower cost;
- deterministic-only processing meets the same outcome;
- two passes cannot produce adequate structured results;
- the local runtime beats DBOS on guarantees and complexity;
- DBOS justifies its Postgres boundary through measured recovery value;
- later scale requires Temporal or another distributed orchestrator.
