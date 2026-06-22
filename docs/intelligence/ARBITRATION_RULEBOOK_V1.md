# Arbitration Rulebook V1

## Rule Format

Each rule has an ID (ARB-NNN), description, condition, output verdict, and
rationale. Rule IDs are referenced in decision traces.

## Rules

### ARB-001: No Eligible Hypotheses

```
Condition: No hypotheses pass the eligibility pipeline.
Output: INSUFFICIENT_EVIDENCE
Rationale: Without any eligible hypothesis, no direction can be determined.
```

### ARB-002: Only Awaiting Confirmation

```
Condition: All eligible hypotheses lack market confirmation.
Output: WAIT_FOR_CONFIRMATION
Rationale: Directional bias without market confirmation is speculation.
```

### ARB-003: Direction Consistent with Complete Evidence Chain

```
Condition: At least one direction has strong evidence and the opposing
           direction does not.
Output: DIRECTIONAL_AVAILABLE with the supported direction
Rationale: One side has verified evidence without credible contradiction.
```

### ARB-004: Weak Consensus vs Strong Counter-Evidence

```
Condition: Multiple weak same-origin hypotheses on one side vs a single
           strong independent hypothesis on the other.
Output: DIRECTIONAL_AVAILABLE towards the strong side
Rationale: Quality > quantity. Strong independent evidence overrides
           weak consensus.
```

### ARB-005: Both Sides Have Strong Evidence

```
Condition: Both directions have independent strong evidence.
Output: CONFLICT_UNRESOLVED
Rationale: Two strong opposing views are a genuine conflict, not
           resolvable by vote count.
```

### ARB-006: One Side Strong, Opposite Side Only Ineligible

```
Condition: One direction has strong evidence, the opposing direction has
           only ineligible hypotheses (with documented reasons).
Output: DIRECTIONAL_AVAILABLE with ineligible reasons preserved
Rationale: Strong evidence is not contradicted by ineligible hypotheses.
```

### ARB-007: Evidence Bundle Conflicting

```
Condition: The evidence bundle itself has conflicting verdict.
Output: CONFLICT_UNRESOLVED or INSUFFICIENT_EVIDENCE
Rationale: Conflicting evidence prevents any directional conclusion.
```

### ARB-008: Regime Not Applicable

```
Condition: Current market regime is in the strategy's invalid_regimes list.
Output: Hypothesis is INELIGIBLE (E08)
Rationale: Strategy known to be ineffective in this regime.
```

### ARB-009: Missing Required Inputs

```
Condition: Strategy's required_inputs are not available.
Output: Hypothesis is INELIGIBLE (E05)
Rationale: Cannot evaluate strategy without required data.
```

### ARB-010: Only Derivatives Confirmation

```
Condition: Only derivatives-based confirmation available, no spot/on-chain.
Output: WAIT_FOR_CONFIRMATION (unless Strategy Pack explicitly allows)
Rationale: Derivatives-only moves can be liquidations/positioning, not
           genuine directional conviction.
```

### ARB-011: Direction Consistent but Transmission Mutually Exclusive

```
Condition: Hypotheses agree on direction but have incompatible
           transmission signatures.
Output: CONFLICT_UNRESOLVED or WAIT with conflict noted
Rationale: Same direction through different mechanisms may indicate
           different underlying causes.
```

### ARB-012: Different Time Scales Opposite

```
Condition: Opposite directions at different time horizons.
Output: Separate assessments, not a conflict.
Rationale: Short-term bullish and long-term bearish are different
           judgments, not contradictions.
```

### ARB-013: No Calibration Artifact

```
Condition: No calibration artifact available for any hypothesis.
Output: Directional allowed but confidence limited to qualitative/
         uncalibrated_score, not calibrated_probability.
Rationale: Without calibration, confidence is unverified.
```

## Eligibility Checks (E01-E12)

| ID | Check | Failure Code |
|----|-------|-------------|
| E01 | Contract valid (has hypothesis_id) | CONTRACT_VALID |
| E02 | Asset scope matches | ASSET_SCOPE_MISMATCH |
| E03 | Horizon recognized | HORIZON_UNRECOGNIZED |
| E04 | Strategy state eligible | STRATEGY_STATE_INELIGIBLE |
| E05 | Required inputs available | REQUIRED_INPUTS_MISSING |
| E06 | Evidence minimum met | EVIDENCE_MINIMUM_NOT_MET |
| E07 | Evidence not conflicting | EVIDENCE_CONFLICTING |
| E08 | Regime not invalid | REGIME_INVALID |
| E09 | Hypothesis not expired | HYPOTHESIS_EXPIRED |
| E10 | Invalidation not triggered | INVALIDATION_TRIGGERED |
| E11 | Confidence representation valid | CONFIDENCE_INVALID |
| E12 | Transmission references valid | TRANSMISSION_INVALID |
