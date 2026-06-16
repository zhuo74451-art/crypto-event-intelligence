# Protocol 09: Noise Gate Shadow Audit and Pilot Execution

**对应决策: 9, 10**

## Shadow Audit

The Legacy Noise Gate's pass/reject decisions MAY be used for a shadow audit comparing its outputs against Research Eligibility decisions. This is observational only:

- Legacy Noise Gate production semantics are NOT modified
- Research Eligibility is determined independently
- Shadow audit results inform future Noise Gate design
- No automatic feedback loop from Research to Noise Gate

## Pilot Execution

Phase 0 seals the protocol package. Pilot execution will:

1. Run Candidate Processing
2. Assign Research Eligibility
3. Pre-register Eligible Units
4. Collect Price Outcomes
5. Assess Interference
6. Produce Attribution Assessments
7. Generate Pilot Report

Each step must be completed before the next begins. No skipping.

## Prohibitions During Pilot

- No modifying protocol mid-pilot
- No removing already-registered units
- No outcome-based parameter tuning
- No adding Development Set results to Pilot statistics
- No trading decisions
- No causal proof claims
