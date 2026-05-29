# v0.7 First-Hand Watcher Daily Report

This report is local-only. It does not send Telegram messages and does not provide trading advice.

## Summary

| field | value |
|---|---:|
| input_alert_rows | 3 |
| deduped_alert_rows | 3 |
| event_rows | 3 |
| needs_model_review_rows | 0 |
| stablecoin_flow_rows | 0 |
| onchain_transfer_rows | 0 |
| status | pass |

## Alerts

| time_china | entity | type | asset | amount_usd | route |
|---|---|---|---|---:|---|
| 2026-05-28 08:00:00 UTC+8 | Binance USD-M | funding_rate_high_positive | BTC | 10000.00 | review |
| 2026-05-28 08:00:00 UTC+8 | Binance USD-M | funding_rate_high_positive | ETH | 2421.00 | review |
| 2026-05-28 08:00:00 UTC+8 | Binance USD-M | funding_rate_high_negative | SOL | 5061.00 | review |

## Normalized Events

| event_id | event_time_china | asset | event_type | title |
|---|---|---|---|---|
| `watcher_fh_6f3e56768004eac9` | 2026-05-28 08:00:00 UTC+8 | BTC | funding_rate | BTC funding rate is unusually positive: 0.00010000 |
| `watcher_fh_7de60de387df5384` | 2026-05-28 08:00:00 UTC+8 | ETH | funding_rate | ETH funding rate is unusually positive: 0.00002421 |
| `watcher_fh_ba39cff8b34167a2` | 2026-05-28 08:00:00 UTC+8 | SOL | funding_rate | SOL funding rate is unusually negative: -0.00005061 |
