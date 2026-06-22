# Research Intelligence Architecture V1

## Why This Is Not a Knowledge Base

A traditional knowledge base stores and retrieves documents. This Research Intelligence system is different:

1. **Claims, not documents** — Each research item becomes a structured Claim Card with type, method, sample period, and quality decomposition. Documents are tracked as Source Records, not stored as full text.

2. **Conflict-first** — Contradictory evidence is preserved as a first-class object (ClaimConflict). Conflicts are not resolved by majority vote, summarization, or ignoring dissenting views.

3. **Knowledge gaps are tracked** — What we don't know is explicitly recorded as KnowledgeGap objects. These drive hypothesis generation.

4. **Decay-aware** — KnowledgeDecayRecords track when and why previously-valid claims may have expired due to market structure changes.

5. **Deterministic compilation** — Strategy Seeds are compiled through deterministic checks (StrategySeedCompiler, StrategyCandidateCompiler), not LLM generation. Missing fields are flagged, not hallucinated.

6. **Provenance validation** — Every Claim must trace to a Source Record. Every Strategy Seed must trace to Claims. Circular provenance is detected and rejected.

## Entity Relationships

```
Source Record
    ↓ (referenced by)
Research Claim ← → Claim Conflict (pairs of Claims)
    ↓ (supports/opposes)
Research Hypothesis ← Knowledge Gap (identifies unknowns)
    ↓ (supports)
Strategy Seed
    ↓ (compiled into)
Strategy Candidate
    ↓ (handed to validation)
External Validation Track
```

## Boundaries

### Research Layer vs Runtime Kernel

- **Research produces:** `ResearchStrategySeed`, `StrategyCandidateProposal`, `ResearchHypothesis`
- **Kernel owns:** `StrategyPack`, `MarketHypothesisInstance`, `ConfidenceStatement`, `ArbitrationEngine`
- **Mapping:** Through `KERNEL_INTEGRATION_REQUEST_V1.md` adapter specification
- **Constraint:** All research objects have `production_eligible: false`

### Research Layer vs Acquisition Layer

- **Research stores:** URL, DOI, metadata, structured summaries (never copyrighted full text)
- **Acquisition handles:** HTTP fetching, RSS, web archiving, change detection
- **Mapping:** Through `ACQUISITION_REQUIREMENTS_V1.md`

### Research Layer vs Validation Track

- **Research specifies:** `testable_hypothesis`, `required_dataset`, `required_label`, `required_baseline`, `required_holdout`, `known_leakage_risks`
- **Validation handles:** Historical out-of-sample testing, shadow validation, performance measurement
- **Constraint:** No strategy is validated by the research layer itself

## Promotion Flow

```
Claim: background → candidate → supported/mixed/contradicted → stale/retracted
Hypothesis: proposed → specification_ready → validation_ready → under_test → supported/rejected/mixed
Strategy Seed: unverified → research_ready → specification_ready → validation_ready → rejected/stale
Strategy Candidate: unvalidated → data_blocked → validation_ready → under_external_validation → rejected
```

No object reaches `production` status through the research layer.
