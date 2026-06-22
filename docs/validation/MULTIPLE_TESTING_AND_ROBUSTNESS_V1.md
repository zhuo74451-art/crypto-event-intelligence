# Multiple Testing and Robustness V1

## The Multiple Comparisons Problem

When evaluating multiple strategies, time horizons, assets, regimes, or threshold variations, the probability of finding at least one "significant" result by chance increases rapidly. Testing 20 independent hypotheses at the 5% significance level yields a ~64% chance of at least one false positive.

## Correction Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| Bonferroni | Multiply p-values by number of comparisons | Conservative; controls family-wise error rate |
| Holm | Step-down Bonferroni; more powerful | Less conservative than Bonferroni |
| Benjamini-Hochberg | Controls false discovery rate | Appropriate for exploratory settings |

## Declaration Requirements

Every experiment must declare before execution:
- `multiple_testing_family`: What group of comparisons this belongs to
- `number_of_comparisons`: How many independent tests will be performed
- `correction_method`: Which correction will be applied

## Scenarios Requiring Correction

1. Multiple time horizons for the same strategy
2. Multiple assets under the same hypothesis
3. Multiple threshold values for abstention
4. Multiple regime slices
5. Multiple label definitions
6. Multiple feature combinations
7. Multiple baseline comparisons

## Robustness / Sensitivity Analysis

A valid result must be stable across reasonable variations in:

| Parameter | Why It Matters |
|-----------|----------------|
| Event window | Should not depend on exact hours chosen |
| Flat threshold | Should not flip with 0.1% threshold change |
| Benchmark choice | Not just against the weakest benchmark |
| Label maturity window | Should not require exactly N days |
| Regime definition | Should not exist in only one regime |
| Source/provider exclusion | Should not depend on one data source |

If a result is highly sensitive to small changes, it must be marked `unstable`.
