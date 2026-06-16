# Protocol 07: Benchmark and Outcome Measurement

**对应决策: 7**

## Outcome Layers

| Layer | Description |
|-------|-------------|
| raw_market_reaction | Absolute price change % in observation window |
| registered_benchmark_relative_reaction | Change relative to the primary benchmark registered for this study |
| historical_materiality | Whether the reaction exceeds expected volatility |

## Outcome vs Registration

Outcome MUST be recorded in a physically separate object from Registration. Registration's `outcome_status` MUST be `not_revealed` until Outcome is computed.

## Naming

The field formerly known as `abnormal_return` in the V1 sealed dataset is a historical artifact. In Pilot v1, the equivalent concept is `registered_benchmark_relative_reaction`. Old data is NOT modified.

## Window Rules

- Each Study Case has exactly ONE primary window
- Secondary/sensitivity windows must NOT rescue a primary window failure
- Both primary benchmark AND sensitivity benchmarks must be pre-registered

## Benchmark Constraints

- For BTC events, existing benchmarks (ETH, SOL, etc.) can only be labeled as "weak proxy"
- Self-benchmark is strictly prohibited (target_asset == primary_benchmark)
- The ONLY valid new field for benchmark-relative reaction is `registered_benchmark_relative_reaction`
