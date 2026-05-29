# v0.8 TG Source Usefulness Report

- generated_at_china: 2026-05-28 13:28:41 UTC+8
- lookback_days: 7
- sent_count: 8
- followup_4h_rows: 7
- followup_24h_rows: 0

## By Source

| source | sent | 4h_hit | 24h_hit | status |
| --- | --- | --- | --- | --- |
| stablecoin_flow | 4 | 0/4 | 0/0 | insufficient_data |
| cex_netflow | 2 | 0/2 | 0/0 | insufficient_data |
| exchange_listing | 1 | 0/0 | 0/0 | insufficient_data |
| liquidation | 1 | 0/1 | 0/0 | insufficient_data |

## Interpretation

- `promising`: post-alert movement is starting to support keeping this source.
- `review_noise`: enough negative/no-move evidence to consider lowering priority, raising thresholds, or moving to digest-only.
- `needs_instrumentation`: messages were sent but follow-up coverage is missing.
- `insufficient_data`: not enough observations yet.
- For stablecoin/CEX stablecoin-flow proxy events, movement hit-rate uses BTC's own post-alert return instead of abnormal-vs-BTC.

## Product Rule

This report is for alert-quality operations only. It does not provide trading advice or execution signals.
