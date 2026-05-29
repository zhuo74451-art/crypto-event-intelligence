# Signal Decay Curve

- generated_at_china: 2026-05-28 19:24:39 UTC+8
- input_rows: 203
- curve_rows: 36

## Curve Preview

| event_type | event_subtype | source_type | sample_count | computed_1h_count | avg_abnormal_primary_1h | computed_4h_count | avg_abnormal_primary_4h | computed_24h_count | avg_abnormal_primary_24h | computed_72h_count | avg_abnormal_primary_72h | decay_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| macro | macro | news:jin10 | 58 | 58 | 0.0 | 58 | 0.0 | 58 | 0.0 | 58 | 0.0 | monitor |
| macro | macro | webhook | 42 | 42 | 9.6e-05 | 42 | 0.000155 | 42 | -0.000607 | 42 | 0.000551 | slow_burn_or_lagged |
| macro | macro | tg:HyperInsight | 16 | 16 | 0.000121 | 16 | 0.000266 | 16 | -0.000339 | 16 | -0.000375 | slow_burn_or_lagged |
| macro | macro | news:cryptonews | 11 | 11 | 0.000112 | 11 | -9e-06 | 11 | -0.001244 | 11 | -0.000192 | slow_burn_or_lagged |
| macro | macro | news:cointelegraph | 9 | 9 | -0.000957 | 9 | 0.002881 | 9 | -0.008123 | 9 | -0.007835 | insufficient_sample |
| macro | macro | news:coinpaper | 8 | 8 | -9.5e-05 | 8 | 0.000594 | 8 | -0.001708 | 8 | -0.001813 | insufficient_sample |
| hack_security | hack_security | webhook | 7 | 7 | 0.000963 | 7 | 0.002527 | 7 | -0.004822 | 7 | -0.005043 | insufficient_sample |
| hack_security | hack_security | news:bitcoinist | 6 | 6 | -0.00065 | 6 | -0.000315 | 6 | -0.005659 | 6 | 0.008192 | insufficient_sample |
| macro | macro | news:decrypt | 6 | 6 | 0.000918 | 6 | 0.002791 | 6 | -0.005961 | 6 | -0.004665 | insufficient_sample |
| other | other | webhook | 4 | 4 | -0.00097 | 4 | 0.000623 | 4 | -1.3e-05 | 4 | 0.007634 | insufficient_sample |
| macro | macro | news:odaily_exchange_gap | 3 | 3 | 0.0 | 3 | 0.0 | 3 | 0.0 | 3 | 0.0 | insufficient_sample |
| hack_security | hack_security | news:cryptonews | 2 | 2 | 0.002017 | 2 | 0.007005 | 2 | 0.002673 | 2 | 0.002963 | insufficient_sample |
| halving | halving | webhook | 2 | 2 | 0.0 | 2 | 0.0 | 2 | 0.0 | 2 | 0.0 | insufficient_sample |
| institutional_flow | institutional_flow | webhook | 2 | 2 | 0.0 | 2 | 0.0 | 2 | 0.0 | 2 | 0.0 | insufficient_sample |
| macro | macro | news:bitcoinist | 2 | 2 | -0.000786 | 2 | 0.000359 | 2 | -0.008524 | 2 | -0.001385 | insufficient_sample |
| macro | macro | news:utoday | 2 | 2 | 0.0 | 2 | 0.0 | 2 | 0.0 | 2 | 0.0 | insufficient_sample |
| macro | macro | tg:OneMillion_AI | 2 | 2 | 0.0 | 2 | 0.0 | 2 | 0.0 | 2 | 0.0 | insufficient_sample |
| network_upgrade | network_upgrade | webhook | 2 | 2 | -0.000632 | 2 | 0.002411 | 2 | 0.002001 | 2 | 0.000884 | insufficient_sample |
| staking_governance | staking_governance | webhook | 2 | 2 | -0.000375 | 2 | 0.000613 | 2 | -0.007946 | 2 | -0.007456 | insufficient_sample |
| hack_security | hack_security | news:bitcoinmagazine | 1 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | insufficient_sample |
| hack_security | hack_security | news:decrypt | 1 | 1 | -0.003563 | 1 | 0.005075 | 1 | -0.003369 | 1 | -0.005541 | insufficient_sample |
| hack_security | hack_security | news:jin10 | 1 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | insufficient_sample |
| hack_security | hack_security | news:odaily_exchange_gap | 1 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | insufficient_sample |
| hack_security | hack_security | tg:OneMillion_AI | 1 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | insufficient_sample |
| halving | halving | news:coinpedia | 1 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | insufficient_sample |
| institutional_flow | institutional_flow | news:cointelegraph | 1 | 1 | 0.000554 | 1 | 0.003583 | 1 | -0.009592 | 1 | -0.014186 | insufficient_sample |
| institutional_flow | institutional_flow | news:cryptonews | 1 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | 1 | 0.0 | insufficient_sample |
| institutional_flow | institutional_flow | news:decrypt | 1 | 1 | 0.000213 | 1 | -0.000981 | 1 | -0.002342 | 1 | -0.010788 | insufficient_sample |
| macro | macro | news:coinpedia | 1 | 1 | 0.000379 | 1 | 0.003623 | 1 | 0.003498 | 1 | 0.003355 | insufficient_sample |
| market_structure | long_short_crowding_extreme | long_short | 1 | 1 | -0.000336 | 0 | 0.0 | 0 | 0.0 | 0 | 0.0 | insufficient_sample |

This curve is for research QA and source routing. It does not provide trading advice.
