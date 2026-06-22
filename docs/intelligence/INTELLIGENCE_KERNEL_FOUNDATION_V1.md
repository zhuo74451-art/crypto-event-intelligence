# Intelligence Kernel Foundation V1

## System Architecture

The intelligence kernel is organized into five layers:

1. **Contracts** (`contracts/`): Pure data models (dataclasses + enums) with no I/O
2. **Engines** (`engines/`): Deterministic business logic operating on contracts
3. **Adapters** (`adapters/`): Read-only mapping of legacy models to new contracts
4. **Serialization** (`serialization/`): Canonical JSON, JSON Schema export, hashing
5. **Errors** (`errors/`): Structured error codes with machine + human-readable descriptions

## Five Classes of State

1. **Evidence State**: Verification status of individual evidence items and bundles
2. **Event State**: Lifecycle state of events with append-only transition history
3. **Market Regime State**: Probability distributions across market dimensions
4. **Strategy Lifecycle**: State machine for strategy instance execution
5. **Market Assessment**: Final directional output per time horizon

## Core Object Relationships

```
Evidence Items → Evidence Bundle (resolved by EvidenceResolver)
EventEntity + Transitions → State Machine (EventStateMachine)
RegimeDimensions → RegimeSnapshot (point-in-time market state)
StrategyPack → StrategyInstance (lifecycle-managed)
StrategyInstance + Evidence → MarketHypothesis (smallest judgment unit)
Hypotheses → Arbitration → HorizonAssessment → MarketAssessment
```

## Data Flow

```
External sources → Legacy Observation → Adapter → Evidence Items
Evidence Items → EvidenceResolver → EvidenceBundle
Event Updates → EventStateMachine → EventTransitions
Market Data → RegimeDimensions → RegimeSnapshot
Strategy Pack → StrategyLifecycleEngine → StrategyInstance
StrategyInstance + Evidence → MarketHypothesis
Hypotheses + Evidence + Regime → ArbitrationEngine → HorizonAssessment
HorizonAssessments + All State → AssessmentBuilder → MarketAssessment
```

## Key Differences from Legacy Signal Spine

| Aspect | Signal Spine (old) | Intelligence Kernel (new) |
|--------|-------------------|--------------------------|
| Confidence | Uncalibrated float | Typed (qualitative/uncalibrated/calibrated) |
| Evidence | Flat list | Structured with independence groups |
| Event State | Simple enum | Full state machine with history |
| Strategy | Simple Signal | Structured Strategy Pack + Instance |
| Arbitration | Vote-based | Deterministic rules with conflict preservation |
| Assessment | Single direction | Multi-time-horizon with alternative explanations |
