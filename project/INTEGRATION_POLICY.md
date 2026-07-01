# Integration Policy

**Status:** Active

## Default rule

A change is merged into `main` without a separate owner confirmation when all of the following are true:

1. the change stays inside the accepted project responsibility and current work package;
2. remote Head, diff, tests, artifacts and runtime evidence have been independently inspected;
3. the candidate is demonstrably better than the current `main` behavior or state;
4. accepted behavior has not regressed;
5. evidence, rollback and recovery remain adequate;
6. the change introduces no new protected access, material recurring cost, public operation, irreversible external effect, wallet action or trading authority;
7. the exact reviewed Head is protected during merge.

The normal route is:

```text
Executor branch and Draft PR
  -> independent GPT acceptance
  -> exact-Head regression check
  -> direct merge to main
  -> remote main verification
  -> canonical state and next node update
```

The executor never merges its own work. GPT owns independent acceptance and integration.

## Meaning of improvement

A candidate is not better merely because it adds files, tests, abstractions or features.

Improvement requires evidence of at least one accepted result while preserving the rest:

- stronger user outcome;
- broader responsibility coverage;
- lower false confidence or better abstention;
- more reliable recovery;
- better point-in-time integrity;
- lower operating complexity for equivalent guarantees;
- lower cost for equivalent quality;
- clearer evidence and auditability;
- removal of obsolete or conflicting behavior.

For an audit or experiment branch, improvement means it resolves an accepted uncertainty with reproducible evidence and does not alter product behavior.

## Merge methods

- use squash merge for a focused work package unless preserving commit boundaries materially helps audit or migration;
- use exact expected Head SHA protection;
- do not merge a moving or unreviewed Head;
- verify the resulting `main` SHA and changed files after merge;
- immediately synchronize canonical state when the merged result changes project facts, decisions or the active node.

## Stop instead of merge

Do not merge when:

- the result is only partially better but leaves the active path internally inconsistent;
- tests assert file existence or structure without proving the accepted responsibility;
- documentation overstates implementation or evidence;
- the candidate creates a second source of truth;
- regression, migration or rollback evidence is missing;
- a dependency, license, security or infrastructure decision remains unresolved;
- the Head differs from the independently reviewed Head;
- the change crosses an owner-governance boundary.

In these cases, repair the same branch when the route remains valid. Replace or close the branch when its architecture is no longer the accepted route.

## Long-lived branch rule

A validated improvement must not remain indefinitely in a Draft PR. Once accepted, merge it and continue from updated `main`.

An obsolete branch is retained only when it serves as:

- historical evidence;
- a component quarry;
- a failure record;
- a migration source.

It does not retain planning authority.

## Current application

- Draft PR #16 is not eligible for merge because its architecture is no longer the accepted product path.
- The Stage 2 foundation compatibility spike is eligible for direct merge after independent acceptance because it is an isolated evidence package with no product behavior.
- Future product work packages are merged directly after exact-Head acceptance and regression proof unless they cross a declared governance boundary.
