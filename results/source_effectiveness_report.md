# Source Effectiveness Report

- generated_at_china: 2026-05-28 19:24:39 UTC+8
- source_rows: 10
- ledger_rows: 3
- outcome_rows: 3
- decision_rows: 33

## Source Matrix

| source_type | enabled | shadow_mode | sent_count | outcome_rows | computed_1h_count | computed_4h_count | avg_abnormal_primary_1h | false_positive_like_rate | historical_status | live_effectiveness_status | recommended_route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hyperliquid | true | false | 1 | 1 | 1 | 0 | -0.017535 | 0.0 | needs_more_outcomes | insufficient_live_outcomes | board |
| long_short | true | false | 1 | 1 | 1 | 0 | -0.000336 | 1.0 | needs_more_outcomes | insufficient_live_outcomes | board |
| token_unlock | true | false | 1 | 1 | 1 | 0 | -0.004734 | 0.0 | needs_more_outcomes | insufficient_live_outcomes | digest |
| address_transfer | true | true | 0 | 0 | 0 | 0 | 0.0 | 0.0 | shadow_collect | shadow_or_no_live_data | shadow |
| cex_netflow | true | false | 0 | 0 | 0 | 0 | 0.0 | 0.0 | needs_baseline | shadow_or_no_live_data | shadow |
| exchange_listing | true | true | 0 | 0 | 0 | 0 | 0.0 | 0.0 | shadow_collect | shadow_or_no_live_data | shadow |
| funding_rate | true | true | 0 | 0 | 0 | 0 | 0.0 | 0.0 | shadow_collect | shadow_or_no_live_data | shadow |
| lending_liquidation | true | true | 0 | 0 | 0 | 0 | 0.0 | 0.0 | shadow_collect | shadow_or_no_live_data | shadow |
| news | true | true | 0 | 0 | 0 | 0 | 0.0 | 0.0 | historical_only | shadow_or_no_live_data | shadow |
| stablecoin_flow | true | false | 0 | 0 | 0 | 0 | 0.0 | 0.0 | needs_baseline | shadow_or_no_live_data | shadow |

## Interpretation

- `shadow_or_no_live_data`: source is registered but has no live outcome evidence yet; keep in shadow or archive.
- `insufficient_live_outcomes`: source has live rows but too few matured horizons for product conclusions.
- `likely_noise_or_digest_only`: available outcomes show low movement; lower priority or move to digest.
- `promising_needs_more_samples`: early signal worth more samples, but not statistically conclusive.

This report is for source governance and research QA. It does not provide trading advice.
