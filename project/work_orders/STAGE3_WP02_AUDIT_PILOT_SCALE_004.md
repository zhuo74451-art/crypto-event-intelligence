# Stage 3 WP-02 Audit, Pilot and Scale 004

**Issue:** #29  
**Draft PR:** #30  
**Branch:** `feat/stage3-wp02-historical-data-factory`  
**Reviewed Head:** `8a9a5253962a1f15b19ade49440724018a4d8942`

Continue the same branch and Draft PR. Preserve valid work. Do not begin WP-03.

## S00 — Safe synchronization

Fetch refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. Do not reset, clean, stash, rebase or create another branch.

## S01 — Finish the durable acquisition protocol

Make output and checkpoint a verifiable committed pair.

Checkpoint must persist:

- run status;
- typed completion reason: SOURCE_EXHAUSTED, RECORD_LIMIT, RECORD_BUDGET, REQUEST_BUDGET, FAILED;
- request fingerprint;
- adapter version and parser version;
- last committed page token;
- committed page list;
- committed record count;
- committed output SHA-256;
- committed output byte size;
- checkpoint schema version.

Required transaction semantics:

- stage new records and next checkpoint state without mutating committed in-memory state;
- write and fsync new output first;
- only after output success, advance committed records, counters, pages and token;
- then atomically write checkpoint;
- output-write failure leaves previous output and checkpoint unchanged;
- checkpoint-write failure leaves the newer output detectable as ahead of checkpoint and recoverable without duplication;
- resume verifies output count, SHA-256 and byte size;
- same-count altered or reordered output is rejected;
- completed resume makes zero source requests and returns zero new records while exposing the committed corpus separately;
- parser or adapter version change rejects resume unless an explicit migration creates a new run ID;
- source-exhausted completion with null token remains terminal.

Required committed tests:

- completed resume after source exhaustion: zero requests and zero new records;
- completed resume after record limit;
- process-style reopen restores records and dedupe IDs;
- output-write injected failure leaves old checkpoint and output unchanged;
- checkpoint-write injected failure leaves newer output recoverable;
- same-count output mutation is rejected by hash;
- output truncation is rejected;
- parser-version and adapter-version mismatch rejected;
- duplicate page after reopen does not duplicate output;
- cyclic page token after reopen fails safely;
- max record budget below record limit remains a hard ceiling.

Do not claim these tests unless they exist on the final remote Head.

## S02 — Run bounded source probes

Run finite public read-only probes for every adapter used by the pilot.

Record exact endpoint, source ID, UTC range, request count, HTTP status, parser/adapter versions, item count, earliest/latest parsed publication time, malformed count and failure class.

A source is pilot-eligible only when the probe produces correctly parsed source items. Configuration-only sources remain pending or rejected.

The feasibility report must not say CONFIRMED while required family routes remain pending.

## S03 — Complete the production auditor

Audit actual canonical artifacts using explicit case assessment times.

Mandatory computed gates:

- point-in-time completeness and future leakage;
- authority and permission completeness;
- duplicate accepted cases;
- cross-split event identities;
- cross-split correction chains;
- BLIND case, identity, chain and outcome contamination;
- outcome reference and structural validity;
- 24h outcome coverage >=95%;
- full source -> evidence -> case -> outcome provenance coverage =100%;
- deterministic second rebuild exists and matches every artifact hash and corpus root.

Missing artifacts must fail. Every failed gate must report exact IDs and reasons. Add mutation tests for every gate.

## S04 — Canonical artifacts and SQLite roundtrip

Implement the complete deterministic artifact set under `data/historical_v1/`:

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

Requirements:

- sorted-key JSONL and deterministic record/shard order;
- every shard listed with SHA-256;
- no volatile timestamp in deterministic hashes;
- no credentials, private paths or full article bodies;
- SQLite materialization from canonical files;
- reverse export yields equivalent canonical records and identical hashes.

## S05 — Real 120-case pilot

Use only pilot-eligible adapters and bounded public reads.

Build at least 120 QUALIFIED cases, at least 20 per family. Each case requires permitted evidence, exact URL, stable event identity, explicit point-in-time fields, authority, permission, asset/benchmark mapping, versioned regime label, separate 1h/6h/24h outcomes, 3d/7d outcomes or explicit missing reason, and complete provenance.

Pilot must pass:

- each family >=20;
- no synthetic, cloned, timestamp-shifted or repeated-summary cases;
- point-in-time and permission completeness 100%;
- future leakage 0;
- duplicate accepted IDs 0;
- cross-split identities/chains 0;
- BLIND contamination 0;
- 24h outcome coverage >=95%;
- audit-path coverage 100%;
- two clean rebuilds with identical hashes.

If it cannot pass after documented fallbacks, stop with a blocked terminal state. Do not fabricate or scale.

## S06 — Scale to at least 1,500 QUALIFIED cases

Scale only after the pilot passes.

Final gates:

- qualified cases >=1,500;
- every family >=150;
- no family >35%;
- bull, bear, ranging, high_volatility, crisis and recovery represented;
- unknown regime <=10%;
- frozen chronological BUILD / DEVELOPMENT / BLIND splits;
- event identity and correction-chain split integrity;
- zero BLIND contamination;
- point-in-time and permission completeness 100%;
- future leakage 0;
- duplicate accepted IDs 0;
- outcome structural violations 0;
- 24h outcome coverage >=95%;
- audit-path coverage 100%;
- two clean full rebuilds with identical artifact and root hashes.

## S07 — Reports and final evidence

Complete and synchronize:

- `docs/stage3/WP02_SOURCE_FEASIBILITY.md`;
- `docs/stage3/WP02_DATA_FACTORY_REPORT.md`;
- `docs/stage3/WP02_CORPUS_AUDIT.md`;
- `docs/stage3/WP02_REJECTION_REPORT.md`;
- PR #30 body;
- Issue #29 receipt.

All counts must be generated from canonical artifacts. Clearly separate configured sources, observed probes, accepted cases, rejected cases, quarantines and unsupported claims.

## S08 — Final verification

Run focused WP-02 tests, all cognition_v2 regressions, Stage 2 regressions, full repository suite, the same full command on current `origin/main` for claimed pre-existing failures, and `git diff --check`.

Push only the existing branch and update only PR #30 and Issue #29. Do not self-merge.

Stop with:

```text
terminal_state: <WP02_ACCEPTED_CANDIDATE|WP02_SOURCE_FEASIBILITY_BLOCKED|WP02_DATA_QUALITY_BLOCKED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 29
pr: 30
branch: feat/stage3-wp02-historical-data-factory
start_head: 8a9a5253962a1f15b19ade49440724018a4d8942
final_remote_head: <exact 40-char SHA>
registry_source_ids: 11
source_family_bindings: 11
live_probe_results: <exact mapping>
pilot_eligible_adapters: <exact list>
completed_resume_source_requests: 0
completed_resume_new_records: 0
output_hash_verified_on_resume: <pass/fail>
output_size_verified_on_resume: <pass/fail>
output_write_failure_preserves_commit: <pass/fail>
checkpoint_write_failure_recoverable: <pass/fail>
parser_adapter_version_resume_guard: <pass/fail>
committed_recovery_tests: <exact result>
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

`WP02_ACCEPTED_CANDIDATE` is valid only when the 120-case pilot and final 1,500-case corpus pass every mandatory gate. Do not begin WP-03.
