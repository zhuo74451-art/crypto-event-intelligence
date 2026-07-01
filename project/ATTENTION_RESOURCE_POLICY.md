# Attention, Resource and Notification Policy

**Status:** Active

Priority measures machine attention, not bullishness. A directionally unclear security or liquidity risk may be P0.

## Priorities

- `P0_IMMEDIATE` — material, time-sensitive, broad impact, not clearly priced, supported by qualified evidence.
- `P1_HIGH` — important with a near catalyst, high uncertainty-reduction value, or major risk-monitoring value.
- `P2_NORMAL` — valid and useful, but not urgent.
- `P3_LOW` — long horizon, weak marginal value, or waiting for a distant catalyst.
- `DORMANT` — no active research except named triggers or periodic requalification.

## Conservative portfolio caps

Initial limits are intentionally bounded:

- active theses: 40 maximum;
- P0: 3 maximum;
- P1: 10 maximum;
- P2: 17 maximum;
- P3: 10 maximum;
- qualifying candidates: 100 maximum.

Discovery records may exceed the candidate cap but cannot receive semantic deep work until capacity exists.

When capacity is full, the Resource Governor downgrades or evicts the thesis with the lowest marginal attention value before admitting another. Limits are never silently exceeded.

## Review cadence

Event-triggered review has priority. Time-based review is the fallback.

- P0: qualified evidence change, otherwise within 4 hours during the active window;
- P1: catalyst or material evidence change, otherwise within 12 hours;
- P2: material evidence change, otherwise within 48 hours;
- P3: named trigger, otherwise within 7 days;
- Dormant: named trigger or 30-day requalification.

A delayed review records the delay and cause.

## No-change decay

- first consecutive no-change: keep priority and interval;
- second: double the interval;
- third: downgrade one priority level;
- fifth: move to Dormant or Archived unless a named catalyst is still pending.

A named catalyst may suspend decay only until its deadline. The counter resets only when new evidence changes a material field, not when a model rewrites the same interpretation.

## Per-review limits

One review cycle may use at most:

- 3 evidence-retrieval rounds;
- 2 semantic evaluation passes;
- 1 risk-and-arbitration retry;
- 5 internal state transitions.

If unresolved, the system abstains, lowers priority or schedules another review. It does not continue reasoning indefinitely.

## Notification policy

### Immediate

- activation of a new P0 thesis;
- invalidation of a P0 or P1 thesis;
- movement by two or more priority levels;
- new broad cross-asset or infrastructure risk;
- governance, security, privacy or unrecoverable health exception.

### Batched

- P1 creation or material revision: daily digest;
- P2 material revision: daily or weekly digest according to volume;
- P3: only on promotion, learning-bearing invalidation, or archive summary.

No notification is sent for duplicate evidence, routine no-change review, low-value expiry or ordinary agent disagreement.

## Graceful degradation

When resources tighten, the system reduces work in this order:

1. stop new deep qualification;
2. suspend P3 work;
3. reduce P2 review frequency;
4. preserve P0 and P1 maintenance;
5. preserve state integrity, audit records and stop controls above all analysis work.

Budget exhaustion stops new work and persists current state. It does not erase pending reviews.

## Loop and recovery

- identical evidence and state signatures twice in one run terminate the loop;
- malformed structured output receives one repair attempt, then deterministic fallback;
- up to two approved source fallbacks may be tried before scope is reduced;
- a valid checkpoint is written before every lifecycle transition;
- transition failure rolls back to the last valid revision;
- three consecutive recovery failures create a governance exception;
- shutdown leaves every thesis in a valid state with pending reviews persisted.

## Resource accounting

Every thesis records:

- current priority;
- no-change count;
- retrieval rounds;
- semantic passes;
- retry count;
- last review and next review;
- resource-limit reason when work is delayed or stopped.

## Acceptance

- portfolio and per-review caps are enforceable;
- repeated no-change reduces attention automatically;
- resource exhaustion degrades lower-priority work first;
- notification volume remains sparse and material;
- every loop terminates, defers or stops safely;
- restart preserves state and pending review intent.
