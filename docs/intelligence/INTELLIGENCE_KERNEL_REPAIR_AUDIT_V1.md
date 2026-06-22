# Intelligence Kernel Repair Audit V1

## Scope

Full audit of the Intelligence Kernel Foundation V1 prototype against the
repair requirements. Each finding references the specific code location
and confirms whether it has been fixed.

## P0 Findings

### P0-1: Arbitration Vote Counting [FIXED]

**Location:** `market_radar/intelligence/engines/arbitration.py` lines 137-141 (original)

**Original issue:** Direction determined by `len(supporting) > len(opposing)`.

**Fix:** Complete rewrite of `_assess_horizon()` using explicit rule IDs
(ARB-001 through ARB-013). Direction is determined by rule-based logic,
not vote counting. Evidence quality, regime fit, and market confirmation
are now evaluated. Verified in test `test_arbitration.py` — three weak
bullish hypotheses no longer override one strong bearish.

### P0-2: Evidence/Regime Not Used in Eligibility [FIXED]

**Location:** `market_radar/intelligence/engines/arbitration.py` lines 79-87 (original)

**Original issue:** `_is_eligible()` only checked hypothesis status.

**Fix:** Complete `_eligibility_pipeline()` with 12 checks (E01-E12)
including evidence state, regime state, required inputs, horizon validation,
and strategy lifecycle state.

### P0-3: Ineligible List Mixes Objects and Strings [FIXED]

**Location:** `market_radar/intelligence/engines/arbitration.py` lines 40-49 (original)

**Original issue:** Hypothesis objects and string reasons appended to same list.

**Fix:** Introduced `EligibilityDecision`, `EligibleHypothesis`, `IneligibleHypothesis`
as structured types. `ArbitrationOutput.ineligible_hypotheses` is now `list[IneligibleHypothesis]`
with full trace information.

### P0-4: Evidence Resolver False Conflict Detection [FIXED]

**Location:** `market_radar/intelligence/engines/evidence_resolver.py` lines 53-59 (original)

**Original issue:** Different claim strings inferred as conflicting evidence.

**Fix:** Conflict detection now requires:
1. Same `claim_key` across items
2. Contradictory `Stance` values (SUPPORTS vs CONTRADICTS)
3. At least one primary source or multiple items

Structured claim fields: `claim_key`, `claim_subject`, `claim_predicate`,
`claim_value`, `stance`.

### P0-5: Staleness Declared But Not Implemented [FIXED]

**Location:** `market_radar/intelligence/engines/evidence_resolver.py` lines 30-31 (original)

**Original issue:** `max_staleness_days=30` stored but never checked.

**Fix:** Implemented `StalenessPolicy` with 6 modes:
- `never_expires` — evidence never decays
- `age_from_published_at` — calculated from publication time
- `age_from_updated_at` — calculated from last update
- `age_from_retrieved_at` — calculated from retrieval time
- `explicit_expires_at` — absolute expiry timestamp
- `event_state_dependent` — controlled by event state

Resolver signature now includes `as_of_time` parameter.

### P0-6: Event State Machine Overly Permissive [FIXED]

**Location:** `market_radar/intelligence/engines/event_state_machine.py` (original)

**Original issues:**
- Revision/Correction always allowed and changed state
- No idempotency detection
- Input event mutated in-place
- String time comparisons

**Fixes:**
- Revision/Correction no longer change state by default
- `STATE_CORRECTION` transition type requires `force_state_change=True`
- Idempotent detection: identical transitions return `idempotent=True`
- Pure function: `transition()` returns new EventEntity, input unchanged
- All time comparisons use `utc_parse()` for aware datetime
- `EventTransitionResult` with updated event, transition, and trace

## P1 Findings

### P1-1: Unstable IDs [FIXED]

**Original:** `bundle_{len(items)}`, `arb_{len(hypotheses)}`

**Fix:** 
- Evidence bundle: `evb_{sha256(sorted evidence IDs)[:24]}`
- Arbitration: `arb_{sha256(asset|sector|count)[:24]}`
- Both are deterministic and content-dependent

### P1-2: Manifest final_sha [FIXED]

Manifest updated to use `implementation_head_sha` and
`manifest_parent_sha` instead of impossible self-referencing `final_sha`.

### P1-3: Broken Documentation Links [FIXED]

**Location:** `docs/ARCHITECTURE.md`

**Fix:** Empty parentheses and "See ." replaced with valid markdown
references to `market_radar/intelligence/` and
`docs/intelligence/INTELLIGENCE_KERNEL_FOUNDATION_V1.md`.

### P1-4: Execution Log [ADDRESSED]

New repair execution log created. Original log limitations noted.

### P1-5: Test Baseline [ADDRESSED]

Test matrix script created at `scripts/run_repository_test_matrix.py`.
Baseline testing pending execution across three states.
