# Longitudinal Validation Plan

**Status:** Active

## What validation must prove

The project is not trying to prove trading profitability. It must prove that an unattended thesis portfolio:

- identifies decision-relevant changes;
- rejects weak or unsupported claims;
- maintains theses correctly over time;
- changes its mind when decisive evidence appears;
- allocates machine attention better than simpler alternatives;
- keeps notifications sparse and useful;
- respects time, resource, state and authority boundaries.

## Evaluation design

Validation has three ordered layers.

### Layer A — Point-in-time replay

Use at least 120 historical event cases across multiple market regimes and domains. Every case is reconstructed from evidence available at the original assessment time. Later outcomes are hidden until scoring.

Required controls:

- immutable evidence manifest;
- publication, effective, first-seen, retrieval and assessment timestamps;
- no future evidence in inference;
- sequential or walk-forward evaluation rather than random mixing;
- frozen prompts, rules and model versions per evaluation run;
- all attempted variants recorded to prevent cherry-picking.

### Layer B — Bounded unattended shadow

Run for at least 21 calendar days and at least 100 qualified cases; both conditions must be met.

The system receives approved live inputs, maintains thesis state, performs follow-up reviews and records notifications without publishing externally or taking market action.

### Layer C — Adversarial and recovery evaluation

Inject:

- duplicate and conflicting sources;
- delayed and corrected reports;
- stale market evidence;
- entity ambiguity and impersonation;
- malformed model output;
- source outage;
- budget exhaustion;
- restart during a lifecycle transition;
- repeated no-change reviews;
- decisive invalidation evidence.

## Baselines

The autonomous system is compared against:

1. `EVENT_ONLY` — ranks events by source and apparent importance without persistent theses;
2. `PRICE_ONLY` — ranks assets by price, volume and volatility changes;
3. `ONE_SHOT` — generates one analysis when the event appears but does not maintain a lifecycle;
4. `ALWAYS_NEUTRAL` — never forms a directional claim;
5. `FORCED_JUDGMENT` — must output a direction even when evidence is weak.

The system must beat simpler baselines on cognition and attention value, not merely produce richer text.

## Primary metrics

### Integrity gates

These are pass/fail:

- future-data leakage: 0;
- semantic override of L0 prohibition: 0;
- illegal lifecycle transition: 0;
- unauthorized external side effect: 0;
- lost or irrecoverable thesis revision: 0;
- silent resource-cap breach: 0.

Any failure blocks advancement until repaired and rerun.

### Judgment quality

- important-event recall;
- active-thesis admission precision;
- weak-evidence rejection rate;
- mechanism and exposure correctness;
- horizon separation quality;
- unsupported directional-claim rate;
- priced-in classification quality;
- abstention precision and coverage;
- false-confidence rate;
- invalidation and downgrade latency;
- useful reopening precision.

### Attention and operations

- material revisions per semantic pass;
- duplicate research avoided;
- percentage of active attention spent on P0 and P1;
- no-change reviews before downgrade;
- owner notification precision;
- mean time to recover;
- successful checkpoint recovery rate;
- cost and resource use per accepted material revision.

## Initial acceptance thresholds

Thresholds are provisional and must be changed only through a recorded evaluation decision.

- weak-evidence rejection: at least 90%;
- unsupported directional claims: no more than 5%;
- duplicate active-thesis creation: no more than 2%;
- decisive invalidation recognized within one scheduled review: at least 80%;
- material owner-notification precision: at least 75%;
- active-thesis admission precision: at least 70%;
- successful recovery from injected recoverable failures: at least 95%;
- attention precision must exceed `EVENT_ONLY` and `ONE_SHOT` by at least 10 percentage points on the same case set;
- forced-judgment error must be materially higher than the system's accepted-claim error, demonstrating useful abstention;
- all integrity gates must be perfect.

No threshold proves profitability or universal market understanding.

## Calibration

The five evidence-status bands in the Risk and Abstention Constitution are scored by observed correctness and revision outcomes.

A band is acceptable only when stronger bands show monotonically better correctness and lower invalidation rates than weaker bands. Numerical probabilities may be introduced only after held-out calibration evidence exists.

Coverage and error are evaluated together: reducing errors by abstaining on almost everything is not success.

## Anti-overfitting rules

- evaluation cases are time-ordered;
- outcome windows do not overlap training or tuning windows without purging or gaps;
- prompt, rule and threshold variants are logged;
- the final acceptance set is not used for tuning;
- results are reported across regimes and domains, not only as one average;
- one favorable historical path cannot authorize operation;
- live shadow results outrank retrospective replay for operational trust.

## Continue, change, reduce or stop

### Continue to repository audit and implementation planning

Proceed when the responsibility contracts are complete and the evaluation design is executable without unresolved owner policy.

### Continue from shadow to owner-facing operation

Proceed only when integrity gates pass, minimum thresholds are met, and the system beats meaningful baselines without excessive abstention or resource use.

### Change

Change the relevant role, evidence path, policy or threshold when value exists but a bounded component fails.

### Reduce scope

Remove autonomous discovery, directional judgment, priced-in reasoning or other layers that fail to beat simpler baselines after one controlled repair cycle.

### Stop

Stop the affected autonomous path when it repeatedly:

- bypasses hard evidence gates;
- creates unsupported certainty;
- cannot terminate or recover safely;
- consumes more attention than the value of its revisions;
- fails to outperform the simpler baseline responsible for the same result.

## Required artifacts

- case and evidence manifests;
- frozen run configuration;
- complete thesis revision histories;
- baseline outputs;
- integrity-gate report;
- metric report by domain and regime;
- error and abstention review;
- resource accounting;
- recovery report;
- continue, change, reduce or stop decision.
