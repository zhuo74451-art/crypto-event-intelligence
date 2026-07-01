# Stage 2 Architecture Decision

**Status:** Accepted first-pass architecture  
**Decision:** deterministic durable pipeline with two bounded semantic passes

## Rejected assumption

The six responsibility roles defined in Stage 1 do not require six independent model agents.

Roles describe accountability. They are not a process topology.

## Selected architecture

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

### Deterministic services

1. **Evidence Gate**
   - source and fact permission;
   - time integrity and leakage blocking;
   - hashes and provenance;
   - entity identity;
   - duplicate and conflict detection.

2. **Candidate Builder**
   - event linkage;
   - prior thesis retrieval;
   - point-in-time context assembly;
   - deterministic features and missing-input map.

3. **Arbitration Service**
   - hard-gate evaluation;
   - claim narrowing;
   - lifecycle and attention action selection from an allowlist;
   - disagreement preservation;
   - no model-generated state transition.

4. **Lifecycle and Resource Service**
   - legal transition validation;
   - optimistic version checks;
   - review scheduling;
   - no-change decay;
   - portfolio caps;
   - loop and retry limits;
   - notification policy.

5. **Durable Runtime**
   - DBOS workflow and step checkpoints;
   - durable waits;
   - cancellation, resume and recovery;
   - status and resource accounting.

### Semantic pass A — Thesis Synthesis

One structured model call may propose:

- novelty and materiality;
- causal mechanism and missing links;
- genuine exposure and exposure type;
- direction by horizon;
- expectation and priced-in interpretation;
- next evidence;
- candidate invalidation conditions.

It cannot:

- grant fact permission;
- override missing or stale evidence;
- choose final lifecycle state;
- choose a trade or external action;
- exceed the schema.

### Semantic pass B — Risk Challenge

A second structured call receives the evidence bundle and Pass A result. It must produce:

- strongest counterevidence;
- alternative explanations;
- unsupported assumptions;
- exposure and horizon mismatch;
- priced-in and crowding risk;
- claim-narrowing recommendation;
- falsification conditions.

It cannot freely veto. Every challenge requires an evidence or logic reference.

## Why two passes instead of one

One pass is cheaper but encourages self-confirmation: the same generation proposes and approves its own story.

Two distinct contracts allow:

- independent validation and retries;
- separate evidence references;
- future optional model diversity;
- comparison of synthesis-only versus synthesis-plus-risk value;
- removal of the risk pass if it fails to add measurable value.

The two passes may use the same provider initially. Separate providers are an experiment, not a dependency.

## Why not a full multi-agent system

A conversational agent society would add:

- uncontrolled token growth;
- unclear responsibility for final state;
- repeated context and evidence drift;
- difficult replay and deterministic recovery;
- complex debugging and observability;
- no demonstrated advantage over two typed passes.

No agent-to-agent free-form conversation is allowed in the first complete slice.

## Why not deterministic only

A deterministic-only pipeline is retained as a baseline but is unlikely to own:

- unseen causal mechanisms;
- nuanced exposure mapping;
- competing explanations;
- cross-domain interpretation;
- novel theme discovery.

It remains useful for evidence, resource, transition and baseline responsibilities.

## Why not event-only or one-shot analysis

Event-only ranking lacks persistent hypotheses, follow-up evidence, invalidation and attention decay.

One-shot analysis cannot prove that the system updates or abandons a thesis correctly over time.

Both remain formal evaluation baselines.

## First-slice runtime components

- DBOS Python for workflow durability;
- Pydantic and Pydantic AI for contracts and two semantic passes;
- SQLAlchemy and Alembic for application state;
- python-statemachine for transition validation;
- OpenTelemetry traces and metrics;
- SQLite for local application and DBOS state during the first slice;
- existing acquisition providers behind thin input adapters.

## Complexity budget

The first slice may contain:

- one runtime process;
- one DBOS application;
- one application database;
- two semantic pass definitions;
- no message broker;
- no graph database;
- no vector database unless Stage 2 proves retrieval cannot work without it;
- no separate agent server;
- no distributed worker pool;
- no public UI requirement.

## Reopen conditions

Reopen the architecture only if evidence shows:

- two semantic passes cannot produce adequate mechanism and risk outputs;
- deterministic arbitration cannot represent necessary unresolved ambiguity;
- DBOS recovery or scheduling fails the injected tests;
- one semantic pass performs equally well with materially lower cost;
- a deterministic-only route meets the same outcome;
- distributed workload or scale requires Temporal or another orchestrator.
