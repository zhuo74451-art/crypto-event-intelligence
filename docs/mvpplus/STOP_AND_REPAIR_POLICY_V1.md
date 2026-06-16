# Stop & Repair Policy v1 — MVP+

## Stop Conditions

A lane MUST stop and report BLOCKED when:

1. **Permission failure** — requires access to unauthorized path, API, or secret
2. **Contract contradiction** — contract requirement conflicts with itself
3. **Production write risk** — code would modify production data/services
4. **Credential exposure** — code would read or expose secrets
5. **Fund/trading risk** — code would touch funds, signatures, or trading endpoints
6. **Git baseline unsafe** — cannot determine safe baseline commit
7. **Outside project boundaries** — requires access to files outside approved roots

## Non-Blocking (Resolve and Continue)

The following are NOT stop conditions:

| Issue | Resolution |
|-------|-----------|
| Path discrepancy | Correct path, record in evidence |
| Package version mismatch | Install/update, verify compatibility |
| API field changes | Adapt to response, degrade gracefully |
| Single request failure | Retry with backoff, degrade if persistent |
| Incomplete fixture | Complete fixture, continue offline logic |
| Test failure | Fix lane's own code, document pre-existing |
| Single source timeout | Degrade source, continue with other sources |

## Repair Budget

| Attempt | Action |
|---------|--------|
| 1st failure | Diagnose root cause |
| 2nd failure (same issue) | Use substantially different safe approach |
| Still fails | Stop blind attempts. Choose: fixture, degrade, minimal blocker report, change request |

## Automatic Repair Constraints

Each lane has max **2 repair rounds**.

Repair messages must be delta-only:
- repair_id
- original_task_id
- current_commit
- failed_acceptance
- evidence
- allowed_change
- forbidden_change
- expected_proof

**Never** resend full project background or charter.

After 2 failed rounds → escalate to Lane 6.

## NO_NEW_EVIDENCE Rule

Each round must produce ≥1 new evidence item:
- code diff
- test result
- API response
- narrowed root cause
- artifact
- verified repo fact

Two consecutive rounds with no new evidence → NO_NEW_EVIDENCE → stop.
