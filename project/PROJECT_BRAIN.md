# PROJECT_BRAIN

## Compilation identity

- Framework stage: 5
- Business repository: `zhuo74451-art/crypto-event-intelligence`
- Authoritative planning base: `feat/overnight-lane-d-validation-walkforward-calibration-v1` at `a6b5baf1e0d5060b5375ce12c68e04ee547efb88`
- Planning branch: `planning/stage5-a-d-lane-e-unattended-v1`
- Compilation mode: finite conditional unattended task graph
- Execution started by this compilation: no
- Runtime compatibility: blocked

## Product identity

**Crypto Market Cognition & Signal OS** is an AI-first crypto market research and intelligence system. It combines a multi-domain market world model, point-in-time evidence, source health, research claims and conflicts, strategy distillation, historical and shadow validation, arbitration, and an explicit `INSUFFICIENT_EVIDENCE` state.

The product is not an auto-trading system, wallet, order executor, public SaaS release, or production publishing service.

## Authoritative facts

| ID | Fact | Evidence |
|---|---|---|
| FACT-001 | `main` is `fc9b76f8a3cfc84bc384b145bd93dda41006e68f`; the current cognition branch is 31 commits ahead and contains the accepted A-D pilot chain. | Git compare, 2026-06-24 |
| FACT-002 | Lane A is an accepted official-release evidence pilot at `9aaabc82f34141e6797d3f92b773d5c463ad99b8`; it contains 12 release events, 12 observations, and 8 source snapshots. | `docs/execution/lane_a/INTEGRATION_MANIFEST.yaml` |
| FACT-003 | Lane B is an accepted event-alignment pilot at `ec8952b600ffceebeabcb50ac11e3b182e76c5e2`, but its legacy integration manifest still contains stale producer wording and placeholders. | Lane B state and manifest |
| FACT-004 | Lane C is an accepted small-sample replay pilot at `72984d8b0fe17dc188239c3c050e082c180853b4`; it locks Lane A and Lane B and forbids probability, calibration, and causal claims. | Lane C state and manifest |
| FACT-005 | Lane D is formally complete at `a6b5baf1e0d5060b5375ce12c68e04ee547efb88` with fail-closed validation, producer byte-hash checks, finite fault injection, manifest-hash checks, and 71 reported tests passing. | Lane D final branch evidence |
| FACT-006 | Lane D permits pilot consumption but does not support calibration, statistical significance, full walk-forward, drift inference, or causal inference. | Lane D execution state and V3 manifest |
| FACT-007 | The old Lane E candidate branch is `integration/overnight-intelligence-v1` at `8dfa3231826707df188be7152c34f00062b3606e`. Its state is stale, `integrated_producers` is empty, and its default route assumes unavailable producers. | Lane E state and manifest |
| FACT-008 | Existing Lane E research contracts, evidence graph, conflict engine, dossier code, and integration engine are candidates only; none receives automatic retention authority from old tests or reports. | Mainline contract |
| FACT-009 | Generic capability engineering follows open-source-first adoption; domain semantics remain project-specific. | Approved project decision |
| FACT-010 | Current approved execution horizon is finite: cross-lane compatibility and reuse audit, bounded Lane E materialization, real A-D producer locking, research artifact compilation, independent validation, and final seal. | Owner-approved route |
| FACT-011 | Recurring services, paid interfaces, production publishing, credentials, funds, deletion, system services, and trading remain outside the approved horizon. | Mainline and Owner boundary |
| FACT-012 | HumanThink `main` does not contain the Autodev runtime. Draft PR #3 exposes `ht-autodev run/resume/status/...`, not the required stable `humanthink-autodev activate` interface. | HumanThink PR #3 and CLI source |
| FACT-013 | The HumanThink alpha graph is an internal execution loop; it does not implement the declarative Stage-5 task graph, GPT gate dispatcher, Owner gate dispatcher, planning-ref loader, or current-node-only Reasonix CLI activation contract. | HumanThink orchestration source |

## Claims requiring execution evidence

| ID | Claim | Required proof |
|---|---|---|
| CLAIM-001 | Selected old Lane E modules can be safely adapted to current mainline semantics. | WP-001 compatibility report plus GATE-COMPAT decision |
| CLAIM-002 | A-D artifacts can be locked and consumed without V2/V3 or stale-SHA mixing. | Producer-lock audit and byte hashes |
| CLAIM-003 | Real A-D artifacts can produce Research Claims, Evidence Graph, Conflict Sets, and Dossiers without sample fallback. | One-shot deterministic integration run |
| CLAIM-004 | The integrated path is reproducible from a clean checkout. | WP-008 and WP-010 detached validation evidence |
| CLAIM-005 | A pure unattended run can be activated from Reasonix Desktop. | A merged and validated HumanThink activation runtime; currently unproven |

## Active tensions

- **TENSION-001:** Mainline says all old modules are candidates, while historical Lane reports describe completed systems.
- **TENSION-002:** Lane B state says the Lane A producer was relocked, while its old manifest contains stale producer metadata and placeholders.
- **TENSION-003:** Lane E contains useful research-domain code but its producer state is stale and its integration route is not evidence-backed.
- **TENSION-004:** The project has a fully compiled unattended graph, while the required background activation runtime is not yet implemented.
- **TENSION-005:** The mainline immediate boundary is one-shot and read-only; any recurring acquisition or production publishing would exceed approval.

