# v0.5 Research Note: Event Return Statistical Validation

## Input

Backfill:

```text
results/v043_older_mature50_event_price_backfill.csv
```

Quality:

```text
results/v043_older_mature50_event_quality_report.csv
```

## Result

The v0.5 validation did not find any `event_type` bucket that passes FDR correction for `abnormal_vs_btc` across 1h / 4h / 24h / 72h.

This means the v0.4.3 observations should remain exploratory.

## Important Observations

- `hack_security` showed positive 1h and 4h descriptive returns, but sample count is 8, below the default minimum of 10, and it fails FDR.
- `network_upgrade` led the 24h descriptive table in v0.4.3, but sample count is only 3.
- `other` led the 72h descriptive table, but sample count is only 5 and the category is not interpretable.
- BTC-based events often produce `abnormal_vs_btc = 0`, which weakens event_type aggregates when BTC events are mixed into the same taxonomy.

## Current Conclusion

Pipeline quality is acceptable for small-sample research, but current sample size and taxonomy are not enough to claim event alpha.

The correct next step is not to generate a signal. The correct next step is to:

1. Split or exclude `other`.
2. Add Regime Filter features.
3. Add pre-event returns to measure price-in.
4. Build a larger but versioned and holdout-controlled dataset.

## Generated Files

```text
results/v05_event_return_statistical_validation.csv
results/v05_event_return_statistical_validation.md
data/v05_other_event_review.csv
```

## Decision

Default to the null hypothesis:

```text
Observed abnormal returns may be noise, taxonomy artifacts, or regime effects until proven otherwise.
```
