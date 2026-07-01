# Stage 3 WP-02 Pilot and Scale 002

**Issue:** #29  
**Draft PR:** #30  
**Branch:** `feat/stage3-wp02-historical-data-factory`  
**Reviewed Head:** `63f2783d6a82de42949bf2def0325d90e9ac7784`

Continue the same branch and Draft PR. Preserve valid infrastructure. Do not begin WP-03.

## P00 — Safe synchronization

Fetch all refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. Do not reset, clean, stash, rebase or create another branch.

## P01 — Close the remaining source-registry gap

Regenerate the feasibility report directly from the machine registry.

Required:

- one authoritative count of unique source IDs;
- separate source-to-family binding count;
- exact class distribution;
- no double-counting one source as two registry entries;
- exact agreement among registry YAML, code, tests, report, PR body and Issue receipt;
- bounded live probe evidence for every production adapter used by the pilot;
- observed HTTP status, response date range, parser result, request count and failure classification;
- unsupported historical-coverage or rate-limit claims removed.

A source may remain configured but cannot support the pilot until its bounded probe and parser evidence pass.

## P02 — Convert adapters into deterministic source-item parsers

Every pilot adapter must return one typed intake record per actual source item, not one record containing an entire page or response body.

Required adapter behavior:

- deterministic `intake_id` derived from stable source record identity and content hash; never use current time;
- explicit parser version and adapter version;
- correct historical-range filtering;
- real bounded pagination where the source supports it;
- original item URL, publication time and source-native identifier preserved;
- malformed item and page errors classified explicitly;
- source/network failure propagated to the acquisition runner, not silently converted to an empty successful page;
- no full article or oversized page body stored;
- maximum excerpt length enforced;
- duplicate source items produce the same deterministic intake ID.

Minimum production routes before pilot:

- regulatory: working historical SEC/CFTC or equivalent official parser;
- corporate: official filing or issuer primary-source parser;
- macro: at least one working official release parser;
- technology: working GitHub Advisory or NVD parser;
- market event: official listing, delisting, outage, maintenance or market notice parser separate from OHLCV;
- security: working official advisory parser;
- outcomes: primary and fallback OHLCV parsers.

Remove registry adapters that instantiate an abstract/unimplemented `fetch_page()` path.

## P03 — Make acquisition output and checkpoint one recoverable state machine

Integrate durable output storage with `CheckpointedAcquisition`; a disconnected `AtomicCheckpointWriter` class is insufficient.

Required semantics:

- `record_limit` and `max_record_budget` are both hard ceilings;
- page results are sliced to the smaller remaining ceiling;
- committed intake records are deduplicated by deterministic intake ID;
- output is durably committed before checkpoint advancement;
- crash after output commit but before checkpoint commit resumes without duplicate records;
- crash before output commit leaves checkpoint unchanged;
- checkpoint records terminal state, last committed token and committed output hash/count;
- completed resume returns zero new records even when completion occurred through source exhaustion before `record_limit`;
- repeated or cyclic page tokens are detected and fail safely;
- incompatible resume parameters remain rejected;
- partial and failed runs preserve exact last committed data and error.

Required host-observable tests:

- ceiling smaller than one fetched page;
- `max_record_budget < record_limit`;
- source-exhausted completed resume;
- output-before-checkpoint injected failure;
- checkpoint-write injected failure;
- duplicate page replay;
- cyclic page token;
- process-style reopen and resume from file-backed outputs.

## P04 — Finish the real corpus auditor

Audit against the explicit `assessment_time`, not event time.

Required behavior:

- missing required artifact is a failure;
- missing outcome file is a failure when accepted cases exist;
- future leakage traverses actual evidence references and uses each evidence availability time against the case assessment cutoff;
- duplicate, cross-split identity, cross-split chain and BLIND contamination diagnostics include exact case, identity, chain and split IDs;
- outcome validation checks every canonical window, provider, instrument and case reference;
- 24h outcome coverage >=95% is part of `all_gates_pass`;
- audit-path coverage must traverse source -> evidence -> case -> outcome and equal 100%;
- a missing second clean rebuild is a failure;
- artifact hash comparison includes the complete build manifest;
- every failed gate returns exact violating IDs and reasons, not only counts;
- audit complexity is suitable for 1,500+ cases using grouped indexes rather than all-pairs scanning where practical.

Add mutation tests for every gate.

## P05 — Complete canonical storage and SQLite roundtrip

Implement and test the complete artifact set:

```text
data/historical_v1/
  source_registry.yaml
  cases.jsonl or deterministic shards
  evidence.jsonl or deterministic shards
  correction_chains.jsonl
  market_bars.jsonl or deterministic shards
  outcome_windows.jsonl or deterministic shards
  split_manifest.json
  build_manifest.json
  quality_report.json
  rejected_records.jsonl
  corpus_report.md
```

