# Stage 3 WP-02 Execution Contract

**Executor:** Reasonix  
**Mode:** Auto  
**Goal mode:** disabled  
**Issue:** #29  
**Branch:** `feat/stage3-wp02-historical-data-factory`  
**Canonical fingerprint:** `86f23066366b5c38657cc4b8447827f8cb273ab8d0a99845b562ce904c9aa989`

## Result

Build a finite, checkpointed historical evidence and point-in-time data factory and produce at least 1,500 QUALIFIED cases across six event families and multiple market regimes.

This is a data-engineering package. Do not run semantic cognition, tune prompts, start WP-03 or create live/public effects.

## Read first

1. `PROJECT_MAINLINE.md`
2. `project/CANONICAL_STATE.yaml`
3. `project/STAGE3_WP01_EXIT.md`
4. `project/WP02_HISTORICAL_DATA_FACTORY_SPEC.md`
5. `project/COMPLETE_ENGINEERING_DELIVERY_TRAIN.md`
6. `project/INTEGRATION_POLICY.md`
7. `project/RISK_ABSTENTION_CONSTITUTION.md`
8. `project/LONGITUDINAL_VALIDATION_PLAN.md`
9. Issue #29

## D00 — Safe synchronization

Work only from `/Users/zhuo/Desktop/市场信号/crypto-event-intelligence`.

Inspect repository root, remote, branch, status and remote SHAs. Do not reset, clean, stash, rebase or overwrite owner files. Stop with `LOCAL_STATE_REVIEW_REQUIRED` for tracked local changes or unexplained untracked product paths.

Check out and fast-forward only:

`feat/stage3-wp02-historical-data-factory`

Verify canonical fingerprint:

`86f23066366b5c38657cc4b8447827f8cb273ab8d0a99845b562ce904c9aa989`

## D01 — Source feasibility and permission register

Before large acquisition, build `docs/stage3/WP02_SOURCE_FEASIBILITY.md` and a machine-readable source registry.

Classify each candidate source as:

- DISCOVERY_ONLY;
- QUALIFYING_EVIDENCE;
- MARKET_OUTCOME;
- REJECTED.

Every accepted source entry requires:

- stable source ID and source class;
- authority and fact permission;
- public read-only access method;
- historical coverage;
- parser version;
- rate limit and finite retry policy;
- terms/permission note;
- whether short excerpts may be stored;
- source-health and failure evidence;
- fallback source when available.

Preferred sources are official regulator/government releases, official company/protocol/exchange notices, public security advisories, public macro releases and public market-data endpoints.

Discovery indexes or news aggregators may identify candidate events, but DISCOVERY_ONLY records cannot independently qualify a case. Qualification requires permitted evidence.

Forbidden:

- paid APIs;
- private credentials;
- login or paywall bypass;
- robots/access-control circumvention;
- full copyrighted article storage;
- invented historical timestamps or source authority.

Store no excerpt longer than 500 Unicode characters. Prefer normalized factual records and source hashes.

Feasibility pilot:

- at least 20 candidate cases per family;
- at least two source classes per family where feasible;
- point-in-time fields and outcomes proven end-to-end;
- pilot quality report before scaling.

If the pilot cannot support the final target after documented fallback attempts, stop with `WP02_SOURCE_FEASIBILITY_BLOCKED`; do not fabricate cases.

## D02 — Data-factory package boundaries

Create production modules under:

```text
market_radar/cognition_v2/data_factory/
  contracts.py
  source_registry.py
  acquisition.py
  checkpoints.py
  normalization.py
  provenance.py
  identity.py
  regimes.py
  outcomes.py
  splits.py
  storage.py
  audit.py
  cli.py
```

Required direction:

- reuse canonical WP-01 domain and persistence contracts;
- no dependency from domain into data_factory;
- acquisition adapters return typed raw/intake records;
- normalization and audit remain deterministic;
- outcome collection is separate from evidence construction;
- operator commands invoke application services rather than embedding business rules.

Add import-boundary tests.

## D03 — Canonical data contracts

Add or extend typed contracts for:

- SourceRegistryEntry;
- AcquisitionRun;
- AcquisitionCheckpoint;
- RawIntakeRecord;
- NormalizedEvidenceRecord;
- CaseQualificationDecision;
- EventIdentityAssignment;
- CorrectionChainAssignment;
- AssetMapping;
- MarketRegimeAssignment;
- OutcomeObservation;
- FrozenSplitAssignment;
- CorpusBuildManifest;
- CorpusQualityReport;
- RejectedRecord.

Every record needs deterministic ID, schema version, rule/parser version, created/retrieved time and source provenance.

Allowed qualification states:

- QUALIFIED;
- INCOMPLETE;
- DUPLICATE;
- LEAKED;
- UNAUTHORIZED_SOURCE;
- IDENTITY_UNRESOLVED;
- OUTCOME_UNAVAILABLE;
- QUARANTINED.

Only QUALIFIED records count toward 1,500.

## D04 — Finite checkpointed acquisition

