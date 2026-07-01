# Stage 3 WP-01 Repair 003

**Issue:** #27  
**Draft PR:** #28  
**Branch:** `feat/stage3-wp01-production-foundation`  
**Reviewed Head:** `45f1e032aa44fc2823d3d8144412ae07b5cd02e6`

Repair only the production-schema and evidence-consistency gaps. Preserve all valid Repair 001/002 work. Do not start WP-02.

## R17 — Safe synchronization

Fetch refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. Do not reset, clean, stash, rebase or create another branch.

## R18 — Make Alembic the production source of schema truth

Update the unmerged baseline migration so a database created by `alembic upgrade head` exactly supports the current ORM and services.

At minimum synchronize:

- `events.event_state` instead of `events.lifecycle_state`;
- `event_revisions.previous_version`;
- `event_revisions.idempotency_key` and its uniqueness constraint;
- `event_revisions.rule_refs_json` and any persisted evidence references required by the contract;
- `thesis_revisions.previous_state`;
- `thesis_revisions.idempotency_key` and uniqueness;
- `thesis_revisions.request_fingerprint`;
- `thesis_revisions.evidence_refs_json`;
- `thesis_revisions.rule_refs_json`;
- all foreign keys declared by ORM models;
- all uniqueness and nullability guarantees declared by ORM models;
- historical identity fields introduced by R20 below.

Because the branch is not merged, replace the baseline cleanly rather than creating compatibility debt unless a separate revision is technically safer and fully tested.

## R19 — Automated migration/ORM schema parity

Add a reusable schema-parity validator that:

1. creates one empty SQLite database through Alembic only;
2. introspects the resulting database with SQLAlchemy Inspector;
3. compares it against `Base.metadata`;
4. reports exact table, column, type-family, nullability, primary-key, foreign-key and unique-constraint differences.

Required tests:

- migration-created schema matches ORM metadata for every production table;
- removing or renaming a required column in a deliberately altered expected schema produces an exact mismatch;
- `events.event_state` exists and `events.lifecycle_state` does not;
- thesis revision audit/idempotency columns exist;
- required foreign keys exist;
- migration failure remains fatal;
- downgrade returns to the documented base state.

Replace the current migration check that only proves an `alembic_version` row exists.

## R20 — Run production services on an Alembic-created database

Use a temporary file database initialized only by Alembic. Do not call `Base.metadata.create_all()`.

Prove on that database:

- insert and reload EventModel using `event_state`;
- insert a thesis;
- execute `TransactionalLifecycleService.transition()`;
- persist request fingerprint, idempotency key, evidence/rule refs and previous state;
- replay the same idempotency key after engine disposal and reopen;
- reject a conflicting same-key request;
- immutable revision listeners still protect ORM updates/deletes;
- all required foreign keys are enforced.

This is the decisive production-path test for WP-01.

## R21 — Durable historical event and correction-chain identity

Persist stable identity needed by WP-02. Update the canonical historical manifest, ORM model, migration and schema map with explicit fields such as:

- `event_identity_id`;
- `correction_chain_id`;
- optional `chain_root_case_id` or equivalent root reference;
- correction relationship/type where applicable.

Requirements:

- deterministic manifest hashing includes the stable input identity fields but excludes outcome data;
- one event/correction chain can be reconstructed from persisted cases;
- split validator consumes the persisted identity fields rather than a disconnected in-memory-only object;
- BLIND chain isolation remains auditable after database close/reopen.

Required tests:

- round-trip persisted historical identity and chain fields;
- reconstruct a correction chain after reopen;
- reject cross-split event identity and correction-chain leakage using persisted records;
- manifest hash changes when identity/chain input changes;
- outcome fields do not affect input manifest hash.

## R22 — One source of truth for reports

Rewrite from the exact final Head:

- `docs/stage3/WP01_ENGINEERING_REPORT.md`;
- `docs/stage3/WP01_SCHEMA_MAP.md`;
- PR #28 body;
- Issue #27 receipt.

Remove stale statements including:

- 94 WP-01 / 248 total tests;
- old validation-only lifecycle description;
- `EventRecord.lifecycle_state`;
- any field or guarantee not present in both ORM and migration.

The report must separately show:

- WP-01 focused command/result;
- Stage 2 regression command/result;
- full branch suite command/result;
- same command/result on current `main` for any claimed pre-existing dependency blocker;
- migration/ORM parity result;
- Alembic-only production-path result;
- exact final remote Head;
- known limits and unsupported claims.

## R23 — Final verification

Run focused WP-01 tests, Stage 2 regressions, full suite, migration parity and `git diff --check`. Push only the existing branch and update only PR #28.

Stop with:

```text
terminal_state: <WP01_ACCEPTED_CANDIDATE|WP01_REDESIGN_REQUIRED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 27
pr: 28
branch: feat/stage3-wp01-production-foundation
start_head: 45f1e032aa44fc2823d3d8144412ae07b5cd02e6
final_remote_head: <exact 40-char SHA>
alembic_orm_schema_parity: <pass/fail>
event_state_column_parity: <pass/fail>
thesis_revision_audit_columns: <pass/fail>
foreign_key_parity: <pass/fail>
unique_constraint_parity: <pass/fail>
alembic_only_lifecycle_transition: <pass/fail>
alembic_only_idempotent_replay_after_reopen: <pass/fail>
alembic_only_conflicting_replay_rejected: <pass/fail>
historical_identity_persisted: <pass/fail>
correction_chain_reconstructed_after_reopen: <pass/fail>
persisted_chain_split_isolation: <pass/fail>
manifest_identity_hashing: <pass/fail>
outcome_excluded_from_input_hash: <pass/fail>
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