## Locked decisions

| ID | Decision |
|---|---|
| DEC-001 | Continue the full Crypto Market Cognition & Signal OS; do not reduce it to a new MVP and do not restart. |
| DEC-002 | Preserve accepted A-D pilot evidence and exact final refs. |
| DEC-003 | Audit before adaptation. Existing code is classified `RETAIN`, `ADAPT`, `QUARANTINE`, or `DELETE`. |
| DEC-004 | Generic capabilities use `ADOPT`, `ADAPT`, `BUILD`, or `DEFER`; custom build requires a documented gap proof. |
| DEC-005 | Domain semantics remain custom: point-in-time evidence, event state, expectation gap, transmission, arbitration, abstention, validation protocol, research claims, conflicts, and knowledge decay. |
| DEC-006 | Reasonix Desktop is activation-only. Reasonix CLI receives only the active node and hot context. |
| DEC-007 | Ordinary retries, conditional fixes, audit handling, no-change closure, and final validation are automatic. |
| DEC-008 | Owner review is exception-only and limited to product identity, value boundary, expanded approval, irreversible or external effects, credentials, funds, deletion, production, or material lock-in. |
| DEC-009 | No execution begins in this compilation turn. |
| DEC-010 | Runtime readiness must remain blocked until the stable activation interface and task-graph controller are real and validated. |

## Open-source reuse policy

### Immediate audit shortlist

- Pydantic for contracts and typed boundaries
- Pandera for dataframe validation where dataframe use is justified
- DuckDB and Parquet for local analytical storage
- pytest and Hypothesis for deterministic and generative validation
- SciPy, statsmodels, and scikit-learn for bounded statistical utilities
- Trafilatura and WARC tooling for evidence extraction and preservation
- RSSHub, Crawl4AI, and changedetection.io only behind replaceable acquisition adapters
- CCXT only behind point-in-time and provider-quality contracts

### Deferred unless scale or evidence demands

- OpenLineage and Marquez
- Neo4j or another graph database
- Prefect, Dagster, Airflow, or Temporal
- Vector databases
- LangChain or LlamaIndex as a total application framework
- Custom multi-agent platform work
- Production schedulers or background services

## Accepted execution outcomes

| ID | Observable result |
|---|---|
| OUT-001 | A complete, evidence-linked disposition and reuse matrix for Lane A-D and the old Lane E candidate surface. |
| OUT-002 | A canonical producer-lock layer that pins exact A-D refs, artifact hashes, record counts, and supported claim boundaries. |
| OUT-003 | A one-shot Lane E path that consumes real A-D artifacts and produces research artifacts without sample fallback. |
| OUT-004 | Clean-checkout reproducibility and falsification evidence. |
| OUT-005 | A final integration seal that states supported and unsupported claims without inflation. |

## Constraints

- CON-001: No daemon, cron, scheduler, systemd registration, or persistent background project service.
- CON-002: No paid interface or new metered dependency.
- CON-003: No production Telegram, external publication, or order execution.
- CON-004: No credentials, funds, wallet, secret rotation, or irreversible action.
- CON-005: No silent scope expansion or product identity change.
- CON-006: No unsupported probability, significance, full walk-forward, drift, causal, or profitability claim.
- CON-007: No executor decomposition, package reordering, or future-pool selection.
- CON-008: No direct push, force-push, merge, or release by Reasonix CLI.
- CON-009: Every write package has finite attempts, finite time, deterministic verification, and a recoverable checkpoint.
- CON-010: Every terminal state stops.

## Risks

| ID | Priority | Risk | Control |
|---|---|---|---|
| RISK-001 | P0 | Stale Lane E locks mix old or missing producers with current A-D artifacts. | Exact ref and artifact hash lock before integration. |
| RISK-002 | P0 | Sample or hardcoded data is presented as real integration. | Source-lineage assertions and sample-fallback prohibition. |
| RISK-003 | P0 | Unsupported statistical or causal claims leak into research artifacts. | Fail-closed claim-boundary audit. |
| RISK-004 | P1 | Old Lane B manifest conflicts with its later relock state. | WP-001 conflict inventory and bounded repair. |
| RISK-005 | P1 | Old Lane E code imports too broad a surface. | Gate-generated exact file allowlist. |
| RISK-006 | P1 | Generic infrastructure is rebuilt instead of adopted. | Reuse matrix and gap-proof requirement. |
| RISK-007 | P1 | A clean validation passes against a different ref than the implementation. | Exact-head detached validation and post-seal verification. |
| RISK-008 | P0 | A non-existent activation command is presented as runnable. | `runtime_compatibility: blocked` and no launch command. |

## No-go routes

- NOGO-001: Directly merge A, B, C, D, and old Lane E without compatibility evidence.
- NOGO-002: Treat old Lane E sample outputs as current product truth.
- NOGO-003: Add recurring acquisition, production publishing, or trading.
- NOGO-004: Introduce a graph database, orchestration platform, vector database, or agent framework without a present gap proof.
- NOGO-005: Ask the Owner to advance ordinary packages manually.
- NOGO-006: Emit a Reasonix Desktop launch envelope while runtime compatibility is blocked.

## Current stage

Stage 5 compilation is complete when all project execution assets are tracked, the finite graph passes static audit, and runtime compatibility is honestly recorded. Execution remains stopped until a future compatible runtime and a separate activation instruction exist.