Implement finite acquisition commands with explicit:

- source IDs;
- start and end time;
- record limit;
- page/batch size;
- request timeout;
- retry limit and backoff;
- checkpoint path;
- output path;
- status and summary;
- stop behavior.

Requirements:

- no daemon, cron, login item or persistent background process;
- interruption preserves the last committed checkpoint;
- resume does not duplicate accepted intake records;
- checkpoint request fingerprint rejects incompatible resume parameters;
- each run has a maximum request and record budget;
- HTTP cache is optional but must be content-addressed and auditable;
- no source write operations.

Test success, retry, permanent failure, interruption, resume, incompatible resume and duplicate-page behavior with deterministic fixtures.

## D05 — Normalization, point-in-time authority and provenance

Normalize source records into canonical evidence with explicit:

- source ID and URL;
- authority and fact permission;
- publication_time;
- effective_time when applicable;
- first_seen_at;
- retrieval_time;
- assessment_time;
- parser and schema version;
- normalized fact or short excerpt;
- content hash;
- provenance edges.

Point-in-time rule:

```text
availability_time = max(first_seen_at, retrieval_time)
```

Publication or effective time alone never makes later-retrieved information available earlier.

Requirements:

- timezone-aware UTC fields;
- deterministic normalization independent of dictionary ordering;
- retractions/corrections first seen later remain unavailable to earlier assessments;
- exact blocked evidence IDs and reasons;
- no silent discard;
- no invented times.

## D06 — Event identity, duplicates and correction chains

Implement deterministic identity assignment using permitted fields and versioned rules.

Separate:

- exact duplicate;
- same event identity;
- related but distinct event;
- correction;
- retraction;
- contradiction;
- supersession.

Requirements:

- accepted case IDs unique;
- exact duplicate accepted cases: 0;
- correction-chain root and members explicit;
- conflicting chain assignments quarantined;
- identity uncertainty ends as IDENTITY_UNRESOLVED rather than forced grouping;
- all identity and chain decisions have rule/version and evidence references;
- no event identity or chain crosses frozen splits.

## D07 — Asset mapping and market-regime labeling

Map each qualified case to:

- one primary affected asset or benchmark;
- optional additional affected assets;
- canonical instrument identifiers;
- mapping rule/version and evidence;
- benchmark asset when direct asset data is unavailable.

Create deterministic regime labels using stored market observations and versioned rules. Required regimes:

- bull;
- bear;
- ranging;
- high_volatility;
- crisis;
- recovery;
- unknown during intake only.

Report exact regime distribution. Unknown may not exceed 10% of accepted cases unless an explicit accepted feasibility decision exists.

## D08 — Outcome acquisition and separation

Use approved public market-data endpoints or accepted existing read-only adapters.

Create separate outcome observations for:

- 1h;
- 6h;
- 24h;
- 3d;
- 7d.

Each outcome requires provider, instrument, interval, open/close times, retrieval time, prices, high, low, volume when available, return, direction, content hash and missing-data reason.

Requirements:

- outcome records stored separately from evidence and cases;
- outcome fields excluded from input manifest hashes;
- timestamps and windows structurally valid;
- prices finite and high not below low;
- missing data explicit, never silently imputed;
- benchmark 24h outcome coverage target at least 95%;
- exact coverage reported by family, regime, asset and window.

## D09 — Frozen split allocator

Allocate by correction-chain root event time with immutable boundary/version records.

Target distribution:

- BUILD approximately 60%;
- DEVELOPMENT approximately 20%;
- BLIND approximately 20%.

Rules:

- one case appears once;
- event identities remain within one split;
- correction chains remain within one split;
- BLIND cases, identities, chains and outcomes never enter tuning input;
- a newer case cannot move an already frozen BLIND case;
- split assignment is deterministic from the same corpus and boundary version;
- boundary changes require a new dataset version, never silent mutation.

## D10 — Canonical artifacts and storage

Create:

```text
data/historical_v1/
  source_registry.yaml
  cases.jsonl
  evidence.jsonl
  correction_chains.jsonl
  market_bars.jsonl
  outcome_windows.jsonl
  split_manifest.json
  build_manifest.json
  corpus_report.md
  quality_report.json
  rejected_records.jsonl
```

Keep every tracked file below GitHub limits. Shard by family/year only when needed and record shards in `build_manifest.json`.

Canonical JSONL rules:

- UTF-8;
- one sorted-key JSON object per line;
- stable newline behavior;
- deterministic record ordering;
- no volatile current timestamp in content hashes;
- no secret, credential, private absolute path or full article body.

Provide SQLite materialization from canonical artifacts and round-trip verification back to equivalent canonical records.

## D11 — Pilot, scale and corpus build

### Pilot gate

Build at least 120 qualified cases, at least 20 per event family.

Before scaling, prove:

- point-in-time completeness;
- source permission completeness;
- outcome separation;
- duplicate and identity behavior;
- correction-chain behavior;
- split allocation;
- deterministic rebuild;
- acceptable source failure rate.

### Scale gate

