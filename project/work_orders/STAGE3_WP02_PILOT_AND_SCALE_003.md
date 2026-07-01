# Stage 3 WP-02 Pilot and Scale 003

**Issue:** #29  
**Draft PR:** #30  
**Branch:** `feat/stage3-wp02-historical-data-factory`  
**Reviewed Head:** `8435ccd06866505f707fc0f0ada0976679d517fd`

Continue the same branch and Draft PR. Preserve valid P01-P03 work. Do not begin WP-03.

## Q00 — Safe synchronization

Fetch all refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. Do not reset, clean, stash, rebase or create another branch.

## Q01 — Prove source feasibility with bounded live probes

The report currently lists every production adapter as `pending bounded probe` while concluding feasibility is confirmed. Replace configuration claims with observed evidence.

For every adapter used by the pilot, run a finite bounded probe and record:

- source ID and exact endpoint;
- UTC start/end range;
- request count and record limit;
- HTTP status and failure classification;
- parser version and adapter version;
- number of source items parsed;
- earliest and latest parsed publication times;
- malformed-item count;
- whether the result is sufficient for pilot qualification;
- exact fallback used when the primary source fails.

Do not state broad historical coverage, rate-limit behavior or family feasibility unless the probe demonstrates it. Sources that cannot pass remain configured but cannot count toward pilot feasibility.

The report, registry, PR body and Issue receipt must agree on 11 source IDs, 11 primary family bindings and the exact source-class counts.

## Q02 — Repair persisted resume semantics

`CheckpointedAcquisition` must never truncate committed output on resume.

Required behavior:

- load the existing durable output before any write;
- rebuild the committed intake-ID set from persisted output;
- never call `write_output(run_id, [])` over an existing completed or partial run;
- checkpoint persists terminal state, completion reason, last committed token, committed output count and committed output hash;
- completed resume returns zero new records and performs zero source requests;
- source-exhausted completion with `last_page_token=None` remains terminal;
- resumed partial runs append only unseen deterministic intake IDs;
- if output and checkpoint disagree, fail with an explicit recovery error rather than silently continuing;
- output commit precedes checkpoint commit;
- checkpoint-write failure leaves committed output recoverable and replay-safe;
- output-write failure leaves checkpoint unchanged;
- process-style reopen preserves all committed records and dedupe state.

Required tests:

- completed resume after source exhaustion;
- completed resume after hitting record limit;
- partial resume after engine/process-style reopen;
- output survives checkpoint-write failure;
- checkpoint does not advance after output-write failure;
- stale checkpoint vs newer output mismatch;
- newer checkpoint vs missing/truncated output mismatch;
- duplicate source page after reopen;
- cyclic page token after reopen;
- `max_record_budget < record_limit` hard ceiling.

## Q03 — Finish the production auditor

Use explicit case `assessment_time`, not event time, as the cutoff.

Required:

- traverse source -> evidence -> case -> outcome references;
- missing required artifacts fail;
- missing outcome artifacts fail when accepted cases exist;
- future evidence reports exact evidence and case IDs;
- duplicate, cross-split identity, cross-split chain and BLIND contamination diagnostics include exact IDs and splits;
- validate all canonical outcome windows, provider, instrument and case references;
- 24h outcome coverage >=95% is part of the overall pass gate;
- audit-path coverage must equal 100% and is part of the overall pass gate;
- missing second rebuild fails;
- complete build-manifest and artifact hashes are compared;
- every failed gate returns exact reasons, not only counts;
- grouped indexes avoid unnecessary all-pairs scans for the 1,500-case corpus.

Add mutation tests for every mandatory gate.

## Q04 — Complete canonical storage and SQLite roundtrip

Produce and test the full canonical artifact set:

- source registry;
- evidence;
- cases;
- correction chains;
- market bars;
- outcome windows;
- split manifest;
- build manifest;
- quality report;
- rejected records;
- corpus report.

Canonical requirements:

- deterministic sorted-key JSONL;
- deterministic record and shard ordering;
- every shard listed with SHA-256;
- no volatile runtime time in corpus hashes;
- no credential, private path or full article body;
- SQLite materialization from canonical files;
- reverse export produces equivalent records and identical canonical hashes.

