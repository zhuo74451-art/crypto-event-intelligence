# v0.8 TG Alert Follow-up Report

This report measures what happened after Telegram alerts were sent. It is for alert-quality review only and is not trading advice.

## Summary

| field | value |
|---|---:|
| sent_state_rows | 18 |
| eligible_event_rows | 8 |
| backfill_rows | 8 |
| ok_rows | 7 |
| partial_rows | 0 |
| skipped_rows | 1 |
| computable_4h_rows | 7 |
| computable_24h_rows | 0 |
| min_age_hours | 4.0 |
| total_rows | 18 |
| non_sent_rows | 10 |
| eligible_rows | 8 |

## By Event Type

| event_type | rows | 4h computable | 24h computable | avg abnormal_vs_btc_4h | avg abnormal_vs_btc_24h |
|---|---:|---:|---:|---:|---:|
| stablecoin_flow | 4 | 4 | 0 | 0.00% |  |
| cex_netflow | 2 | 2 | 0 | 0.00% |  |
| liquidation | 1 | 1 | 0 | 0.28% |  |
| exchange_listing | 1 | 0 | 0 |  |  |

## Best 4h Follow-ups

| abnormal_vs_btc | asset | event_type | title |
|---:|---|---|---|
| 0.28% | ETH | liquidation | TG sent alert: liquidation ETH amount_usd=2500000.00 severity=watch |
| 0.00% | BTC | stablecoin_flow | TG sent alert: stablecoin_flow USDT amount_usd=51789849.16 severity=watch followup_proxy=BTC |
| 0.00% | BTC | stablecoin_flow | TG sent alert: stablecoin_flow USDT amount_usd=97000000.00 severity=watch followup_proxy=BTC |
| 0.00% | BTC | cex_netflow | TG sent alert: cex_netflow USDT amount_usd=503257903.73 severity=critical followup_proxy=BTC |
| 0.00% | BTC | cex_netflow | TG sent alert: cex_netflow USDT amount_usd=65000000.00 severity=watch followup_proxy=BTC |
| 0.00% | BTC | stablecoin_flow | TG sent alert: stablecoin_flow USDT amount_usd=51789849.16 severity=watch followup_proxy=BTC |
| 0.00% | BTC | stablecoin_flow | TG sent alert: stablecoin_flow USDT amount_usd=97000000.00 severity=watch followup_proxy=BTC |

## Worst 4h Follow-ups

| abnormal_vs_btc | asset | event_type | title |
|---:|---|---|---|
| 0.00% | BTC | stablecoin_flow | TG sent alert: stablecoin_flow USDT amount_usd=51789849.16 severity=watch followup_proxy=BTC |
| 0.00% | BTC | stablecoin_flow | TG sent alert: stablecoin_flow USDT amount_usd=97000000.00 severity=watch followup_proxy=BTC |
| 0.00% | BTC | cex_netflow | TG sent alert: cex_netflow USDT amount_usd=503257903.73 severity=critical followup_proxy=BTC |
| 0.00% | BTC | cex_netflow | TG sent alert: cex_netflow USDT amount_usd=65000000.00 severity=watch followup_proxy=BTC |
| 0.00% | BTC | stablecoin_flow | TG sent alert: stablecoin_flow USDT amount_usd=51789849.16 severity=watch followup_proxy=BTC |
| 0.00% | BTC | stablecoin_flow | TG sent alert: stablecoin_flow USDT amount_usd=97000000.00 severity=watch followup_proxy=BTC |
| 0.28% | ETH | liquidation | TG sent alert: liquidation ETH amount_usd=2500000.00 severity=watch |

## Best 24h Follow-ups

| abnormal_vs_btc | asset | event_type | title |
|---:|---|---|---|
| n/a |  |  | no computable rows yet |

## Worst 24h Follow-ups

| abnormal_vs_btc | asset | event_type | title |
|---:|---|---|---|
| n/a |  |  | no computable rows yet |

## Interpretation

- 4h rows become meaningful only after alerts are at least 4 hours old.
- 24h rows become meaningful only after alerts are at least 24 hours old.
- Missing rows usually mean the alert is too new, the asset has no Binance symbol, or the old sent-state row lacked asset metadata.
