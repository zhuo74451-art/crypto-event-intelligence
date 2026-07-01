# Cognition Spine V1 - Integration Report

Run: COGNITION-SPINE-INTEGRATION-LAUNCH-001
Terminal State: COGNITION_SPINE_PARTIAL

Repair Issue: #17
PR: #16
Branch: workbench/cognition-spine-v1

## Architecture

The orchestrator (market_radar/cognition/orchestrator.py) connects all stages:

1. Input validation -> event grouping -> EventStore
2. Expectation state -> market snapshot windows -> confirmation rules
3. Lifecycle transition -> transmission paths -> assessment/abstention
4. Evidence synthesis -> output files

## 6 End-to-End Case Results

| Case | Events | Assessments | Abstentions | Contradicted |
|------|--------|-------------|-------------|--------------|
| Regulatory surprise | 1 | 1 | 0 | 0 |
| Macro release | 1 | 1 | 0 | 1 |
| Security incident | 2 | 2 | 0 | 1 |
| Software release | 1 | 0 | 1 | 0 |
| Duplicate cross-source | 1 | 1 | 0 | 0 |
| Ambiguous dates | 2 | 0 | 2 | 0 |

Total: 3 abstentions, 2 contradicted cases.

## Test Results

- cognition tests: 34 passed
- acquisition tests: 133 passed (regression clean)
- known baseline failures: 21 unchanged

## Key Properties

- Deterministic replay: identical inputs produce identical events
- EventStore: idempotent upsert, revision history, lifecycle transitions
- Point-in-time: as-of parameter filters future market data
- Future leakage: snapshots with as_of > evaluation time are excluded
- Strict non-empty output directory isolation
- No trading, publishing, daemon, paid API, or UI capabilities

## Limitations

1. Live market snapshot validation requires --mode live with available provider
2. Consensus estimation uses fixture expectation.json (not live survey data)
3. Historical evaluation harness is infrastructure-level (baseline comparisons available)
4. All 6 committed cases are fixture/in-sample engineering evidence

## Recovery Commands

