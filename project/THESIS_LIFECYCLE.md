# Thesis Lifecycle

**Status:** Active

Lifecycle state and attention priority are separate.

## States

- `DISCOVERED` — bounded candidate record; no thesis claim.
- `QUALIFYING` — identity, evidence, mechanism, exposure and verification checks are running.
- `CANDIDATE` — basic checks passed, but active admission is incomplete.
- `ACTIVE` — all admission gates passed.
- `DORMANT` — potentially valid, but no near catalyst or marginal research value.
- `INVALIDATED` — a necessary premise or explicit falsification condition failed.
- `EXPIRED` — the declared window or catalyst passed without enough confirmation.
- `ARCHIVED` — no current attention; history remains queryable.
- `REOPEN_REVIEW` — new evidence may justify reopening, but reactivation is not automatic.
- `REJECTED` — admission failed; retained only for deduplication and learning.
- `ISOLATED` — identity, integrity, permission or security problems forbid semantic processing.

`STRENGTHENED`, `WEAKENED`, `CONTESTED` and `UNCHANGED` are revision outcomes, not lifecycle states.

## Legal transitions

```text
DISCOVERED -> QUALIFYING | REJECTED | ISOLATED
QUALIFYING -> CANDIDATE | REJECTED | ISOLATED | EXPIRED
CANDIDATE -> ACTIVE | DORMANT | REJECTED | EXPIRED | ISOLATED
ACTIVE -> ACTIVE | DORMANT | INVALIDATED | EXPIRED | ARCHIVED
DORMANT -> ACTIVE | INVALIDATED | EXPIRED | ARCHIVED
INVALIDATED -> ARCHIVED | REOPEN_REVIEW
EXPIRED -> ARCHIVED | REOPEN_REVIEW
ARCHIVED -> REOPEN_REVIEW
REJECTED -> REOPEN_REVIEW
ISOLATED -> QUALIFYING | REJECTED
REOPEN_REVIEW -> ACTIVE | CANDIDATE | ARCHIVED | REJECTED | ISOLATED
```

No transition may skip active-admission gates. Price movement alone cannot strengthen or reopen a thesis.

## Revision contract

Every review produces exactly one result:

- `UNCHANGED`
- `STRENGTHENED`
- `WEAKENED`
- `CONTESTED`
- `INVALIDATED`
- `EXPIRED`
- `ARCHIVED`
- `REOPENED`

The revision records what changed, why, which evidence changed it, and which prior claims remain valid.

## Invalidation, expiry and archive

- **Invalidated:** a necessary assumption fails, an explicit falsification condition occurs, or higher-authority evidence directly contradicts the thesis.
- **Expired:** the relevant time window closes or the named catalyst passes without enough confirming evidence.
- **Archived:** continuing research has negligible or negative attention value.

Invalidation is epistemic. Expiry is temporal. Archive is operational.

## Reopening

A closed thesis enters `REOPEN_REVIEW` only when:

- new independent evidence addresses the original failure;
- the relevant regime materially changes;
- an authoritative correction changes the event state;
- a new event changes the mechanism or exposure;
- a genuinely new catalyst appears after a time-bound expiry.

Reopening requires normal admission gates and a fresh Risk Agent review. Price, popularity or model disagreement alone is insufficient.

## Evidence freshness

Freshness is claim-type specific:

- immutable official facts remain valid until corrected;
- market-state evidence expires according to its data cadence;
- event status remains current only until the next expected update or deadline;
- research claims weaken when regime, applicability or assumptions change;
- social attention and price evidence have short validity and cannot establish causality alone.

Every active thesis declares `review_by`, `expires_at`, or an explicit event-based expiry rule.

## Minimum thesis record

- thesis ID and version;
- lifecycle state;
- portfolio class: thesis, risk observation or mechanism candidate;
- evidence and event references;
- mechanism and exposure links;
- horizon and priced-in state;
- support, counterevidence and uncertainty;
- next evidence and named catalyst;
- review trigger and `review_by`;
- expiry and invalidation conditions;
- complete revision history.

## Acceptance

- every transition follows the legal graph;
- lifecycle and attention priority remain separate;
- invalidated, expired and archived retain distinct meaning;
- reopening never bypasses admission and risk review;
- every active thesis has review, expiry and invalidation rules.
