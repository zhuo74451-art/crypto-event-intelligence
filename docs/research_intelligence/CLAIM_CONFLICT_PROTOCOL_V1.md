# Claim Conflict Protocol V1

## Principles

1. **Conflicts are preserved, not resolved by fiat** — When two claims contradict, both are retained. The conflict is documented with possible reasons (different sample, period, regime, measurement, method).

2. **No single-paper validation** — A single study does not make a claim `supported`. At minimum, independent replication is required.

3. **Regime-dependence is a valid resolution** — Both claims may be correct in different regimes. The conflict is marked `regime_dependent`.

4. **Unresolved is acceptable** — Many conflicts will remain unresolved indefinitely. This is a feature, not a bug.

## Conflict Types

| Type | Description |
|------|-------------|
| `direct_contradiction` | Claims directly oppose each other on the same question |
| `different_sample` | Same question, different populations |
| `different_period` | Same question, different time periods |
| `different_market` | Same question, different markets |
| `different_regime` | Same question, different regimes (valid resolution) |
| `different_measurement` | Claims use different variable definitions |
| `different_horizon` | Claims valid at different time horizons |
| `methodological_disagreement` | Different methods produce different results |
| `replication_failure` | Later study fails to replicate earlier finding |
| `scope_mismatch` | Claims address different sub-questions |
| `apparent_conflict` | Conflict resolves on closer inspection |

## How to Add a Conflict

1. Identify the two Claim IDs
2. Determine the conflict type
3. Document shared question and differences (sample, method, measurement, regime)
4. Set resolution status (honestly — `unresolved` if not resolved)
5. Add required research to resolve if needed

## What Not to Do

- Do NOT delete a claim because it conflicts with another
- Do NOT average conflicting effect sizes
- Do NOT let a summary generator silently conflate two contradictory findings
- Do NOT use citation counts or author reputation to resolve conflicts
