# Stage 3 WP-01 Repair 001

**Issue:** #27  
**Draft PR:** #28  
**Branch:** `feat/stage3-wp01-production-foundation`  
**Reviewed Head:** `3d33006f82a448f6fed500776a701ab784c7ae69`

Repair the same branch and PR. Preserve all valid work. Do not start WP-02.

## R00 — Safe synchronization

Fetch all refs, check out the existing branch and fast-forward only. Stop for tracked local changes or unexplained untracked product files. Do not reset, clean, stash, rebase or create another branch.

## R01 — Real immutable revisions

Enforce immutability for both `EventRevisionModel` and `ThesisRevisionModel`.

Acceptable implementation:

- registered SQLAlchemy `before_update` and `before_delete` listeners with a typed `RevisionImmutableError`; or
- database triggers plus typed repository errors.

Required tests:

- commit a revision, attempt update, commit fails with the exact error;
- reopen and prove the row is unchanged;
- attempt delete, commit fails with the exact error;
- reopen and prove the row remains;
- duplicate `(entity_id, version)` remains rejected;
- cover both event and thesis revisions.

Remove the unregistered `block_revision_modification()` claim or wire it correctly.

## R02 — Transactional persistent lifecycle service

Implement a production lifecycle application service backed by SQLAlchemy.

One transition transaction must:

1. resolve an existing idempotency key and return the original committed result;
2. load the thesis current projection;
3. verify expected state and version;
4. validate the canonical legal edge;
5. require a non-empty reason;
6. require evidence or rule references for epistemic transitions;
7. append an immutable `ThesisRevisionModel` containing the idempotency key and evidence/rule references;
8. perform a single-statement CAS update of the current thesis projection;
9. commit revision and projection atomically;
10. roll back both on any failure.

Add schema and migration support for:

- unique transition idempotency key;
- serialized or relational evidence references;
- rule references;
- transition timestamp and previous state/version.

Required tests:

- one legal transition writes exactly one revision and advances the projection;
- stale version writes nothing;
- illegal edge writes nothing;
- missing epistemic references is rejected;
- repeating the same idempotency key returns the existing revision and creates no duplicate;
- reusing one idempotency key with different request content is rejected;
- injected failure after revision staging leaves neither revision nor projection update;
- close/reopen preserves the committed result.

Replace `test_same_request_validates_twice`; validation-only repetition is not idempotency.

## R03 — Event state separation

Create an event-specific status enum and contract. Do not reuse `ThesisState` for events.

Define the minimal event-resolution states needed by the data factory, such as:

- DISCOVERED
- RESOLVING
- CONFIRMED
- CONTESTED
- CORRECTED
- RETRACTED
- SUPERSEDED
- REJECTED

The exact names may be adjusted, but event identity/resolution must remain separate from thesis lifecycle. Update Pydantic contracts, SQLAlchemy model, migration, schema map and tests.

## R04 — Explicit point-in-time authority

For historical/replay creation paths, do not silently invent critical authority or time facts.

Required changes:

- source authority and fact permission must be explicitly supplied for persisted historical sources;
- evidence first-seen and retrieval times must be explicit for historical evidence;
- all point-in-time datetimes must be timezone-aware;
- assessment time must be explicit for an evaluated historical case;
- BLOCKED/INSUFFICIENT claims with no evidence must include at least one structured abstention or missing-input reason;
- SUPPORTED/STRONG still require evidence references.

Convenience defaults may exist only in clearly named live-construction helpers, not in canonical historical contracts.

## R05 — Real future-leakage validation

Validate complete evidence availability rather than arbitrary datetime lists.

For each evidence item, the information is available to an assessment only when its allowed availability time is at or before the assessment cutoff. At minimum use `first_seen_at` and `retrieval_time`; publication/effective time alone must never make later-retrieved evidence available earlier.

Required tests:

- published before cutoff but retrieved after cutoff is blocked;
- retrieved before cutoff but assessed after cutoff remains available only at/after retrieval;
- correction first seen after cutoff is blocked even when correcting an older item;
- mixed clean/leaked evidence returns exact blocked IDs and reasons;
- timezone-naive values are rejected;
- filtering cannot silently discard evidence without an audit result.

## R06 — Real split-order integrity

Replace the no-op split validator.

Implement explicit frozen boundaries or a deterministic chronological allocation policy with these guarantees:

- BUILD precedes DEVELOPMENT;
- DEVELOPMENT precedes BLIND;
- one case cannot appear in multiple splits;
- one event identity or correction chain cannot cross into another split in a way that leaks the target outcome;
- BLIND IDs cannot be accepted as tuning/training input;
- adding a newer case cannot retroactively move an existing frozen BLIND case;
- invalid overlap returns exact case IDs and boundary violations.

Required tests must include valid multi-case ordering and actual invalid overlaps. A single BUILD case does not prove split integrity.

## R07 — Correct outcome windows

Compute close times from event time:

- 1h = +1 hour;
- 6h = +6 hours;
- 24h = +24 hours;
- 3d = +3 days;
- 7d = +7 days.

Validate:

- close time is after open time;
- labels are from the canonical set;
- price and return values are finite when present;
- high is not below low;
- outcome data is separated from evidence available to the cognition run;
- future outcome fields cannot enter the input manifest hash used at assessment time.

## R08 — Evidence consistency

Update together:

- production contracts and models;
- Alembic baseline or a follow-up migration appropriate for the unmerged branch;
- `WP01_SCHEMA_MAP.md`;
- `WP01_ENGINEERING_REPORT.md`;
- PR #28 body;
- Issue #27 receipt.

The report must include exact commands and distinguish:

- WP-01 focused tests;
- Stage 2 regression tests;
- full repository suite command and result;
- the same full-suite result on `main` when claiming a pre-existing dependency blocker.

Do not write that immutability, idempotency, split integrity or leakage blocking passed unless the repaired responsibility tests exist and pass.

## R09 — Final verification and receipt

Run focused WP-01 tests, Stage 2 regressions and the full repository suite. Run `git diff --check`. Push only the existing branch and update the existing Draft PR.

Stop with:

```text
terminal_state: <WP01_ACCEPTED_CANDIDATE|WP01_REDESIGN_REQUIRED|LOCAL_STATE_REVIEW_REQUIRED>
repo: zhuo74451-art/crypto-event-intelligence
issue: 27
pr: 28
branch: feat/stage3-wp01-production-foundation
start_head: 3d33006f82a448f6fed500776a701ab784c7ae69
final_remote_head: <exact 40-char SHA>
event_revision_update_rejected: <pass/fail>
event_revision_delete_rejected: <pass/fail>
thesis_revision_update_rejected: <pass/fail>
thesis_revision_delete_rejected: <pass/fail>
transactional_lifecycle_transition: <pass/fail>
transition_idempotent_replay: <pass/fail>
transition_conflict_rejected: <pass/fail>
transition_atomic_rollback: <pass/fail>
event_state_separate_from_thesis: <pass/fail>
explicit_historical_authority_and_times: <pass/fail>
structured_abstention_reason_required: <pass/fail>
point_in_time_leakage_tests: <exact result>
split_order_integrity_tests: <exact result>
outcome_window_time_tests: <exact result>
real_alembic_upgrade: <pass/fail>
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

Do not merge and do not begin WP-02. GPT will independently inspect and integrate only the accepted exact remote Head.
