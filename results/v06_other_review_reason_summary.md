# v0.6 Other Review Reason Summary

This is a rule-based split of the `other_review` bucket. It does not mutate the source queue.

- total_other_review_rows: 210
- auto_discard_candidate_count: 205
- keep_review_count: 5

## Reasons

| reason | count |
|---|---:|
| reject_missing_entity_low_crypto_relevance | 155 |
| reject_social_noise_or_contextless | 22 |
| reject_geopolitics_no_crypto_angle | 10 |
| reject_equity_company_no_crypto_angle | 6 |
| reject_generic_price_recap | 6 |
| review_btc_treasury_company | 3 |
| reject_non_crypto_health_weather_local | 2 |
| reject_opinion_or_kol_thesis | 2 |
| reject_tradfi_marketing_or_ad | 1 |
| review_crypto_entity_missing | 1 |
| reject_industry_meta_or_career_content | 1 |
| review_onchain_transfer | 1 |

## Actions

| action | count |
|---|---:|
| auto_discard_candidate | 205 |
| keep_review | 5 |