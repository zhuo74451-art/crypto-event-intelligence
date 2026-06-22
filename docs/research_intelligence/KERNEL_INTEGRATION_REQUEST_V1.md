# Kernel Integration Request V1

## Context

The Research Intelligence Lab produces `ResearchStrategySeed`, `StrategyCandidateProposal`, and `ResearchHypothesis` objects. These need to be mapped to the Intelligence Kernel's `StrategyPack`, `MarketHypothesisInstance`, and `ConfidenceStatement` through an adapter layer.

## Required Adapters

1. **StrategySeed → StrategyPack mapping**
   - Fields to map: domains, assets, time_horizons, regime_scope, trigger_conditions, confirmation_conditions, invalidation_conditions
   - Mapping is one-to-many: one seed may produce multiple strategy packs at different parameterizations

2. **StrategyCandidate → StrategyPack runtime contract**
   - `runtime_contract_status` is currently `pending_integration`
   - Candidate spec needs to be converted to executable StrategyPack format

3. **ResearchHypothesis → MarketHypothesisInstance**
   - Hypothesis test design (required_inputs, labels, null_hypothesis) informs what data the kernel needs

## Non-Requirements

- No need to copy research provenance chains into the kernel
- No need to replicate conflict graphs — kernel can reference research_conflict_ids

## Status

pending_integration — requires kernel implementors to define the adapter contract.
