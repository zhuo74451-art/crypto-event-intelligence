# Overnight Execution Protocol V1

## Purpose
Governs the deterministic, offline-repeatable execution of Lane E's research intelligence and continuous integration pipeline.

## Principles
1. **Deterministic** — Same inputs produce same outputs (run IDs, claim IDs, edge IDs)
2. **Idempotent** — Rerunning does not create duplicates
3. **Incremental** — Supports resume from last checkpoint
4. **Offline** — No network calls for business data
5. **Locked** — Producer SHAs are locked and verified before consumption

## Pipeline Order
```
Lane A (macro evidence)
  → Lane B (market data)
  → Lane C (strategy replay)
  → Lane D (validation)
  → Lane E (research intelligence)
```

## Gate Sequence
1. Lock & Hash Verification
2. Contract Compatibility
3. Single-Lane Tests
4. Cross-Lane Interface Integrity
5. End-to-End Real Sample
6. Kernel Seal Regression
7. Full Repository Matrix

## Prohibitions
- No silent SHA upgrades during a run
- No majority-vote conflict resolution
- No single-score evidence compression
- No deletion of opposing evidence or failed experiments
- No claiming causality from correlation
- No out-of-sample conclusions from in-sample results
