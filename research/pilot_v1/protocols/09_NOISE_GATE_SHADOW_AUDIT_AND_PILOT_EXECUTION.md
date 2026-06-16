# Protocol 09: Noise Gate Shadow Audit and Pilot Execution

**对应决策: 9, 10**

## Shadow Audit

The Legacy Noise Gate's pass/reject decisions MAY be used for a shadow audit comparing its outputs against Research Eligibility decisions. This is observational only:

- Legacy Noise Gate production semantics are NOT modified
- Research Eligibility is determined independently
- Shadow audit results inform future Noise Gate design
- No automatic feedback loop from Research to Noise Gate

### Shadow Audit (Decision 9)

- Maintain complete Candidate Log for every candidate processed during Pilot
- Outcome data must NOT participate in candidate selection (no outcome-based sampling)
- Human reference labels must be blinded (reviewers must not see each other's labels)
- Shadow audit requires at least two reviewers: Reviewer A and Reviewer B
- Disagreements between reviewers enter adjudication process
- Missing data must be marked as "unknown" or "manual_review" — not assumed absent
- Performance must NOT be summarized by a single aggregate accuracy metric (different error types have different costs)
- Shadow audit is observational only — does NOT modify Legacy Noise Gate

### Calibration Pilot (Decision 10)

- Duration: 14 consecutive natural days
- If fewer than 8 registered cases by day 14: one 7-day extension is permitted (pre-registered, one time only)
- Must capture at least 3 different main event families
- Pipeline: Candidate Capture → Blinded Dual Review → Adjudication & Registration Lock → Outcome Reveal → Attribution Assessment
- All deviations must be documented (no silent deletions)
- Every Registration record includes: git commit hash + file SHA256 lock
- Pilot does NOT require positive attribution conclusions — all verdicts are valid outcomes

## Prohibitions During Pilot

- No modifying protocol mid-pilot
- No removing already-registered units
- No outcome-based parameter tuning
- No adding Development Set results to Pilot statistics
- No trading decisions
- No causal proof claims
