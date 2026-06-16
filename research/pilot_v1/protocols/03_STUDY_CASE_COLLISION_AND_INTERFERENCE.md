# Protocol 03: Study Case Collision and Interference

**对应决策: 3**

## Problem

Multiple events can occur within the same observation window and affect the same asset's price path. Price backfill alone cannot separate their contributions.

## Separability Statuses

| Status | Meaning |
|--------|---------|
| isolated | No other events detected in observation window |
| minor_interference | Other events present but likely negligible |
| conditionally_separable | Separable under specific assumptions |
| cluster_only | Cannot separate; treat as cluster |
| inseparable | Cannot separate under any reasonable assumption |
| insufficient_inventory | Cannot assess due to monitoring gaps |

## Requirements

Each Interference Record MUST include:
- Collision set (concurrent events within window)
- Alternative explanations (at least one)
- Coverage insufficiency flag

Coverage insufficiency MUST NOT be represented as "no other events".
