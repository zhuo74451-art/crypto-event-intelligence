# Complete Engineering Delivery Train

**Status:** Active plan  
**Delivery target:** complete internal production version, not a demo MVP

## Delivery principle

The project is built as a sequence of mergeable internal work packages that converge on one complete result. Each accepted package is merged into `main` immediately and becomes the next starting point.

Historical replay and backtest evidence are built early. Live Shadow is used only after the system has passed large offline evaluation and does not require continuous owner supervision.

## Final internal product result

The completed system must autonomously:

- ingest approved event and market evidence;
- preserve source, time, permission and provenance integrity;
- resolve and revise events;
- create, abstain from, strengthen, weaken, invalidate, expire, archive and reopen theses;
- map real asset and theme exposures;
- reason separately by horizon;
- challenge its own mechanism and exposure claims;
- allocate bounded machine attention;
- schedule and recover follow-up reviews;
- compare itself with simple baselines over historical data;
- generate sparse material alerts and periodic owner summaries;
- remain silent when no material change occurs;
- expose exact status, stop, resume, inspect and replay controls.

## Work packages

### WP-01 — Production engineering foundation

Result:

- supported Python runtime and locked dependencies;
- clean `cognition_v2` package boundaries;
- canonical Pydantic contracts;
- SQLAlchemy models and Alembic migrations;
- append-only revisions and current projections;
- table-driven lifecycle validator;
- structured logging and OpenTelemetry bootstrap;
- exact unit and migration tests.

No semantic model call and no live loop.

### WP-02 — Historical evidence and point-in-time data factory

Result:

- reproducible historical case manifest;
- evidence artifact storage and hashes;
- publication, effective, first-seen, retrieval and assessment times;
- event correction and contradiction records;
- market outcome windows at 1h, 6h, 24h, 3d and 7d;
- time-ordered build, development and final blind sets;
- future-evidence leakage validator;
- initial multi-domain historical corpus.

Initial target:

- at least 1,500 historical event cases;
- six major event families;
- multiple market regimes;
- deterministic rebuild and audit report.

### WP-03 — Evidence Gate and event identity

Result:

- source-specific fact permissions;
- entity and asset identity resolution;
- exact duplicate and correction handling;
- explicit candidate relationships for non-exact similarity;
- conflict preservation;
- immutable event revisions;
- point-in-time context assembly;
- adaptation of approved existing acquisition providers.

### WP-04 — Persistent thesis portfolio

Result:

- Thesis, ThesisRevision, Claim, ExposureLink, CounterEvidence, ReviewIntent, AttentionAllocation and NotificationDecision;
- legal lifecycle transitions;
- optimistic versioning and idempotency;
- provenance from evidence through owner output;
- portfolio caps and thesis-scoped retrieval;
- no-change decay, expiry and archive rules.

### WP-05 — Two-pass cognition engine

Result:

- Thesis Synthesis structured pass;
- Risk Challenge structured pass;
- bounded repair and deterministic fallback;
- provider abstraction for approved low-cost or local models;
- versioned prompts, schemas and model configurations;
- no model-controlled lifecycle transition or external action;
- offline fixture and historical-case execution.

### WP-06 — Deterministic arbitration and abstention

Result:

- L0 evidence gates;
- typed claim permission;
- evidence-status bands;
- mandatory abstention;
- claim narrowing;
- disagreement preservation;
- allowlisted attention actions;
- notification materiality and silence decisions;
- resource and call limits.

### WP-07 — Durable unattended runtime and operator controls

Result:

- SQLAlchemy ReviewIntent scheduler;
- conditional atomic claiming;
- persisted checkpoints, retry limits and failure states;
- restart recovery and duplicate prevention;
- evidence-triggered wake-up and scheduled review;
- exact status, doctor, inspect, stop, resume and replay commands;
- no hidden daemon requirement;
- bounded foreground or explicitly launched long-run process.

### WP-08 — Historical replay and baseline laboratory

Result:

- walk-forward point-in-time replay;
- EVENT_ONLY, PRICE_ONLY, ONE_SHOT, ALWAYS_NEUTRAL, FORCED_JUDGMENT and SYNTHESIS_ONLY baselines;
- important-event recall;
- weak-evidence rejection;
- admission precision;
- mechanism and exposure correctness;
- horizon-separated direction quality;
- abstention precision and coverage;
- invalidation latency;
- attention efficiency;
- notification precision;
- resource use and recovery metrics;
- results by domain and market regime.

### WP-09 — Adversarial, recovery and data-quality evaluation

Result:

- duplicate and conflicting sources;
- delayed corrections and retractions;
- stale market context;
- entity ambiguity and impersonation;
- malformed semantic output;
- source outage;
- budget exhaustion;
- process restart during transition;
- repeated no-change reviews;
- decisive invalidation evidence;
- migration and database recovery drills.

### WP-10 — Complete internal production integration

Result:

- six event families;
- multi-asset and multi-thesis operation;
- complete evidence-to-thesis-to-review path;
- historical replay and evaluation commands;
- daily and weekly summaries;
- sparse material alerts;
- resource, health and recovery views;
- installation and operator documentation;
- one-command bounded launch, exact stop and restart recovery.

This is the first owner-usable internal version. Earlier packages are internal checkpoints, not separate MVP deliveries.

### WP-11 — Offline blind evaluation

Result:

- frozen final blind set not used for tuning;
- exact configuration and model versions;
- baseline comparison;
- quality, abstention, attention and recovery thresholds;
- continue, change, reduce-scope or stop decision.

No live owner validation is required during the run.

### WP-12 — Unattended live Shadow

Result:

- at least 21 calendar days and 100 qualified cases;
- read-only approved inputs;
- no trade, wallet, public publication or production external effect;
- automatic state maintenance, recovery and reporting;
- final comparison with offline results and baselines;
- one final owner decision on long-term internal operation.

## Merge and quality policy

Each package uses:

```text
bounded branch and Draft PR
  -> exact remote Head inspection
  -> focused and regression evidence
  -> direct merge by GPT when better than main
  -> remote main verification
  -> canonical state update
```

Do not leave accepted improvements in Draft branches. Do not merge existence-only tests, stale reports, unsupported claims or partial paths that make `main` internally inconsistent.

## Backtest-first allocation

Target engineering and validation effort:

- historical evidence, replay, blind evaluation and adversarial testing: 55–65%;
- cognition and lifecycle product implementation: 25–35%;
- unattended live Shadow and owner-facing verification: 10–15%;
- routine real-time owner testing: approximately zero.

## Owner involvement

Owner decisions are expected only for:

- a material recurring model or infrastructure cost;
- protected credentials or private data access;
- public operation or irreversible external effects;
- final blind-evaluation acceptance;
- final live-Shadow acceptance.

Routine implementation, testing, repair, merging and evidence review remain autonomous.
