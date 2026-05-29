# v0.7 First-Hand Watcher Daily Report

This report is local-only. It does not send Telegram messages and does not provide trading advice.

## Summary

| field | value |
|---|---:|
| input_alert_rows | 9 |
| deduped_alert_rows | 9 |
| event_rows | 9 |
| needs_model_review_rows | 5 |
| stablecoin_flow_rows | 0 |
| onchain_transfer_rows | 0 |
| cex_netflow_rows | 0 |
| funding_rate_rows | 0 |
| liquidation_rows | 0 |
| status | pass |

## Alerts

| time_china | entity | type | asset | amount_usd | route |
|---|---|---|---|---:|---|
| 2026-05-28 19:23:27 UTC+8 | Unknown Hyperliquid Whale | hyperliquid_position_long | BTC | 34959911.44 | review |
| 2026-05-28 19:23:27 UTC+8 | Matrixport Related | hyperliquid_position_long | ETH | 79520000.00 | review |
| 2026-05-28 19:23:27 UTC+8 | loraclexyz | hyperliquid_position_short | BTC | 34375168.54 | review |
| 2026-05-28 19:23:27 UTC+8 | loraclexyz | hyperliquid_position_short | HYPE | 102660871.07 | review |
| 2026-05-28 19:23:27 UTC+8 | Unknown HYPE Whale | hyperliquid_position_long | HYPE | 78367102.49 | review |
| 2026-05-28 08:00:00 UTC+8 | Binance | cex_listing_announcement | CTR | 0 | review |
| 2026-05-28 19:23:36 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | HAEDAL | 762030.98 | review |
| 2026-05-28 19:23:36 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | HOME | 19617278.19 | review |
| 2026-05-28 19:23:36 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | TBOT | 1097.64 | review |

## Normalized Events

| event_id | event_time_china | asset | event_type | title |
|---|---|---|---|---|
| `watcher_fh_dbb232d98231d333` | 2026-05-28 19:23:27 UTC+8 | BTC | whale_position | Unknown Hyperliquid Whale holds large Hyperliquid long position: $34.96M BTC |
| `watcher_fh_5c0ab6b52311e31a` | 2026-05-28 19:23:27 UTC+8 | ETH | whale_position | Matrixport Related holds large Hyperliquid long position: $79.52M ETH |
| `watcher_fh_f03efc9e86591489` | 2026-05-28 19:23:27 UTC+8 | BTC | whale_position | loraclexyz holds large Hyperliquid short position: $34.38M BTC |
| `watcher_fh_dfd0158b68a27d1a` | 2026-05-28 19:23:27 UTC+8 | HYPE | whale_position | loraclexyz holds large Hyperliquid short position: $102.66M HYPE |
| `watcher_fh_aa864d8c8c70ed6c` | 2026-05-28 19:23:27 UTC+8 | HYPE | whale_position | Unknown HYPE Whale holds large Hyperliquid long position: $78.37M HYPE |
| `watcher_fh_c882497a6ccec22f` | 2026-05-28 08:00:00 UTC+8 | CTR | exchange_listing | Binance published listing announcement for CTR |
| `watcher_fh_e3179cf77941da9e` | 2026-05-28 19:23:36 UTC+8 | HAEDAL | token_unlock | HAEDAL scheduled token unlock is approaching: $762.03K |
| `watcher_fh_d52226e92055465c` | 2026-05-28 19:23:36 UTC+8 | HOME | token_unlock | HOME scheduled token unlock is approaching: $19.62M |
| `watcher_fh_adbf5f85f5f6391f` | 2026-05-28 19:23:36 UTC+8 | TBOT | token_unlock | TBOT scheduled token unlock is approaching: $1.10K |
