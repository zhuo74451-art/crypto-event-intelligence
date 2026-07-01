# Stage 3 WP-01 Repair 004

**Issue:** #27  
**Draft PR:** #28  
**Branch:** `feat/stage3-wp01-production-foundation`  
**Reviewed Head:** `ad4d4f625e292c13167f188c042aecaac812aceb`

Repair only the remaining exact-parity, persisted split-isolation and documentation gaps. Preserve all valid WP-01 work. Do not start WP-02.

## R24 — Safe synchronization

Fetch refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. Do not reset, clean, stash, rebase or create another branch.

## R25 — Make schema parity exact rather than one-sided

Strengthen `schema_parity_check()` so it reports exact differences in both directions.

Required comparisons:

- missing and extra tables;
- missing and extra columns;
- type family;
- nullability;
- primary keys;
- foreign-key triples: constrained column, referred table and referred column;
- missing and extra foreign keys;
- composite and single-column unique constraints/indexes;
- missing and extra unique constraints.

Do not consider a foreign key correct merely because the constrained column has some foreign key.

Replace `test_deliberate_mismatch_detected`, which currently only rechecks the valid schema, with a real negative test. Construct altered expected metadata or a deliberately altered disposable schema and prove exact diagnostics for at least:

- one missing/renamed required column;
- one wrong foreign-key target;
- one missing unique constraint;
- one unexpected extra column.

Keep the full Alembic-created schema parity test and migration-failure/downgrade tests.

## R26 — Use persisted historical identity in split isolation

`CorrectionChainSplitValidator` must use the fields carried by each `HistoricalCaseManifest`:

- `event_identity_id`;
- `correction_chain_id`;
- `chain_root_case_id`;
- `correction_type`;
- `split_label`.

Remove the `case_id` event-identity proxy. Do not require a disconnected in-memory `CorrectionRelations` graph as the authority when persisted identity fields are available.

Required behavior:

- the same non-null `event_identity_id` cannot appear across multiple splits;
- the same non-null `correction_chain_id` cannot cross splits;
- every chain member must agree on one root identity when a root is declared;
- a BLIND event identity or chain cannot enter BUILD/DEVELOPMENT tuning IDs;
- exact violating case IDs, identity IDs, chain IDs and split labels are returned;
- cases without a correction chain remain valid when event identity is present.

## R27 — Prove persisted close/reopen split audit

Use a temporary file-backed database initialized by Alembic only.

Required test:

1. persist historical cases with event identities, a correction chain and split labels;
2. dispose the engine without calling `Base.metadata.create_all()` again;
3. reopen the same database with a normal engine/session factory;
4. reconstruct `HistoricalCaseManifest` objects from persisted rows;
5. run the production split-isolation validator;
6. prove a valid same-split chain passes;
7. prove a cross-split event identity is rejected;
8. prove a cross-split correction chain is rejected;
9. prove BLIND identity/chain tuning exclusion;
10. prove diagnostics contain exact persisted IDs.

Replace the current close/reopen test that calls `Base.metadata.create_all()` again.

## R28 — Rewrite the evidence package

Rewrite, from the current implementation and exact commands:

- `docs/stage3/WP01_ENGINEERING_REPORT.md`;
- `docs/stage3/WP01_SCHEMA_MAP.md`;
- PR #28 body;
- Issue #27 final receipt.

Remove all stale statements, including:

- 94 WP-01 / 248 total tests;
- validation-only lifecycle service description;
- `EventRecord.lifecycle_state`;
- schema fields that do not match ORM and Alembic;
- claims that historical identity isolation uses persisted fields unless R26/R27 tests pass.

The engineering report must document:

- transactional lifecycle and deterministic request fingerprint;
- immutable revisions;
- Alembic/ORM exact parity;
- Alembic-only service execution;
- persisted event/correction-chain identity;
- persisted close/reopen split audit;
- exact focused and Stage 2 regression commands/results;
- exact full-suite branch and `main` comparison when classifying pre-existing blockers;
- known limits and unsupported claims.

Do not place a self-referential final commit SHA inside a file that would change that SHA. Record the tested command output and tree state in the report; record the exact final remote SHA in PR #28 and Issue #27 after the final push.

## R29 — Final verification

Run focused WP-01 tests, Stage 2 regressions, full suite and `git diff --check`. Push only the existing branch and update only PR #28.

Stop with:

```text
terminal_state: <WP01_ACCEPTED_CANDIDATE|WP01_REDESIGN_REQUIRED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 27
pr: 28
branch: feat/stage3-wp01-production-foundation
start_head: ad4d4f625e292c13167f188c042aecaac812aceb
final_remote_head: <exact 40-char SHA>
schema_extra_column_detection: <pass/fail>
schema_wrong_fk_target_detection: <pass/fail>
schema_missing_unique_detection: <pass/fail>
schema_exact_parity: <pass/fail>
persisted_event_identity_validator: <pass/fail>
persisted_correction_chain_validator: <pass/fail>
alembic_file_db_reopen_without_create_all: <pass/fail>
persisted_valid_chain_after_reopen: <pass/fail>
persisted_cross_split_event_rejected: <pass/fail>
persisted_cross_split_chain_rejected: <pass/fail>
persisted_blind_tuning_exclusion: <pass/fail>
report_stale_claims_removed: <pass/fail>
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
