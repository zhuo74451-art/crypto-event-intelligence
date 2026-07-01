# Stage 2 Responsibility Coverage Matrix

**Status:** Pass 1

| Accepted responsibility | Current evidence | Coverage | Classification | Intended owner |
|---|---|---:|---|---|
| Approved broad-recall input | Curated provider and feed protocol | Partial | ADAPT | acquisition adapter |
| Public market context | Hyperliquid and CCXT read-only adapters | Partial | ADAPT | market adapter |
| Source health and provenance | Adapter envelopes and source-health history | Partial | ADAPT | Evidence Gate and app DB |
| Source fact permission | PR #16 authority and permission fields | Weak | ADAPT | Evidence Gate |
| Point-in-time time model | timestamps and some leakage checks | Partial | ADAPT | Evidence Gate |
| Artifact integrity | SHA-256 verification exists | Partial | ADAPT | Evidence Gate |
| Entity identity | asset and entity strings only | Weak | MISSING | Evidence Gate |
| Exact duplicate handling | duplicate IDs and exact dedup keys | Partial | ADAPT | Event Builder |
| Non-exact event relationships | title/time fuzzy grouping | Unsafe | QUARANTINE | candidate linker only |
| Conflict preservation | SourceConflict records | Partial | ADAPT | Event Builder |
| Immutable event revisions | SQLite revision intent | Weak | ADAPT | SQLAlchemy ledger |
| Persistent thesis object | no canonical thesis record | None | MISSING | app DB |
| Thesis revisions across runs | no persistent lifecycle | None | MISSING | app DB and lifecycle service |
| Mechanism reasoning | keyword transmission strings | Unsafe | REMOVE | Thesis Synthesis pass |
| Genuine exposure mapping | asset lists without proof | Weak | MISSING | Thesis Synthesis plus gates |
| Horizon-separated direction | absent from active pipeline | None | MISSING | Thesis Synthesis |
| Prior expectation | arithmetic helpers and fixture records | Partial | ADAPT | Candidate Builder |
| Priced-in reasoning | fixed pre-move thresholds | Weak | QUARANTINE | Thesis Synthesis and Risk Challenge |
| Counterevidence and falsification | scattered fields, no active challenge | Weak | MISSING | Risk Challenge |
| Claim-level abstention | four coarse abstention conditions | Weak | REMOVE and replace | deterministic arbitration |
| Evidence-status bands | numeric confidence averages instead | None | MISSING | arbitration and output contracts |
| Active admission gates | any eligible strategy may activate watch | Unsafe | REMOVE | deterministic arbitration |
| Legal lifecycle transitions | event statuses and ad hoc transitions | Unsafe | REMOVE and replace | transition service |
| Attention priority and caps | absent | None | MISSING | Resource Governor |
| Scheduled follow-up reviews | bounded synchronous loop only | None | MISSING | DBOS workflow |
| No-change decay | absent | None | MISSING | lifecycle service |
| Material notification policy | older alert candidates, not thesis policy | Weak | ADAPT | notification service |
| Durable workflow recovery | file lock, stop marker and finite loop | Weak | QUARANTINE | DBOS |
| Operator status and inspection | workbench doctor, run, inspect and manifests | Partial | ADAPT | operator CLI |
| Schema migrations | manual SQLite migration strings | Weak | ADAPT | Alembic |
| Resource accounting | some run counts and adapter latency | Weak | ADAPT | DBOS, app DB and OpenTelemetry |
| Traces and metrics | no OpenTelemetry | None | MISSING | observability adapter |
| Point-in-time replay | fixture mode and as-of checks | Partial | ADAPT | evaluation runner |
| Accepted baselines | incomplete and incorrectly named metrics | Unsafe | REMOVE | evaluation runner |
| Calibration | confidence buckets without outcomes | Unsafe | REMOVE | held-out evaluator |
| Longitudinal Shadow | one-shot and finite batch only | None | MISSING | DBOS shadow workflow |
| Recovery injection tests | limited transaction and runner tests | Weak | ADAPT | adversarial harness |
| Governance exceptions | stop marker and error statuses only | Weak | ADAPT | Resource Governor and operator CLI |

## Coverage conclusion

The repository has useful acquisition, read-only safety, evidence, exact-dedup, fixture, operator and run-audit material. It does not yet contain the central product capability: a persistent, durably reviewed, risk-challenged thesis portfolio.

The first implementation route should reuse boundary and operator assets while replacing the cognition path rather than extending the one-shot packet pipeline.
