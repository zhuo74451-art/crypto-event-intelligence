# Stage 2 Repository Responsibility Audit — Pass 1

**Status:** Active evidence-backed audit  
**Refs:** `main` plus Draft PR #16 `workbench/cognition-spine-v1`  
**Implementation:** prohibited during this pass

## Executive judgment

Draft PR #16 is not an almost-finished version of the accepted autonomous system.

It is a useful prototype collection containing typed records, fixture ingestion, deterministic helpers and a one-shot artifact pipeline. Its current active path does not implement persistent theses, attention allocation, durable reviews, typed claim limits, two-pass semantic judgment, legal thesis transitions or longitudinal validation.

The branch repeatedly treats these as equivalent:

- a dataclass exists -> a responsibility is implemented;
- a domain object exists -> a world domain is available;
- a fixture passes -> a market judgment is valid;
- a file is written -> an integrated product result exists;
- a numeric average exists -> confidence is calibrated;
- one batch run exists -> Shadow operation exists.

Those equivalences are rejected.

## Repository-wide dependency fact

`requirements.txt` on `main` contains only `pandas` and `requests>=2.28.0`.

Therefore the repository currently has no declared mature dependency for:

- durable workflow recovery;
- schema migrations;
- validated semantic output;
- state-machine validation;
- traces and metrics;
- model-provider abstraction.

## Evidence and intake

### Useful material

`intake_contracts.py` preserves lanes, timestamps, source identity, authority classes, fact permission, hashes, entities, assets and origin modes.

`input_loader.py` contains deterministic duplicate-ID handling and artifact hash verification.

### Problems

- contracts are permissive dataclasses rather than validated boundary models;
- many fields default to empty values that can pass deep into the pipeline;
- `importance`, `urgency`, `novelty` and confidence values are uncalibrated floats;
- the QuickFlash SQLite loader calls the leakage check but discards its result;
- direct-source identity is a hard-coded set;
- direct evidence is marked confirmed by source-name routing rather than source-specific fact permission;
- errors are often collected without blocking the affected claim;
- broad exception handling hides malformed rows.

### Classification

`ADAPT` — retain the lane and evidence concepts; replace boundary handling with validated Pydantic models and explicit gate results.

## Event identity and grouping

### Useful material

- exact grouping by upstream dedup key;
- deterministic event IDs;
- observation membership;
- explicit source conflicts;
- tests for duplicate IDs, generic-title separation and different-date separation.

### Problems

- fuzzy grouping is primarily `SequenceMatcher` title similarity plus a time window;
- the implementation comments mention asset and entity overlap, but the function does not require them;
- fuzzy merges alter an existing event without an auditable merge-decision object;
- title differences are treated as conflicts even when they may be harmless paraphrases;
- event status is set to active merely because origin is live.

### Classification

- exact-key grouping and conflict preservation: `ADAPT`;
- current fuzzy fallback: `QUARANTINE`;
- live-origin automatic activation: `REMOVE`.

## Persistence and revisions

### Useful material

- SQLite WAL usage exists elsewhere on `main`;
- explicit transactions, foreign keys and event revision intent;
- run history and operator manifests already exist;
- idempotency is recognized as a requirement.

### Problems in PR #16 EventStore

- current state and revision snapshots are mixed without one authoritative append-only ledger;
- the orchestrator creates a revision with number 1 regardless of whether an event already existed;
- `get_event_as_of()` may return the current state labelled as revision 0 when no prior revision is found;
- state updates and revision insertion are not consistently committed as one domain operation;
- raw `sqlite3` schema strings have no reviewed migration history;
- thread locking is process-local and does not provide durable workflow ownership;
- there is no thesis, review-intent, notification or model-call persistence.

### Classification

- append-only revision intent: `RETAIN` as a design requirement;
- current EventStore implementation: `ADAPT` by replacement with SQLAlchemy/Alembic tables;
- current manual schema migration pattern: `QUARANTINE` for new cognition tables;
- existing operational data may be migrated, not discarded.

