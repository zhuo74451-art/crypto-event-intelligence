# v0.7 First-Hand Watcher Daily Report

This report is local-only. It does not send Telegram messages and does not provide trading advice.

## Summary

| field | value |
|---|---:|
| input_alert_rows | 20 |
| deduped_alert_rows | 20 |
| event_rows | 20 |
| needs_model_review_rows | 9 |
| stablecoin_flow_rows | 4 |
| onchain_transfer_rows | 2 |
| cex_netflow_rows | 0 |
| funding_rate_rows | 0 |
| liquidation_rows | 0 |
| status | pass |

## Alerts

| time_china | entity | type | asset | amount_usd | route |
|---|---|---|---|---:|---|
| 2026-06-03 17:47:47 UTC+8 | Tether | stablecoin_treasury_in | USDT | 136900000.00 | review |
| 2026-06-03 17:25:59 UTC+8 | Tether | stablecoin_treasury_in | USDT | 72356102.55 | review |
| 2026-06-03 17:21:11 UTC+8 | Tether | stablecoin_treasury_out | USDT | 180000000.00 | review |
| 2026-06-02 19:56:23 UTC+8 | Tether | stablecoin_treasury_in | USDT | 500000000.00 | review |
| 2026-06-03 17:47:47 UTC+8 | Bitfinex | cex_transfer_out | USDT | 109463867.56 | review |
| 2026-06-03 02:04:11 UTC+8 | Bitfinex | cex_transfer_in | USDT | 86954192.64 | review |
| 2026-06-03 19:37:54 UTC+8 | Unknown Hyperliquid Whale | hyperliquid_position_short | BTC | 69783114.70 | review |
| 2026-06-03 19:37:54 UTC+8 | Matrixport Related | hyperliquid_position_long | ETH | 75180000.00 | review |
| 2026-06-03 19:37:54 UTC+8 | Unknown HYPE Whale | hyperliquid_position_long | HYPE | 100072413.45 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | AORA | 115613.40 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | LAB | 10127642.47 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | GATA | 17896.17 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | CTT | 18662.02 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | ENA | 18158295.95 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | MATTLE | 10158.34 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | XION | 1837661.36 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | CUDIS | 153294.41 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | POWER | 1641640.78 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | BERA | 4191095.46 | review |
| 2026-06-03 19:40:23 UTC+8 | coinmarketcap_token_unlocks | token_unlock_upcoming | MYX | 13057798.79 | review |

## Normalized Events

| event_id | event_time_china | asset | event_type | title |
|---|---|---|---|---|
| `watcher_fh_b22dcf7f666fab1f` | 2026-06-03 17:47:47 UTC+8 | BTC | stablecoin_flow | Tether treasury received $136.90M USDT |
| `watcher_fh_85424eddb842ca32` | 2026-06-03 17:25:59 UTC+8 | BTC | stablecoin_flow | Tether treasury received $72.36M USDT |
| `watcher_fh_3c74283fe1d2d556` | 2026-06-03 17:21:11 UTC+8 | BTC | stablecoin_flow | Tether treasury sent $180.00M USDT |
| `watcher_fh_b8f8238b383c8ecc` | 2026-06-02 19:56:23 UTC+8 | BTC | stablecoin_flow | Tether treasury received $500.00M USDT |
| `watcher_fh_870ebc01a26f0c5a` | 2026-06-03 17:47:47 UTC+8 | USDT | onchain_transfer | Bitfinex wallet cex transfer out $109.46M USDT |
| `watcher_fh_e71623c66eea05af` | 2026-06-03 02:04:11 UTC+8 | USDT | onchain_transfer | Bitfinex wallet cex transfer in $86.95M USDT |
| `watcher_fh_b8f2496d52d670fe` | 2026-06-03 19:37:54 UTC+8 | BTC | whale_position | Unknown Hyperliquid Whale holds large Hyperliquid short position: $69.78M BTC |
| `watcher_fh_5c0ab6b52311e31a` | 2026-06-03 19:37:54 UTC+8 | ETH | whale_position | Matrixport Related holds large Hyperliquid long position: $75.18M ETH |
| `watcher_fh_aa864d8c8c70ed6c` | 2026-06-03 19:37:54 UTC+8 | HYPE | whale_position | Unknown HYPE Whale holds large Hyperliquid long position: $100.07M HYPE |
| `watcher_fh_8a3ca560b51d49a2` | 2026-06-03 19:40:23 UTC+8 | AORA | token_unlock | AORA scheduled token unlock is approaching: $115.61K |
| `watcher_fh_204df23a3d9534e9` | 2026-06-03 19:40:23 UTC+8 | LAB | token_unlock | LAB scheduled token unlock is approaching: $10.13M |
| `watcher_fh_d176d5cdf93e9cb4` | 2026-06-03 19:40:23 UTC+8 | GATA | token_unlock | GATA scheduled token unlock is approaching: $17.90K |
| `watcher_fh_b65d96c15f643a4b` | 2026-06-03 19:40:23 UTC+8 | CTT | token_unlock | CTT scheduled token unlock is approaching: $18.66K |
| `watcher_fh_515b692864a1d9e2` | 2026-06-03 19:40:23 UTC+8 | ENA | token_unlock | ENA scheduled token unlock is approaching: $18.16M |
| `watcher_fh_7a027a00f2f8f646` | 2026-06-03 19:40:23 UTC+8 | MATTLE | token_unlock | MATTLE scheduled token unlock is approaching: $10.16K |
| `watcher_fh_0e796bce7bd74ff1` | 2026-06-03 19:40:23 UTC+8 | XION | token_unlock | XION scheduled token unlock is approaching: $1.84M |
| `watcher_fh_da3de894877ad150` | 2026-06-03 19:40:23 UTC+8 | CUDIS | token_unlock | CUDIS scheduled token unlock is approaching: $153.29K |
| `watcher_fh_6e2438cb6887fe00` | 2026-06-03 19:40:23 UTC+8 | POWER | token_unlock | POWER scheduled token unlock is approaching: $1.64M |
| `watcher_fh_856b44471d92db67` | 2026-06-03 19:40:23 UTC+8 | BERA | token_unlock | BERA scheduled token unlock is approaching: $4.19M |
| `watcher_fh_ae335e054e793ea4` | 2026-06-03 19:40:23 UTC+8 | MYX | token_unlock | MYX scheduled token unlock is approaching: $13.06M |