Required:

- stable sorted-key JSONL and deterministic record order;
- explicit shard manifest and hashes;
- no volatile runtime timestamp inside deterministic corpus hashes;
- SQLite materialization from canonical files;
- reverse export produces equivalent canonical records and hashes;
- no credentials, private paths or full copyrighted bodies.

## P06 — Run the real 120-case pilot

Use bounded public reads only. Build at least 120 QUALIFIED cases, at least 20 per family.

Each accepted pilot case requires:

- permitted source and exact URL;
- stable evidence and event identity;
- publication, first-seen, retrieval and assessment times;
- explicit authority and fact permission;
- asset or benchmark mapping;
- regime assignment and rule version;
- separate 1h, 6h and 24h outcome records;
- 3d and 7d outcomes or explicit missing reason;
- source-to-outcome provenance path;
- qualification decision derived by code.

Pilot gates:

- all six families >=20;
- no synthetic, cloned, timestamp-shifted or repeated-summary cases;
- future leakage 0;
- duplicate accepted IDs 0;
- cross-split event identities 0;
- cross-split chains 0;
- BLIND contamination 0;
- point-in-time and permission completeness 100%;
- audit-path coverage 100%;
- 24h outcome coverage >=95%;
- two clean rebuilds have identical artifact and root hashes;
- exact source failure and rejection report.

If the pilot cannot pass after documented fallback attempts, stop honestly with `WP02_SOURCE_FEASIBILITY_BLOCKED` or `WP02_DATA_QUALITY_BLOCKED`. Do not fabricate or scale.

## P07 — Scale to at least 1,500 QUALIFIED cases

Scale only after P06 passes.

Required final corpus:

- qualified cases >=1,500;
- each family >=150;
- no family >35%;
- bull, bear, ranging, high_volatility, crisis and recovery represented;
- unknown regime <=10%;
- chronological frozen BUILD / DEVELOPMENT / BLIND allocation;
- event identity and correction chain remain in one split;
- BLIND cases, identities, chains and outcomes excluded from tuning;
- point-in-time and permission completeness 100%;
- future leakage 0;
- duplicate accepted IDs 0;
- outcome structural violations 0;
- 24h outcome coverage >=95%;
- audit-path coverage 100%;
- two clean full rebuilds produce identical file and root hashes.

Do not meet the target using synthetic cases, cloned source records, repeated descriptions of one event or timestamp shifting.

## P08 — Complete reports

Create and synchronize:

- `docs/stage3/WP02_SOURCE_FEASIBILITY.md`;
- `docs/stage3/WP02_DATA_FACTORY_REPORT.md`;
- `docs/stage3/WP02_CORPUS_AUDIT.md`;
- `docs/stage3/WP02_REJECTION_REPORT.md`;
- PR #30 body;
- Issue #29 receipt.

All counts and distributions must be generated from canonical artifacts. Separate configuration, observed live evidence, assumptions, failures, quarantines and unsupported claims.

## P09 — Final tests and receipt

Run:

- focused data-factory tests;
- all cognition_v2 regressions;
- Stage 2 regressions;
- full repository suite;
- same full command on current `origin/main` in a safe temporary worktree for any claimed pre-existing failures;
- `git diff --check`.

Push only the existing branch and update only Draft PR #30 and Issue #29. Do not self-merge.

Stop with:

```text
terminal_state: <WP02_ACCEPTED_CANDIDATE|WP02_SOURCE_FEASIBILITY_BLOCKED|WP02_DATA_QUALITY_BLOCKED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 29
pr: 30
branch: feat/stage3-wp02-historical-data-factory
start_head: 63f2783d6a82de42949bf2def0325d90e9ac7784
final_remote_head: <exact 40-char SHA>
registry_source_ids: <integer>
source_family_bindings: <integer>
registry_report_counts_match: <pass/fail>
live_probe_results: <exact mapping>
production_parsers: <exact list>
deterministic_intake_ids: <pass/fail>
completed_resume_new_records: 0
record_limit_hard_ceiling: <pass/fail>
max_budget_hard_ceiling: <pass/fail>
atomic_output_checkpoint_recovery: <pass/fail>
placeholder_or_assumed_audit_values: 0
pilot_qualified_cases: <integer>
pilot_family_distribution: <exact mapping>
pilot_24h_outcome_coverage: <percent>
pilot_audit_path_coverage: <percent>
pilot_rebuild_one_hash: <sha256>
pilot_rebuild_two_hash: <sha256>
pilot_gate: <pass/fail>
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
paid_api_calls: 0
real_model_calls: 0
postgres_installed_or_started: no
background_processes_created: 0
blockers: <none-or-list>
```

`WP02_ACCEPTED_CANDIDATE` is valid only when the 120-case pilot and the final 1,500-case corpus both pass every mandatory gate. Do not begin WP-03.