## Cognition orchestrator

### Critical semantic failures

The current one-shot orchestrator:

- moves every candidate event to active even when no supporting confirmation exists;
- derives a direction hypothesis from the sign of a numeric expectation gap;
- uses price response as confirmation without controlling for competing market drivers;
- derives volume baseline from `pre_event_ref` when no volume baseline exists;
- uses title keywords to create transmission paths;
- averages hand-assigned weights into overall confidence;
- does not maintain persistent theses or scheduled follow-up reviews;
- cannot implement the accepted lifecycle or attention policies.

### Classification

- stage/result envelope and artifact-writing pattern: `ADAPT`;
- current cognition decision path: `REMOVE` from the future active path;
- retain it only as a legacy fixture harness until replacement tests cover its useful parsing behavior.

## World model

### Evidence

The branch declares eleven domains, but the builder creates eight of them as objects whose primary content is `unavailable_variables=["no_data_received"]`.

`available_domains()` reports every non-null object as available, including those unavailable placeholders.

The macro domain contains BTC price, ETH price and funding rate rather than a real macro-liquidity state. The regime classifiers use fixed thresholds without research status, calibration or applicability evidence.

### Classification

- explicit domain-availability concept: `ADAPT`;
- eleven-domain object hierarchy: `QUARANTINE`;
- current world-builder availability claim: `REMOVE`;
- current regime and priced-in thresholds: `QUARANTINE` as unvalidated hypotheses.

The replacement should assemble only context requested by an active thesis rather than constructing an always-present universal world model.

## Mechanism and exposure

### Evidence

`transmission.py` maps title keywords such as `sec`, `hack` and `release` to generic mechanism strings.

It does not establish entity-specific exposure, intermediate causal steps, assumptions, source support or horizon.

### Classification

Current keyword transmission: `REMOVE` from judgment. It may survive only as a low-cost discovery tagger.

Mechanism and exposure become structured output of the bounded Thesis Synthesis pass, followed by Risk Challenge and deterministic gate checks.

## Research claims

### Useful material

- claim IDs, source metadata, applicable regime, falsification, limitations and lifecycle intent;
- status-transition validation concept;
- explicit stale and rejected states.

### Problems

- Markdown parsing is ad hoc;
- the half-life rule marks stale only after twice the configured half-life without domain evidence;
- historical and shadow support are labels, not linked evaluation results;
- no immutable claim revisions or provenance;
- no binding between a research claim and a mechanism decision.

### Classification

`ADAPT` — preserve the claim object and legal-transition idea; replace storage, parsing and evidence linkage.

## Eight strategy evaluators

### Evidence

The evaluators use fixed rules such as:

- absolute surprise greater than 2 or 3;
- price movement greater than 5%;
- funding greater than 0.001;
- unlock greater than 1% of supply;
- critical incident and TVL greater than ten million.

The integrated runner passes `None` for many required variables, runs every evaluator for every event, and does not connect the rules to accepted research evidence or historical support.

Some expiry and invalidation strings are semantically questionable; for example, continued extreme funding is labelled an invalidation for a leverage-dislocation observation.

### Classification

All eight strategy evaluators: `QUARANTINE`.

They may become named research hypotheses in future evaluation, but none belongs in the first active autonomous path. The first product is market thesis maintenance, not strategy eligibility.

## Arbitration and confidence

### Evidence

The current arbitration:

- marks an event `ACTIONABLE_WATCH` whenever any strategy is eligible and no source conflict exists;
- computes confidence from the fraction of eligible strategies and arbitrary fixed weights;
- lowers confidence through arithmetic rather than claim-level evidence gates;
- does not consume a structured mechanism, exposure or adversarial risk result.

`assessment.py` averages confidence-component values. `decision_pipeline.py` packages the resulting number as overall confidence.

### Classification

