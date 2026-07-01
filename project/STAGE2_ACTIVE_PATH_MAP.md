# Stage 2 Active Path Map

**Status:** Accepted first-pass target path

## Intended active path

```text
QuickFlash contract output + approved direct evidence + public market adapters
  -> Pydantic boundary validation
  -> Evidence Gate
  -> append-only EvidenceRecord and source-health update
  -> exact Event resolution and candidate relationship generation
  -> relevant prior thesis and point-in-time context retrieval
  -> Thesis Synthesis structured pass
  -> Risk Challenge structured pass
  -> deterministic claim and admission gates
  -> ThesisRevision transaction
  -> legal lifecycle transition and attention allocation
  -> DBOS durable review wait or evidence-triggered wake-up
  -> material notification, digest, or silence
  -> OpenTelemetry and immutable audit record
```

## Layer ownership

### 1. Acquisition boundary

Inputs:

- QuickFlash curated event contract;
- official direct evidence bundles;
- allowlisted public market providers;
- expectation and research records;
- historical outcome records only in evaluation mode.

Existing assets to adapt:

- `CuratedFeedProvider` and `FeedProviderProtocol`;
- Hyperliquid and CCXT public adapters;
- adapter result, provenance and source-health concepts;
- one-shot collection and manifests.

Rules:

- acquisition never creates a thesis;
- provider health never becomes fact permission by itself;
- raw artifacts are hashed and retained or referenced;
- historical outcomes cannot enter live inference.

### 2. Evidence Gate

New deterministic service:

- validates source contract, identity and permissions;
- validates publication, effective, first-seen, retrieval and assessment times;
- blocks future evidence;
- verifies hashes and provenance;
- resolves or isolates entity identity;
- marks duplicate, correction, update or contradiction;
- emits typed gate results rather than silent error lists.

Port selectively from PR #16:

- evidence hash checks;
- origin and authority concepts;
- exact IDs and duplicate handling.

### 3. Event and candidate builder

New deterministic service:

- exact event grouping and immutable memberships;
- explicit event revisions;
- candidate relationship generation for fuzzy or semantic similarity;
- no automatic merge from similarity alone;
- prior thesis retrieval by entity, mechanism, exposure and event relation;
- point-in-time context assembly limited to the current candidate.

Port selectively:

- exact dedup-key grouping;
- source conflict record;
- expectation arithmetic;
- deterministic market calculations.

Do not port:

- live-origin activation;
- title-similarity merge authority;
- universal eleven-domain world model.

### 4. Semantic gateway

Two schema-bound calls:

- `ThesisSynthesisResult`;
- `RiskChallengeResult`.

Runtime:

- Pydantic models and Pydantic AI;
- provider and model configuration recorded;
- strict call, token, retry and tool limits;
- no free-form agent-to-agent conversation;
- no state transition or external action from the model.

### 5. Deterministic arbitration

New local service:

- applies L0 hard gates;
- validates required semantic fields and evidence references;
- preserves component-level disagreement;
- narrows unsupported claims;
- selects only allowlisted portfolio outcomes;
- uses evidence-status bands, not uncalibrated probabilities;
- emits a proposed transition and attention action.

### 6. Thesis transaction and lifecycle

Application database:

- SQLAlchemy models;
- Alembic migrations;
- append-only revisions plus current projections;
- optimistic versioning and idempotency keys;
- evidence-to-output provenance edges;
- review intent and resource usage persisted.

Transition validation:

- `python-statemachine` or a table-driven equivalent behind a local service;
- database is authoritative;
- every transition has expected prior state, reason and evidence references.

### 7. Durable runtime

DBOS owns:

- workflow step progress;
- durable wait until a review time;
- evidence-triggered continuation;
- retries and timeouts;
- cancel, resume and status;
- recovery from the last committed step.

DBOS does not own:

- thesis truth;
- claim permission;
- lifecycle policy;
- notification materiality.

### 8. Notification and owner surface

Outputs:

- immediate material alert;
- daily or weekly digest;
- no-output decision with audit record;
- governance exception.

Adapt existing operator vocabulary:

- doctor;
- status;
- inspect;
- compare;
- stop;
- resume;
- bundle.

The current workbench renderer and decision packet are not the canonical product object.

### 9. Validation path

A separate mode uses the same contracts and decision services with:

- frozen point-in-time evidence;
- future outcome isolation;
- EVENT_ONLY, PRICE_ONLY, ONE_SHOT, ALWAYS_NEUTRAL and FORCED_JUDGMENT baselines;
- adversarial and recovery injection;
- complete resource and variant accounting.

## Dependency direction

```text
Domain contracts
  <- acquisition adapters
  <- semantic gateway
  <- deterministic services
  <- workflow application
  <- operator CLI
```

Domain contracts do not import DBOS, provider SDKs or UI code. External frameworks stay behind adapters.

## First complete delivery boundary

The first complete slice supports one event family end to end:

- ingest approved evidence;
- resolve one event;
- create or abstain from one thesis;
- persist a revision;
- schedule one follow-up review;
- recover after restart;
- produce one material notification or silence;
- replay the same case without future leakage.

It does not include the eight strategy evaluators, universal world model, public UI, graph database, vector database, trading or publication.