Scale to at least 1,500 QUALIFIED cases for 2021-01-01 through 2026-06-30 UTC.

Mandatory distribution:

- all six families;
- no family below 150 accepted cases unless source-feasibility report proves the constraint and terminal state is not ACCEPTED;
- no family above 35% of the accepted corpus;
- all required regimes represented;
- unknown regime at most 10%;
- exact year, family, regime, source and asset distributions reported.

Do not meet counts by cloning, timestamp shifting, synthetic duplication or repeated summaries of one event.

## D12 — Quality audit and deterministic rebuild

Run all mandatory gates:

- accepted cases >= 1,500;
- critical point-in-time fields 100%;
- authority and permission 100%;
- accepted future leakage 0;
- cross-split event identities 0;
- cross-split correction chains 0;
- BLIND tuning contamination 0;
- duplicate accepted case IDs 0;
- structural outcome violations 0;
- source-to-evidence-to-case-to-outcome audit coverage 100%;
- rejected records include exact reason and source;
- deterministic rebuild hashes match twice.

Perform two clean rebuilds into separate temporary directories from the same canonical intake/snapshot inputs. Compare every canonical artifact hash and corpus root hash.

Add mutation tests proving the audit catches:

- future evidence;
- duplicate case;
- cross-split identity;
- cross-split chain;
- BLIND contamination;
- missing permission;
- outcome included in input hash;
- invalid outcome window;
- nondeterministic ordering;
- altered source content.

## D13 — Tests, regression and reports

Required reports:

- `docs/stage3/WP02_SOURCE_FEASIBILITY.md`;
- `docs/stage3/WP02_DATA_FACTORY_REPORT.md`;
- `docs/stage3/WP02_CORPUS_AUDIT.md`;
- `docs/stage3/WP02_REJECTION_REPORT.md`.

Reports must separate:

- executed evidence;
- source feasibility;
- corpus statistics;
- qualification and rejection reasons;
- point-in-time and split guarantees;
- outcome coverage;
- deterministic rebuild evidence;
- known limits;
- unsupported claims;
- exact commands and results.

Run:

- focused data-factory tests;
- all `tests/cognition_v2/` regressions;
- Stage 2 regressions;
- full repository suite;
- same full-suite command on current `origin/main` in a safe temporary worktree for claimed pre-existing blockers;
- `git diff --check`.

## D14 — Git, Draft PR and terminal receipt

Use focused commits. Before each commit inspect `git diff --check`, diff stat and full diff.

Push only `feat/stage3-wp02-historical-data-factory`.

After the first remote implementation commit, create or update one Draft PR to `main` linked to Issue #29. Do not create another branch or PR. Do not self-merge.

After the final push, obtain the exact remote SHA and update the Draft PR and Issue #29 receipt. Do not modify tracked files afterward.

Stop with:

```text
terminal_state: <WP02_ACCEPTED_CANDIDATE|WP02_SOURCE_FEASIBILITY_BLOCKED|WP02_DATA_QUALITY_BLOCKED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 29
branch: feat/stage3-wp02-historical-data-factory
base: main
start_head: <exact sha>
final_remote_head: <exact 40-char sha-or-unchanged>
draft_pr: <number-or-none>
source_registry_entries: <integer>
qualifying_source_classes: <integer>
public_read_only_sources_only: <pass/fail>
paid_api_calls: 0
real_model_calls: 0
pilot_qualified_cases: <integer>
total_intake_records: <integer>
qualified_cases: <integer>
rejected_or_quarantined_cases: <integer>
family_distribution: <exact mapping>
regime_distribution: <exact mapping>
year_distribution: <exact mapping>
source_distribution: <exact mapping>
critical_time_completeness: <percent>
authority_permission_completeness: <percent>
future_leakage_violations: <integer>
duplicate_accepted_case_ids: <integer>
cross_split_event_identities: <integer>
cross_split_correction_chains: <integer>
blind_tuning_contamination: <integer>
outcome_structural_violations: <integer>
benchmark_24h_outcome_coverage: <percent>
audit_path_coverage: <percent>
rebuild_one_root_hash: <sha256>
rebuild_two_root_hash: <sha256>
deterministic_rebuild: <pass/fail>
canonical_artifact_size_bytes: <integer>
focused_tests: <exact result>
cognition_v2_regression: <exact result>
stage2_regression: <exact result>
full_suite_branch: <exact result>
full_suite_main_comparison: <exact result>
git_diff_check: <pass/fail>
old_cognition_core_modified: no
pr_16_draft_unmerged: <pass/fail>
postgres_installed_or_started: no
background_processes_created: 0
reports:
  - docs/stage3/WP02_SOURCE_FEASIBILITY.md
  - docs/stage3/WP02_DATA_FACTORY_REPORT.md
  - docs/stage3/WP02_CORPUS_AUDIT.md
  - docs/stage3/WP02_REJECTION_REPORT.md
blockers: <none-or-list>
```

Do not merge and do not begin WP-03. GPT independently reviews and directly integrates only the accepted exact remote Head.
