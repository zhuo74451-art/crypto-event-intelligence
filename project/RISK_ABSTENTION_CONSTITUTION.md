# Risk and Abstention Constitution

**Status:** Active

The system is allowed to narrow, defer or abstain. It is not allowed to manufacture certainty.

## Claim classes

Claims are separated so evidence for one class cannot silently authorize another:

- `FACT` — what a qualified source directly establishes;
- `EVENT_STATE` — confirmed, partial, disputed, unconfirmed or retracted;
- `MECHANISM` — how the event could affect market variables;
- `EXPOSURE` — which assets, sectors or structures are genuinely connected;
- `DIRECTION` — positive, negative, mixed or unclear by horizon;
- `PRICED_IN` — unpriced, partial, largely priced, possible overreaction or unavailable;
- `ATTENTION_ACTION` — activate, observe, risk-only, mechanism-candidate, abstain or reject.

The maximum claim is limited by the weakest required gate.

## Evidence thresholds

- A qualified primary source may establish a direct fact about itself or its official action.
- A third-party report cannot establish facts outside its source permission without corroboration.
- A mechanism claim requires an explicit causal chain, assumptions and missing links.
- A directional claim requires a defensible mechanism, genuine exposure, horizon, counterevidence review and relevant market context.
- A priced-in claim requires pre-event expectation and market-response evidence; price movement alone is insufficient.
- Attention action may be taken with uncertainty, but it must preserve the narrower claim class.

## Confidence representation

No unsupported numerical confidence is shown.

Each claim carries one evidence status:

- `BLOCKED` — prohibited by identity, permission, time or integrity failure;
- `INSUFFICIENT` — required evidence or reasoning link is missing;
- `TENTATIVE` — a defensible interpretation exists but important uncertainty remains;
- `SUPPORTED` — evidence and counterevidence review support the bounded claim;
- `STRONG` — multiple independent evidence paths support the claim and no material unresolved contradiction remains.

These bands are calibrated later against real outcomes. They are not model self-ratings.

## Mandatory abstention

The system must abstain from the affected claim when any required condition holds:

- unresolved entity identity or impersonation risk;
- invalid source permission, provenance or timestamp integrity;
- possible future-data leakage;
- no defensible causal mechanism;
- no genuine exposure for the named asset or theme;
- decisive evidence is missing or stale;
- material contradiction remains unresolved;
- the Risk Agent review is missing or malformed;
- direction differs across horizons and cannot be represented separately;
- market context is unavailable for a priced-in claim;
- manipulation, liquidity or data-quality risk exceeds the claim authority;
- the review budget is exhausted before qualification completes.

Abstention from direction does not require discarding a valid fact, event, risk observation or mechanism candidate.

## Hard vetoes

Only deterministic L0 failures and direct failure of a necessary thesis premise are hard vetoes.

The Risk Agent cannot veto through unsupported opinion. It must cite counterevidence, an alternative explanation, a hidden assumption or a falsification condition.

## Disagreement

Disagreement is preserved by component:

- fact disagreement;
- mechanism disagreement;
- exposure disagreement;
- horizon disagreement;
- priced-in disagreement;
- lifecycle disagreement.

The system does not average incompatible claims into one score. Arbitration narrows the claim, lowers priority, keeps competing hypotheses, or abstains.

## Output constraints

An owner-facing assessment must state:

- claim class and evidence status;
- supported conclusion;
- what remains unknown;
- strongest alternative explanation;
- horizon and exposure scope;
- next evidence and review condition;
- invalidation condition;
- lifecycle and attention action.

It must not produce entries, exits, leverage, sizing, return promises or a disguised trade instruction.

## Risk dimensions

Every active thesis tracks separately:

- fact and source risk;
- interpretation and causal risk;
- exposure mismatch;
- horizon mismatch;
- market, liquidity and crowding risk;
- priced-in risk;
- manipulation and data-quality risk;
- model and agent process risk;
- resource and staleness risk;
- behavioral misuse risk.

A single composite risk score may be used only for ordering work, never to hide a failed hard gate.

## Learning boundary

A wrong outcome does not automatically prove the original reasoning was invalid, and a correct outcome does not automatically prove it was valid. Learning must distinguish:

- evidence error;
- mechanism error;
- exposure error;
- timing error;
- priced-in error;
- calibration error;
- process or recovery error;
- outcome variance not attributable to the thesis.

A global rule changes only after repeated or high-severity evidence and regression review.

## Acceptance

- every claim is typed and bounded;
- abstention may occur at one claim layer without erasing lower-layer facts;
- L0 failures block affected claims;
- disagreement remains visible;
- numerical confidence is not emitted before calibration evidence exists;
- every active direction claim includes mechanism, exposure, horizon, counterevidence and invalidation.
