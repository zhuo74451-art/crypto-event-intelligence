# Stage 2 External Foundation Comparison

**Status:** Accepted first-pass decision  
**Scope:** generic runtime, state, semantic gateway, provenance, evaluation and observability capabilities

## Decision summary

| Responsibility | Preferred route | Decision |
|---|---|---|
| Durable unattended workflow | DBOS Python | ADOPT for first complete slice |
| Distributed high-scale orchestration | Temporal | RESERVE; do not adopt initially |
| Data-pipeline deployment and experiments | Prefect | REFERENCE only |
| Structured semantic output | Pydantic AI plus Pydantic models | ADOPT as thin model gateway |
| Thesis lifecycle validation | python-statemachine | ADOPT behind local transition service |
| Application persistence | SQLAlchemy 2.x plus Alembic | ADOPT |
| Full event-sourcing framework | eventsourcing package | REJECT for first slice |
| Evidence provenance model | W3C PROV concepts plus local hashed records | ADAPT concepts; do not add RDF stack |
| Dataset lineage backend | OpenLineage | REJECT for first slice |
| Agent graph runtime | LangGraph | REJECT for core path |
| Traces and metrics | OpenTelemetry Python | ADOPT |
| Log transport through OpenTelemetry | OpenTelemetry Logs | DEFER; Python logs remain less mature than traces and metrics |
| Evaluation | custom point-in-time runner plus standard statistical metrics | ADOPT minimal local implementation |

## Durable workflow decision

### DBOS — selected

Why it fits the first internal deployment:

- Python-native durable workflows and steps;
- automatic recovery from the last completed step;
- durable sleep for future review times;
- workflow timeouts, retry limits, cancel, resume and status inspection;
- SQLite works without setup for local development;
- Postgres is the recommended production path;
- no separate orchestration server is required for the local open-source path;
- current project is a single-owner internal system before any distributed scale requirement.

Required constraints:

- DBOS owns workflow progress, not domain truth;
- thesis and evidence state remain in the application database;
- every external or database-writing step is idempotent;
- application and workflow versions are recorded in every run;
- Conductor or another hosted control plane is not required for the first slice;
- production migration to Postgres is a later evidence-based decision.

### Temporal — reserved

Temporal has stronger multi-node, long-running and operational guarantees, but introduces a Temporal service, workers, deterministic workflow constraints and higher operating complexity.

Use Temporal only if later evidence shows a need for:

- multiple active executors;
- large workflow volume;
- cross-service signals and task queues;
- stricter distributed recovery;
- operational scale that exceeds the DBOS single-application model.

### Prefect — not the cognition runtime

Prefect is valuable for scheduled data flows and evaluation jobs. It is not selected as the core thesis-lifecycle runtime because the project needs durable per-thesis waits, exact state transitions and recovery semantics rather than primarily deployment-oriented data orchestration.

It may later run offline replay or bulk evaluation jobs if that is simpler than the core runtime.

## Semantic execution decision

### Pydantic AI — selected as a gateway, not an agent society

Use Pydantic AI only for:

- provider abstraction, including OpenAI-compatible providers such as DeepSeek and Ollama;
- validated structured outputs;
- bounded output repair;
- usage accounting and hard call limits;
- test and function models for deterministic tests.

Do not use:

- autonomous tool-selection loops;
- free-form memory;
- subagent societies;
- model-controlled workflow or lifecycle transitions.

The accepted architecture uses two semantic passes:

1. `THESIS_SYNTHESIS` — mechanism, exposure, horizon, expectations, priced-in interpretation and missing links;
2. `RISK_CHALLENGE` — counterevidence, alternative explanations, hidden assumptions, falsification and claim narrowing.

Both passes may initially use the same configured model with different contracts. A second independent model becomes optional validation infrastructure, not an architectural requirement.

## Lifecycle validation decision

Use `python-statemachine` as a small validation layer for the accepted legal state graph.

The application database remains authoritative. The library validates transition legality and catches unreachable or invalid state definitions; it does not persist state or choose transitions.

The transition service must additionally enforce:

- expected prior version;
- evidence and judgment references;
- actor or rule version;
- idempotency key;
- checkpoint before commit;
- append-only revision after commit.

## Persistence decision

Adopt SQLAlchemy and Alembic rather than continuing raw `sqlite3` schema strings.

Initial database route:

- SQLite with WAL for the local internal slice;
- explicit foreign keys and unique idempotency constraints;
- append-only evidence, event, claim and thesis-revision tables;
- separate current-state projections for efficient reads;
- Alembic migrations reviewed and tested;
- a later Postgres migration only when concurrency or DBOS production needs justify it.

Do not adopt a full event-sourcing library initially. The required domain is broader than one aggregate model and already needs evidence, workflow, review, notification and evaluation records. A small explicit append-only ledger is easier to audit.

## Provenance decision

Use W3C PROV concepts as a vocabulary:

- Entity — evidence artifact, event revision, thesis revision or output;
- Activity — retrieval, normalization, semantic judgment, arbitration, transition or evaluation;
- Agent — source, deterministic rule, model configuration or executor;
- derivation and usage edges — explicit links between inputs and outputs.

Implement these concepts in local relational tables and hashes. Do not add RDF, a graph database or an OpenLineage backend in the first slice.

OpenLineage is optimized for dataset and job lineage across data platforms. The current internal thesis system needs claim-level provenance and would gain more complexity than value.

## Observability decision

Adopt OpenTelemetry for:

- workflow and semantic-pass traces;
- retrieval, model, transition and recovery spans;
- counters and latency histograms;
- resource-budget attributes;
- correlation by run, event, thesis and revision IDs.

Keep structured JSON application logs and existing manifests initially. OpenTelemetry Python traces and metrics are stable; log signal maturity is lower.

## Evaluation decision

Do not adopt an agent-evaluation platform as the source of truth.

Build a small deterministic evaluator that:

- freezes manifests and configurations;
- performs walk-forward point-in-time replay;
- prevents future evidence;
- runs the accepted baselines;
- calculates classification, abstention, attention, recovery and resource metrics;
- produces machine-readable and Markdown reports.

Standard statistical packages may compute metrics, but project-specific claim, lifecycle and leakage semantics remain local contracts.

## License and operational notes

Selected first-slice dependencies use permissive licenses:

- DBOS Python — MIT;
- Pydantic AI — MIT;
- python-statemachine — MIT;
- SQLAlchemy and Alembic — MIT;
- OpenTelemetry Python — Apache 2.0.

Dependency versions must be pinned with lock and license records before implementation.

## External evidence reviewed

Primary documentation and repositories reviewed on 2026-07-01:

- DBOS workflows, recovery, management, timeouts, durable sleep and architecture;
- Temporal durable execution and Python SDK;
- Prefect deployments and retry behavior;
- Pydantic AI structured outputs, validation, retries and provider support;
- python-statemachine definition validation;
- SQLAlchemy SQLite behavior and Alembic migrations;
- W3C PROV data model;
- OpenLineage object model;
- OpenTelemetry Python status and instrumentation.

## Reopen conditions

Reopen this comparison if:

- DBOS cannot recover the project’s review and lifecycle workflows under injected failure;
- SQLite cannot support the required concurrency or integrity;
- Pydantic AI cannot reliably validate outputs from the chosen low-cost provider;
- transition-library integration adds more complexity than a table-driven validator;
- operational evidence requires distributed Temporal-scale execution;
- a mature evaluation package demonstrably owns the project-specific metrics with less local code.
