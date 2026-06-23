# Strategy Replay System V1

## Overview

Lane C implements a deterministic, auditable, offline-replayable macro strategy replay system. It compiles historical macro evidence and market data into structured strategy instances, hypotheses, abstention records, and Kernel-compatible input packages.

## Architecture

```
Macro Events + Consensus + Market Data
          │
          ▼
    Replay Engine ──→ Strategy Router
          │                  │
          ▼                  ▼
    State Machine      Strategy Definitions (6)
          │                  │
          ▼                  ▼
    Market Confirmation ←───┘
          │
          ▼
    Evidence Compiler ──→ StrategyHypothesisV1
          │
          ├──→ AbstentionRecordV1 (if insufficient)
          └──→ KernelInputPackageV1 (via adapter)
```

## Components

| Component | File | Description |
|-----------|------|-------------|
| Contracts | contracts.py | All typed dataclasses and enums |
| State Machine | state_machine.py | Deterministic state transitions |
| Replay Clock | replay_clock.py | Point-in-time boundary enforcement |
| Kernel Adapter | kernel_adapter.py | Converts to sealed kernel contracts |
| Replay Engine | replay_engine.py | Event-driven batch replay |
| Regime Classifier | regime_classifier.py | Rule-based macro regime detection |
| Market Confirmation | market_confirmation.py | Cross-asset BTC reaction evaluation |
| Evidence Compiler | evidence_compiler.py | Supporting/opposing evidence assembly |
| Abstention System | abstention.py | First-class abstention records |
| Baselines | baselines.py | 8 comparison baselines |

## Strategy Families (6)

- us_cpi: Headline CPI transmission
- us_core_cpi: Core CPI (Fed-preferred inflation)
- us_nonfarm_payrolls: Labor demand
- us_unemployment_rate: Labor slack
- us_core_pce: Fed-preferred inflation gauge
- us_fomc_rate_decision: Fed policy

## Key Design Rules

1. No future information in strategy inputs
2. Same inputs → same outputs (deterministic)
3. No LLM or paid APIs for strategy judgment
4. Abstention is first-class, not a fallback
5. Multi-horizon preserved (not flattened)
6. Transmission conflicts propagated to kernel
