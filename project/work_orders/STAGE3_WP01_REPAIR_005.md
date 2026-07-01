# Stage 3 WP-01 Repair 005

**Issue:** #27  
**Draft PR:** #28  
**Branch:** `feat/stage3-wp01-production-foundation`  
**Reviewed Head:** `6f2fa448d98ed5bf394ac26d197879028d96adab`

Repair only the final bidirectional-parity, persisted split-audit and evidence-consistency gaps. Preserve all valid WP-01 work. Do not start WP-02.

## R30 — Safe synchronization

Fetch refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. Do not reset, clean, stash, rebase or create another branch.

## R31 — Complete bidirectional schema parity

Strengthen `schema_parity_check()` so the comparison is exact in both directions.

It must report:

- missing and extra tables;
- missing and extra columns;
- type-family, nullability and primary-key differences;
- missing and extra foreign-key triples `(local_column, referred_table, referred_column)`;
- missing and extra unique constraints/indexes using normalized column tuples;
- exact deterministic diagnostics.

Required negative tests must create real independent mismatches and assert the exact affected table/field:

1. migration schema has an unexpected extra column;
2. expected schema requires a missing column;
3. actual foreign key points to the wrong table or wrong referred column;
4. required unique constraint is missing;
5. migration has an unexpected extra unique constraint;
6. migration has an unexpected extra foreign key.

Do not count a valid-schema recheck as a negative test. Do not treat a constrained column with any foreign key as parity.

## R32 — Strict persisted identity semantics

Update `CorrectionChainSplitValidator` to use only persisted identity fields as identity authority:

- a missing `event_identity_id` means event-identity comparison is unavailable; do not substitute `case_id` and claim identity validation;
- a missing `correction_chain_id` means the case is not part of a correction chain; do not create a synthetic one-case chain from `case_id`;
- all members of one non-null `correction_chain_id` must declare one consistent `chain_root_case_id`;
- when a root is declared, the root case must exist in the supplied manifests and belong to that chain;
- one non-null `event_identity_id` cannot cross splits;
- one non-null `correction_chain_id` cannot cross splits.

Diagnostics must include exact case IDs, event identity or chain ID, declared root IDs and split labels.

## R33 — Explicit BLIND tuning exclusion

Extend the production validator API with an explicit tuning/training input set, such as `tuning_case_ids`, or an equivalent typed input.

Reject:

- a BLIND case ID included in tuning input;
- any tuning case sharing a BLIND `event_identity_id`;
- any tuning case belonging to a BLIND `correction_chain_id`;
- a correction-chain root or member from BLIND entering BUILD/DEVELOPMENT tuning through an alternate case ID.

Return exact violating tuning case IDs, BLIND case IDs, event identities and chain IDs.

## R34 — Full persisted close/reopen audit matrix

Use temporary file-backed databases initialized only with Alembic. After seeding, dispose the engine, reopen the same database without `Base.metadata.create_all()`, reconstruct manifests from persisted rows and run the production validator.

Required independent tests:

- a valid same-split correction chain passes after reopen;
- the same persisted event identity across BUILD and BLIND is rejected;
- one persisted correction chain across DEVELOPMENT and BLIND is rejected;
- inconsistent chain roots are rejected;
- missing declared root is rejected;
- BLIND case tuning exclusion is rejected;
- BLIND event-identity tuning exclusion is rejected;
- BLIND correction-chain tuning exclusion is rejected;
- diagnostics contain exact persisted IDs and split labels.

Do not satisfy this requirement with one combined cross-chain test only.

## R35 — Final evidence package

Rewrite from the final tested tree:

- `docs/stage3/WP01_ENGINEERING_REPORT.md`;
- `docs/stage3/WP01_SCHEMA_MAP.md`;
- PR #28 body;
- Issue #27 receipt.

The committed report must not contain:

- the prior Head `ad4d4f...` as the final tested Head;
- stale 157/3333 totals after the test count changes;
- “before repair-004 changes” language;
- unsupported claims about exact schema parity or persisted split isolation.

The report must contain exact commands and results for:

- WP-01 focused tests;
- Stage 2 regressions;
- schema-parity tests;
- persisted split-audit tests;
- full branch suite;
- the exact same full-suite command on current `origin/main`, run in a safe temporary worktree when classifying failures as pre-existing;
- `git diff --check`.

Do not put a self-referential final commit SHA into a tracked file. After the final push, record the exact remote SHA only in PR #28 and Issue #27.

## R36 — Final verification

Run all required suites and `git diff --check`. Push only the existing branch and update only PR #28 and Issue #27.

Stop with:

```text
terminal_state: <WP01_ACCEPTED_CANDIDATE|WP01_REDESIGN_REQUIRED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 27
pr: 28
branch: feat/stage3-wp01-production-foundation
start_head: 6f2fa448d98ed5bf394ac26d197879028d96adab
final_remote_head: <exact 40-char SHA>
schema_missing_column_detection: <pass/fail>
schema_extra_column_detection: <pass/fail>
schema_wrong_fk_target_detection: <pass/fail>
schema_missing_fk_detection: <pass/fail>
schema_extra_fk_detection: <pass/fail>
schema_missing_unique_detection: <pass/fail>
schema_extra_unique_detection: <pass/fail>
schema_exact_parity: <pass/fail>
no_case_id_identity_fallback: <pass/fail>
no_case_id_chain_fallback: <pass/fail>
consistent_chain_root_enforced: <pass/fail>
missing_chain_root_rejected: <pass/fail>
persisted_valid_chain_after_reopen: <pass/fail>
persisted_cross_split_event_rejected: <pass/fail>
persisted_cross_split_chain_rejected: <pass/fail>
blind_case_tuning_exclusion: <pass/fail>
blind_identity_tuning_exclusion: <pass/fail>
blind_chain_tuning_exclusion: <pass/fail>
exact_persisted_diagnostics: <pass/fail>
report_matches_final_tested_tree: <pass/fail>
schema_map_matches_code: <pass/fail>
focused_tests: <exact result>
stage2_regression: <exact result>
full_suite_branch: <exact result>
full_suite_main_comparison: <exact result>
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
