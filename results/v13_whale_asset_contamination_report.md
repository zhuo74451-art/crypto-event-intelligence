# v13 Whale Asset Contamination Report

- generated_at_china: 2026-05-28 19:45:49 UTC+8
- whale_rows: 59
- asset_groups: 6
- status: fail

| asset | count | share | days | burst_3d_share | top_source_share | avg_24h | win_rate_24h | flags | recommendation |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| HYPE | 48 | 0.8136 | 1.4012 | 1.0 | 0.7083 | 0.09567 | 0.9375 | single_asset_concentration,short_time_span,burst_window_concentration,single_source_dominated | downgrade_asset_whale_to_digest |
| SOL | 5 | 0.0847 | 0.0848 | 1.0 | 1.0 | 0.010827 | 1.0 | short_time_span,burst_window_concentration,single_source_dominated | collect_more_with_contamination_flag |
| AAVE | 2 | 0.0339 | 0.9948 | 1.0 | 1.0 | 0.000668 | 0.5 | short_time_span,burst_window_concentration,single_source_dominated | collect_more_with_contamination_flag |
| XRP | 2 | 0.0339 | 0.0846 | 1.0 | 0.5 | -0.003633 | 0.0 | short_time_span,burst_window_concentration | collect_more_with_contamination_flag |
| BNB | 1 | 0.0169 | 0.0 | 1.0 | 1.0 | 0.009199 | 1.0 | burst_window_concentration,single_source_dominated | collect_more_with_contamination_flag |
| LINK | 1 | 0.0169 | 0.0 | 1.0 | 1.0 | 0.019699 | 1.0 | burst_window_concentration,single_source_dominated | collect_more_with_contamination_flag |
