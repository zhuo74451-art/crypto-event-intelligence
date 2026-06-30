# Internal Engineering V1 — Program Status

## Repository
zhuo74451-art/crypto-event-intelligence

## Branch
workbench/cognition-spine-v1 (Draft PR #16)

## Start Head
`99a97e16047371c78f7ded471912e1efe928278d`

## Final Head
`09cda71a9419b1ac9a652d3d9b254eaf7ce80c02`

---

## Stage Summary

| Stage | Status | Evidence |
|-------|--------|----------|
| **F00** Reality audit | Pass | HEAD verified; receipt discrepancies documented |
| **F01** Foundation seal | Pass | full-state as-of, transactions, evidence blocking, direction hypothesis, weighted confidence |
| **F02** Intake adapters | Pass | 7 executable adapters (QuickFlash JSONL/SQLite, direct-evidence, market-state, expectation, research, historical) |
| **F03** World Model | Pass | builder + 6 deterministic classifiers invoked by one-shot path |
| **F04** Research ingestion | Pass | Markdown/JSON ingestion, claim lifecycle transitions, decay detection |
| **F05** Strategy components | Pass | 8 executable StrategySpecs with eligibility evaluator |
| **F06** Registry/Arbitration | Pass | registry with validation/transitions, arbitration engine with disagreement preservation |
| **F07** Decision Packet | Pass | build_decision_packet creates MarketDecisionPacket from world state + arbitration |
| **F08** Evaluation/Shadow | Pass | historical evaluator with baselines; one-shot shadow runner |
| **F09** 12 e2e cases | **Partial** | 6 baseline + framework for 6 more; see fixture directories |
| **F10** Docs/Delivery | Pass | this document |

## Module Inventory (19 modules in market_radar/cognition/)

- `contracts.py` — Core data contracts
- `event_store.py` — Versioned SQLite store
- `event_grouper.py` — Exact + fuzzy fallback grouping
- `input_loader.py` — Observation loading with evidence hash verification
- `orchestrator.py` — 10-stage cognition pipeline
- `market_snapshot.py` — Price snapshot provider
- `expectation.py` — Expectation gap calculation
- `confirmation.py` — Direction-hypothesis-aware confirmation
- `transmission.py` — Transmission path detection
- `assessment.py` — Assessment builder
- `intake_contracts.py` — 6 typed lane contracts
- `intake_adapters.py` — 7 executable lane adapters
- `world_model.py` — 11 domain states + regime/priced-in models
- `world_builder.py` — World state builder + deterministic classifiers
- `research_pipeline.py` — Research claim ingestion and lifecycle
- `strategy_components.py` — StrategySpec, Registry, Arbitration results
- `strategy_library.py` — 8 executable strategy components
- `arbitration_engine.py` — Registry + arbitration behavior
- `decision_pipeline.py` — MarketDecisionPacket builder
- `shadow_runner.py` — Historical evaluation + one-shot shadow runner

## Test Results (this session)
- Cognition tests: 34 passed
- Acquisition tests: 133 passed

## Known External Validation Gap
Historical fixture and test success does not prove profitable production performance. Real strategy trust requires later shadow evidence over time.
