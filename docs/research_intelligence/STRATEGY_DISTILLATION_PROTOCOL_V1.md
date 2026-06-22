# Strategy Distillation Protocol V1

## Overview

The strategy distillation pipeline converts raw research material (traders, papers, projects) into structured, auditable strategy candidates for external validation.

```
Trader/Paper/Project material
    → Research Claim extraction
    → Claim quality assessment
    → Conflict/gap identification
    → Strategy Seed formation
    → Seed completeness check (StrategySeedCompiler)
    → Strategy Candidate compilation (StrategyCandidateCompiler)
    → Validation specification
    → Handoff to validation track
```

## Rules

### 1. Claims First
Every Strategy Seed must be grounded in at least one Research Claim. Claims must have Source Records.

### 2. Counter-Evidence Required
Every Strategy Seed must reference counter-claims or knowledge gaps. A strategy with no downsides is incomplete.

### 3. Abstention Logic Required
Every Strategy Seed must specify when to abstain. A strategy that always has a view is not a strategy; it's a bias.

### 4. Invalidation Conditions Required
Every Strategy Seed must specify conditions that invalidate the thesis. Without invalidation, the strategy cannot be falsified.

### 5. No Persona Mimicry
Strategy Seeds capture variable combinations, triggers, confirmations, and risk controls — not trader personalities. No "This is how Trader X would think."

### 6. No Performance Claims
Strategy Seeds and Candidates must NOT contain:
- win_rate, sharpe, expected_return, production_probability
- Trader self-reported returns
- Unverified backtest results

### 7. Production Guard
All Seeds and Candidates have `production_eligible: false`. Only external validation can change this status.

## Compiler Role

The StrategySeedCompiler and StrategyCandidateCompiler are DETERMINISTIC — they check completeness and flag missing fields. They do NOT:
- Fill in missing logic
- Generate abstention conditions
- Create claims
- Rank strategies
- Approve production use
