# Stage 1 Exit — Autonomous Responsibility Foundation

**Status:** Accepted  
**Stage:** Problem, responsibility and autonomy foundation

## True problem

The project must autonomously decide which crypto-market changes deserve machine attention, maintain evidence-backed theses over time, and reduce or stop attention when evidence no longer supports continued work.

## Accepted operating story

The system continuously receives approved evidence, resolves events, forms bounded interpretations, creates or updates theses, maps exposures, attacks its own reasoning, allocates attention, gathers follow-up evidence, changes lifecycle state, and remains silent unless a material change or governance exception occurs.

Routine human judgment is absent.

## Completed contracts

- product responsibility and owner role;
- broad discovery with strict active admission;
- judgment inventory J01 through J22;
- L0 through L3 authority model;
- Evidence, Thesis, Risk, Arbitration, Lifecycle and Resource Governor roles;
- legal thesis state machine;
- attention priorities, portfolio caps and review cadence;
- automatic no-change decay;
- notification, loop, checkpoint and recovery rules;
- typed claim, risk and mandatory-abstention rules;
- longitudinal replay, shadow, adversarial and recovery validation design;
- baseline, metric, threshold and stop rules.

## Action qualification

`BOUNDED`

The responsibility model is coherent enough to challenge prior art and audit the existing repository. It is not yet qualified for unattended production operation because implementation coverage and longitudinal evidence are absent.

## Claims this stage supports

- the intended product and owner role are explicit;
- normal-path AI judgments have declared owners and fallbacks;
- autonomous discovery, state changes and resource use have bounded policies;
- the design can be used as an audit standard.

## Claims this stage does not support

- the current code implements the design;
- the proposed agents or thresholds are optimal;
- the system improves market judgment in practice;
- the system is ready for unattended live operation;
- any strategy is profitable;
- trade or public-advice behavior is justified.

## Remaining uncertainty

The largest remaining uncertainty is not the conceptual architecture. It is whether existing code and mature external foundations can implement this responsibility with substantially less complexity and better reliability than a custom agent system.

## Next stage

Run an **External Prior Art Challenge and Existing Repository Responsibility Audit**:

1. identify mature components and methods for event sourcing, state machines, scheduling, evidence provenance, research agents, selective prediction, evaluation and observability;
2. challenge the proposed design with simpler alternatives;
3. inspect `main`, Draft PR #16, tests and runtime paths;
4. classify every relevant component as `RETAIN`, `ADAPT`, `QUARANTINE`, `REMOVE` or `MISSING`;
5. produce the smallest complete engineering route.

No feature implementation begins until this audit is accepted.