- allowlisted internal outcomes and disagreement fields: `ADAPT`;
- current arbitration logic: `REMOVE`;
- all numeric confidence aggregation: `REMOVE`;
- Market Decision Packet as the final product object: `QUARANTINE`.

The replacement output is a Thesis Revision plus Attention Action, using evidence-status bands until calibration exists.

## Shadow and evaluation

### Evidence

The current shadow runner is one batch invocation. It does not maintain state across time.

The evaluation code:

- calls confidence bucket counts “calibration” without comparing confidence to outcomes;
- detects leakage by searching `known_unknowns` text;
- attempts to match outcomes using a substring of event ID;
- does not implement the documented event-only, price-only or one-shot baselines;
- reports coverage and artifact counts rather than longitudinal judgment quality.

### Classification

- one-shot artifact runner: `ADAPT` as a replay command;
- current evaluation metrics and historical-baseline claims: `REMOVE`;
- current use of the term Shadow: `REMOVE` until state persists across multiple reviews.

## Tests

### Retain as seed tests

- duplicate observation rejection;
- exact cross-source merge;
- generic-title false-merge prevention;
- same-title different-date separation;
- deterministic IDs;
- artifact hash mismatch;
- future-evidence blocking;
- basic transaction rollback and idempotency cases.

### Quarantine or rewrite

Many end-to-end tests assert only that:

- a result object exists;
- one or more packets exist;
- output files exist;
- status is `ok` or `degraded`;
- a registry contains eight components.

These prove assembly, not semantic responsibility.

### Missing tests

- persisted thesis revisions across runs;
- legal and illegal lifecycle transitions;
- mandatory claim-level abstention;
- risk challenge changes the result;
- attention caps and eviction;
- no-change decay;
- durable wait and restart recovery;
- resource exhaustion;
- notification sparsity;
- point-in-time baseline comparison;
- model schema failure and deterministic fallback;
- provenance from evidence to owner output.

## Main-branch operational components

### Useful existing assets

`operator_workbench.py`, `run_history.py`, manifests, diagnoses, status and stop-marker concepts already provide an operator shell and auditable run metadata.

### Problems

- the current workbench is tied to older post-MVP one-shot profiles;
- schema migration is manually encoded;
- status is not a durable thesis scheduler;
- the Mac receipt already exposed a schema constant mismatch;
- a stop marker does not replace durable cancellation and persisted pending work.

### Classification

`ADAPT` — retain CLI vocabulary, status, doctor, manifest, diagnosis and read-only inspection patterns; connect them to DBOS workflow state and the new application database.

## Missing capability register

The accepted product currently lacks:

- durable cognition workflow and review scheduling;
- validated application database schema and migrations;
- persistent Thesis, ThesisRevision, ExposureLink and ReviewIntent objects;
- legal lifecycle transition service;
- structured Thesis Synthesis and Risk Challenge model passes;
- deterministic claim-level arbitration;
- evidence-status bands and mandatory abstention enforcement;
- active portfolio and resource governor;
- owner notification batching and suppression;
- OpenTelemetry traces and metrics;
- prompt, model, rule and configuration version recording;
- true point-in-time replay and accepted baselines;
- longitudinal live Shadow state;
- adversarial recovery test harness.

## Pass-1 architecture conclusion

The smallest route does not merge PR #16 and then patch it.

The preferred route is:

1. preserve useful evidence, fixture and operator concepts;
2. build a new narrow core from `main` using mature foundations;
3. port only individually accepted modules or tests;
4. keep PR #16 Draft and use it as a component quarry and failure record;
5. do not carry the eight-strategy or universal-world-model architecture into the first slice.

## Remaining audit work

Before Stage 2 exit:

- inspect acquisition, source-health and market-provider contracts on `main`;
- map all reusable operator and replay components;
- verify DBOS, Pydantic AI and transition-library compatibility in a tiny spike without product behavior;
- produce the final active-path map and dependency graph;
- identify exact files to port, supersede or leave untouched;
- compile the first complete engineering slice.
