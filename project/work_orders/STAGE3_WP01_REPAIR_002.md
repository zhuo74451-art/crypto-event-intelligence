# Stage 3 WP-01 Repair 002

**Issue:** #27  
**Draft PR:** #28  
**Branch:** `feat/stage3-wp01-production-foundation`  
**Reviewed Head:** `dfc10ee86969012f2ac1b331b14d3947d5b62560`

Repair only the remaining evidence gaps. Preserve all valid Repair 001 work. Do not start WP-02.

## R10 — Safe synchronization

Fetch refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. Do not reset, clean, stash, rebase or create another branch.

## R11 — Deterministic transition request identity

Persist a deterministic fingerprint for every committed lifecycle transition. The fingerprint must cover at least:

- thesis_id;
- from_state;
- to_state;
- expected_version;
- normalized reason;
- normalized evidence references;
- normalized rule references.

When an idempotency key already exists:

- return the existing committed result only when the stored fingerprint matches exactly;
- raise `IdempotentTransitionError` when any request field differs, including same thesis_id with a different target state, reason, evidence ref or rule ref.

Update model, migration, service and schema map.

Required tests:

- exact replay returns the same revision and does not advance the projection twice;
- same key and same thesis but different target state is rejected;
- same key and same thesis but different reason is rejected;
- same key and same thesis but different evidence refs is rejected;
- same key and same thesis but different rule refs is rejected;
- normalized ordering of equivalent evidence/rule refs produces the same fingerprint.

## R12 — Failure injection through the production service

Add a test-only or dependency-injected failure hook to `TransactionalLifecycleService` at a defined point after revision staging and before commit/CAS completion.

The production default must have no failure hook and no behavior change.

Required test:

- create a thesis in a file-backed or normal test database;
- call the real `transition()` method with failure injection enabled;
- surface the injected exception;
- prove no revision persisted;
- prove thesis state and version are unchanged;
- reopen the database and prove the rollback remains true.

Do not manually reproduce part of the transaction outside the service and call that service rollback evidence.

## R13 — Real close/reopen recovery

Replace the empty in-memory test with a temporary file-backed SQLite database.

Required proof:

1. create the database and migrate/initialize it;
2. insert a thesis;
3. execute a real lifecycle transition;
4. dispose the engine and close sessions;
5. create a new engine/session factory for the same file;
6. prove the current thesis projection and exact immutable revision remain;
7. replay the same idempotency key after reopen and receive the existing result without another revision.

Remove all `pass` placeholders and comments that admit the test does not work.

## R14 — Correction-chain split isolation

Extend historical manifests or a related split-assignment record with stable event identity and correction-chain identity.

The frozen split validator must reject:

- the same event identity appearing across more than one split;
- a correction, retraction, contradiction or superseding item placed in a different split from its chain root when that would expose later information to an earlier tuning set;
- any BLIND chain member or chain outcome entering BUILD/DEVELOPMENT tuning input.

Required tests:

- valid chain remains inside one split;
- same event identity across BUILD and BLIND is rejected;
- correction chain crossing DEVELOPMENT and BLIND is rejected;
- BLIND chain IDs are rejected from training/tuning input;
- exact violating case IDs, chain IDs and split labels are reported.

## R15 — One source of truth for evidence

Rewrite from exact final commands:

- `docs/stage3/WP01_ENGINEERING_REPORT.md`;
- `docs/stage3/WP01_SCHEMA_MAP.md` when schema changes;
- PR #28 body;
- Issue #27 final receipt.

The engineering report must contain separately:

- WP-01 focused test command and exact result;
- Stage 2 regression command and exact result;
- full branch suite command and exact result;
- the same full-suite command/result on current `main` when claiming pre-existing blockers;
- exact final remote Head;
- known limits and unsupported claims.

No stale 94/248 totals may remain after the final test count changes.

## R16 — Final verification

Run the focused suite, Stage 2 regression and full repository suite. Run `git diff --check`. Push only the existing branch and update only PR #28.

Stop with:

```text
terminal_state: <WP01_ACCEPTED_CANDIDATE|WP01_REDESIGN_REQUIRED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 27
pr: 28
branch: feat/stage3-wp01-production-foundation
start_head: dfc10ee86969012f2ac1b331b14d3947d5b62560
final_remote_head: <exact 40-char SHA>
transition_request_fingerprint: <pass/fail>
same_key_different_target_rejected: <pass/fail>
same_key_different_reason_rejected: <pass/fail>
same_key_different_evidence_rejected: <pass/fail>
same_key_different_rules_rejected: <pass/fail>
service_failure_injection_rollback: <pass/fail>
file_database_close_reopen: <pass/fail>
idempotent_replay_after_reopen: <pass/fail>
event_identity_split_isolation: <pass/fail>
correction_chain_split_isolation: <pass/fail>
blind_chain_tuning_exclusion: <pass/fail>
focused_tests: <exact result>
stage2_regression: <exact result>
full_suite_branch: <exact result>
full_suite_main_comparison: <exact result>
report_matches_exact_head: <pass/fail>
git_diff_check: <pass/fail>
old_cognition_core_modified: no
pr_16_draft_unmerged: <pass/fail>
real_model_calls: 0
paid_api_calls: 0
postgres_installed_or_started: no
background_processes_created: 0
blockers: <none-or-list>
```

Do not merge and do not begin WP-02. GPT independently reviews and directly integrates only the accepted exact remote Head.
