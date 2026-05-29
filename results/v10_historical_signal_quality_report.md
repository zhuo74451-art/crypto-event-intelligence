# v0.8 Historical Source Usefulness From Backtest

- backfill: `C:\Users\PC\Desktop\Projects\事件情报系统\results\v08_historical_replay_conservative_120_price_backfill.csv`
- input_rows: 120
- event_type_rows: 7
- source_rows: 9

## By Event Type

| event_type | samples | 24h_valid | 24h_avg | 24h_hit | status |
| --- | --- | --- | --- | --- | --- |
| macro | 94 | 94 | 0.000865 | 0.0319 | benchmark_polluted |
| hack_security | 10 | 10 | -0.003375 | 0.0 | benchmark_polluted |
| institutional_flow | 6 | 6 | 0.019451 | 0.3333 | insufficient_data |
| halving | 3 | 3 | 0.0 | 0.0 | insufficient_data |
| staking_governance | 3 | 3 | -0.012606 | 0.0 | insufficient_data |
| network_upgrade | 2 | 2 | 0.002001 | 0.0 | insufficient_data |
| whale_position | 2 | 2 | -0.025591 | 0.5 | insufficient_data |

## By Source

| source | samples | 24h_valid | 24h_avg | 24h_hit | status |
| --- | --- | --- | --- | --- | --- |
| tg:HyperInsight | 20 | 20 | 0.009271 | 0.1 | promising_for_expansion |
| webhook | 48 | 48 | -0.000469 | 0.0625 | benchmark_polluted |
| news:jin10 | 28 | 28 | 0.0 | 0.0 | benchmark_polluted |
| news:cryptonews | 13 | 13 | -0.001263 | 0.0 | benchmark_polluted |
| news:coinpaper | 5 | 5 | -0.002733 | 0.0 | insufficient_data |
| news:coinpedia | 2 | 2 | 0.001749 | 0.0 | insufficient_data |
| news:odaily_exchange_gap | 2 | 2 | -0.028497 | 0.5 | insufficient_data |
| news:bitcoinmagazine | 1 | 1 | 0.0 | 0.0 | insufficient_data |
| news:utoday | 1 | 1 | 0.0 | 0.0 | insufficient_data |

## Interpretation Rules

- `promising_for_expansion`: historical rows show enough follow-up movement to justify more samples/source work.
- `benchmark_polluted`: BTC/ETH benchmark assets dominate; do not use this bucket for abnormal-vs-BTC conclusions without a different benchmark.
- `review_noise_or_digest_only`: enough samples but weak post-event movement; lower priority or move to digest.
- `insufficient_data`: do not make product conclusions yet.

This report is research QA only and does not provide trading instructions.
