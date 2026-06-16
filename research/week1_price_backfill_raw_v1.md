# Week 1 Price Backfill — Network Raw Results

**Run mode**: network
**Generated**: 2026-06-16T06:40:08Z
**Observations**: 6
**Source commit**: 3de23324ab6d681aad7365e08c2b1e869a220cbc

---

## w1_001: HYPE -> HYPE

| Field | Value |
|-------|-------|
| broadcast_time_utc | 2026-05-25T13:02:00Z |
| t0_basis | broadcast_time |
| provider | hyperliquid |
| interval | 15m |
| precision_seconds | 900 |
| selection_policy | nearest_candle_open |
| signed_lag_seconds | -120 |
| t0_price | 62.61 (completed) src=hyperliquid_public_api lag=120s |
| 1h_status | completed |
| 1h_return_percent | 1.1276% |
| 1h_target_price | 63.316 |
| 1h_signed_lag_s | -120 |
| 1h_btc_abnormal | 1.1892% |
| 1h_eth_abnormal | 1.1852% |
| 1h_sel_policy | nearest_candle_open |
| 4h_status | completed |
| 4h_return_percent | -0.8625% |
| 4h_target_price | 62.07 |
| 4h_signed_lag_s | -120 |
| 4h_btc_abnormal | -1.4137% |
| 4h_eth_abnormal | -1.9287% |
| 4h_sel_policy | nearest_candle_open |
| 24h_status | completed |
| 24h_return_percent | -0.7714% |
| 24h_target_price | 62.127 |
| 24h_signed_lag_s | -120 |
| 24h_btc_abnormal | -0.4527% |
| 24h_eth_abnormal | -1.1322% |
| 24h_sel_policy | nearest_candle_open |
| data_origin | network |
| calculation_version | v1.18-week1-rc |

---

## w1_002: ETH -> ETH

| Field | Value |
|-------|-------|
| broadcast_time_utc | 2026-05-25T15:19:00Z |
| t0_basis | broadcast_time |
| provider | binance |
| interval | 1m |
| precision_seconds | 60 |
| selection_policy | first_after_target |
| signed_lag_seconds | 0 |
| t0_price | 2130.34 (completed) src=binance_public_api lag=0s |
| 1h_status | completed |
| 1h_return_percent | -0.2028% |
| 1h_target_price | 2126.02 |
| 1h_signed_lag_s | 0 |
| 1h_btc_abnormal | 0.0251% |
| 1h_eth_abnormal | self_benchmark% |
| 1h_sel_policy | first_after_target |
| 4h_status | completed |
| 4h_return_percent | -0.3267% |
| 4h_target_price | 2123.38 |
| 4h_signed_lag_s | 0 |
| 4h_btc_abnormal | -0.0142% |
| 4h_eth_abnormal | self_benchmark% |
| 4h_sel_policy | first_after_target |
| 24h_status | completed |
| 24h_return_percent | -1.0036% |
| 24h_target_price | 2108.96 |
| 24h_signed_lag_s | 0 |
| 24h_btc_abnormal | 0.0047% |
| 24h_eth_abnormal | self_benchmark% |
| 24h_sel_policy | first_after_target |
| data_origin | network |
| calculation_version | v1.18-week1-rc |

---

## w1_003: BTC -> BTC

| Field | Value |
|-------|-------|
| broadcast_time_utc | 2026-05-25T16:12:00Z |
| t0_basis | broadcast_time |
| provider | binance |
| interval | 1m |
| precision_seconds | 60 |
| selection_policy | first_after_target |
| signed_lag_seconds | 0 |
| t0_price | 77583.8 (completed) src=binance_public_api lag=0s |
| 1h_status | completed |
| 1h_return_percent | 0.181% |
| 1h_target_price | 77724.19 |
| 1h_signed_lag_s | 0 |
| 1h_btc_abnormal | self_benchmark% |
| 1h_eth_abnormal | -0.1857% |
| 1h_sel_policy | first_after_target |
| 4h_status | completed |
| 4h_return_percent | -0.1725% |
| 4h_target_price | 77450.0 |
| 4h_signed_lag_s | 0 |
| 4h_btc_abnormal | self_benchmark% |
| 4h_eth_abnormal | 0.0884% |
| 4h_sel_policy | first_after_target |
| 24h_status | completed |
| 24h_return_percent | -1.5387% |
| 24h_target_price | 76390.0 |
| 24h_signed_lag_s | 0 |
| 24h_btc_abnormal | self_benchmark% |
| 24h_eth_abnormal | 0.7316% |
| 24h_sel_policy | first_after_target |
| data_origin | network |
| calculation_version | v1.18-week1-rc |