## Q05 — Run the real 120-case pilot

Use only bounded public reads from adapters that passed Q01.

Build at least 120 QUALIFIED cases, at least 20 in each family. Every accepted case must have:

- permitted public source and exact URL;
- stable evidence and event identity;
- publication, first-seen, retrieval and assessment times;
- explicit authority and fact permission;
- asset or benchmark mapping;
- versioned regime assignment;
- separate 1h, 6h and 24h outcomes;
- 3d and 7d outcomes or explicit missing reason;
- source-to-evidence-to-case-to-outcome provenance;
- qualification decision derived by code.

Pilot gates:

- each family >=20;
- no synthetic, cloned, timestamp-shifted or repeated-summary cases;
- point-in-time and permission completeness 100%;
- future leakage 0;
- duplicate accepted IDs 0;
- cross-split identities and chains 0;
- BLIND contamination 0;
- 24h outcome coverage >=95%;
- audit-path coverage 100%;
- two clean rebuilds have identical file and root hashes.

If the pilot cannot pass after documented fallback attempts, stop with `WP02_SOURCE_FEASIBILITY_BLOCKED` or `WP02_DATA_QUALITY_BLOCKED`. Do not fabricate or scale.

## Q06 — Scale to at least 1,500 QUALIFIED cases

Scale only after Q05 passes.

Required:

- >=1,500 qualified cases;
- every family >=150;
- no family >35%;
- bull, bear, ranging, high_volatility, crisis and recovery represented;
- unknown regime <=10%;
- frozen chronological BUILD / DEVELOPMENT / BLIND splits;
- identity and correction-chain split integrity;
- zero BLIND tuning contamination;
- point-in-time and permission completeness 100%;
- future leakage 0;
- duplicate accepted IDs 0;
- outcome structural violations 0;
- 24h outcome coverage >=95%;
- audit-path coverage 100%;
- two clean full rebuilds produce identical artifact and root hashes.

Do not satisfy counts using synthetic cases, cloned records, repeated descriptions or timestamp shifting.

## Q07 — Reports and final evidence

Complete and synchronize:

- `docs/stage3/WP02_SOURCE_FEASIBILITY.md`;
- `docs/stage3/WP02_DATA_FACTORY_REPORT.md`;
- `docs/stage3/WP02_CORPUS_AUDIT.md`;
- `docs/stage3/WP02_REJECTION_REPORT.md`;
- PR #30 body;
- Issue #29 receipt.

All counts and distributions must be generated from canonical artifacts. Separate configured sources, observed probe evidence, accepted cases, rejected cases, quarantines, failures and unsupported claims.

## Q08 — Final tests and receipt

Run focused data-factory tests, all cognition_v2 regressions, Stage 2 regressions, the full repository suite, the exact same full command on current `origin/main` for claimed pre-existing failures, and `git diff --check`.

Push only the existing branch and update only PR #30 and Issue #29. Do not self-merge.

Stop with:

```text
terminal_state: <WP02_ACCEPTED_CANDIDATE|WP02_SOURCE_FEASIBILITY_BLOCKED|WP02_DATA_QUALITY_BLOCKED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 29
pr: 30
branch: feat/stage3-wp02-historical-data-factory
start_head: 8435ccd06866505f707fc0f0ada0976679d517fd
final_remote_head: <exact 40-char SHA>
registry_source_ids: 11
source_family_bindings: 11
registry_report_counts_match: <pass/fail>
live_probe_results: <exact mapping>
pilot_eligible_adapters: <exact list>
completed_resume_source_requests: 0
completed_resume_new_records: 0
persisted_output_reloaded_before_write: <pass/fail>
persisted_dedupe_state_restored: <pass/fail>
output_checkpoint_mismatch_detection: <pass/fail>
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

`WP02_ACCEPTED_CANDIDATE` is valid only when the 120-case pilot and final 1,500-case corpus both pass every mandatory gate. Do not begin WP-03.