---

## w1_004: BTC -> BTC

| Field | Value |
|-------|-------|
| broadcast_time_utc | 2026-05-25T16:12:00Z |
| t0_basis | broadcast_time |
| provider | binance |
| interval | 1m |
| precision_seconds | 60 |
| selection_policy | first_after_target |
| signed_lag_seconds | N/A |
| t0_price | None (unavailable) src=network_error lag=Nones |
| network_error | binance_api_failed: BTCUSDT at 2026-05-25T16:12:00Z |
| 1h_status | completed |
| 1h_return_percent | 0.181% |
| 1h_target_price | 77724.19 |
| 1h_signed_lag_s | 0 |
| 1h_btc_abnormal | self_benchmark% |
| 1h_eth_abnormal | -0.1857% |
| 1h_sel_policy | first_after_target |
| 4h_status | completed |
| 4h_return_percent | -0.1725% |
| 4h_target_price | 77450.0 |
| 4h_signed_lag_s | 0 |
| 4h_btc_abnormal | self_benchmark% |
| 4h_eth_abnormal | 0.0884% |
| 4h_sel_policy | first_after_target |
| 24h_status | completed |
| 24h_return_percent | -1.5387% |
| 24h_target_price | 76390.0 |
| 24h_signed_lag_s | 0 |
| 24h_btc_abnormal | self_benchmark% |
| 24h_eth_abnormal | 0.7316% |
| 24h_sel_policy | first_after_target |
| data_origin | network_error |
| calculation_version | v1.18-week1-rc |

---

## w1_005__BTC: WTI -> BTC

| Field | Value |
|-------|-------|
| broadcast_time_utc | 2026-05-25T11:34:00Z |
| t0_basis | broadcast_time |
| provider | binance |
| interval | 1m |
| precision_seconds | 60 |
| selection_policy | first_after_target |
| signed_lag_seconds | 0 |
| t0_price | 77477.91 (completed) src=binance_public_api lag=0s |
| 1h_status | completed |
| 1h_return_percent | -0.1291% |
| 1h_target_price | 77377.92 |
| 1h_signed_lag_s | 0 |
| 1h_btc_abnormal | self_benchmark% |
| 1h_eth_abnormal | -0.0795% |
| 1h_sel_policy | first_after_target |
| 4h_status | completed |
| 4h_return_percent | 0.2024% |
| 4h_target_price | 77634.75 |
| 4h_signed_lag_s | 0 |
| 4h_btc_abnormal | self_benchmark% |
| 4h_eth_abnormal | -0.1251% |
| 4h_sel_policy | first_after_target |
| 24h_status | completed |
| 24h_return_percent | -0.2156% |
| 24h_target_price | 77310.87 |
| 24h_signed_lag_s | 0 |
| 24h_btc_abnormal | self_benchmark% |
| 24h_eth_abnormal | -0.4417% |
| 24h_sel_policy | first_after_target |
| data_origin | network |
| calculation_version | v1.18-week1-rc |

---

## w1_005__ETH: WTI -> ETH

| Field | Value |
|-------|-------|
| broadcast_time_utc | 2026-05-25T11:34:00Z |
| t0_basis | broadcast_time |
| provider | binance |
| interval | 1m |
| precision_seconds | 60 |
| selection_policy | first_after_target |
| signed_lag_seconds | 0 |
| t0_price | 2118.59 (completed) src=binance_public_api lag=0s |
| 1h_status | completed |
| 1h_return_percent | -0.0496% |
| 1h_target_price | 2117.54 |
| 1h_signed_lag_s | 0 |
| 1h_btc_abnormal | 0.0795% |
| 1h_eth_abnormal | self_benchmark% |
| 1h_sel_policy | first_after_target |
| 4h_status | completed |
| 4h_return_percent | 0.3276% |
| 4h_target_price | 2125.53 |
| 4h_signed_lag_s | 0 |
| 4h_btc_abnormal | 0.1251% |
| 4h_eth_abnormal | self_benchmark% |
| 4h_sel_policy | first_after_target |
| 24h_status | completed |
| 24h_return_percent | 0.2261% |
| 24h_target_price | 2123.38 |
| 24h_signed_lag_s | 0 |
| 24h_btc_abnormal | 0.4417% |
| 24h_eth_abnormal | self_benchmark% |
| 24h_sel_policy | first_after_target |
| data_origin | network |
| calculation_version | v1.18-week1-rc |

---
