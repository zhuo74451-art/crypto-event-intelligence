# Week 1 Raw Research Dataset v1

## Purpose

This dataset packages Week 1 event samples with their corresponding raw price
backfill results. It is the foundation for downstream attribution analysis.

## Dataset Structure

| Layer | Count | Description |
|-------|-------|-------------|
| Event Samples | 5 | 5 event facts from the manifest |
| Unique Price Observations | 5 | 5 deduplicated price backfill results |
| Sample-to-Observation Links | 6 | 6 links connecting samples to observations |

## Event Samples

| ID | Title | Subject | Broadcast (UTC) |
|----|-------|---------|-----------------|
| w1_001 | Loracle HYPE空单浮亏扩大，持仓规模达1.13亿美元 | HYPE | 2026-05-25T13:02:00Z |
| w1_002 | 麻吉黄立成增持ETH多单921.47枚，清算价接近现价 | ETH | 2026-05-25T15:19:00Z |
| w1_003 | Binance近10天BTC流入显著增加，比特币面临卖出信号 | BTC | 2026-05-25T16:12:00Z |
| w1_004 | Strategy本周暂停比特币购买，转而回购可转换债务 | BTC | 2026-05-25T16:12:00Z |
| w1_005 | WTI原油期货日内暴跌6% | WTI | 2026-05-25T11:34:00Z |

## Price Observations

| Key | Observed Asset | Provider | Interval | Policy | Signed Lag |
|-----|---------------|----------|----------|--------|------------|
| `obs:1dca300591048a74` | HYPE | hyperliquid | 15m | nearest_candle_open | -120s |
| `obs:834f574fd532130f` | ETH | binance | 1m | first_after_target | 0s |
| `obs:51cda55f23d17cca` | BTC | binance | 1m | first_after_target | 0s |
| `obs:ecd43b0d379775e0` | BTC | binance | 1m | first_after_target | 0s |
| `obs:41922c2e6c5cd84d` | ETH | binance | 1m | first_after_target | 0s |

## Sample Links

| Sample | Result ID | Observation Key | Reused |
|--------|-----------|-----------------|--------|
| w1_001 | w1_001 | `obs:1dca300591048a74` | no |
| w1_002 | w1_002 | `obs:834f574fd532130f` | no |
| w1_003 | w1_003 | `obs:51cda55f23d17cca` | no |
| w1_004 | w1_004 | `obs:51cda55f23d17cca` | yes (from w1_003) |
| w1_005 | w1_005__BTC | `obs:ecd43b0d379775e0` | no |
| w1_005 | w1_005__ETH | `obs:41922c2e6c5cd84d` | no |

## Key Design Decisions

1. **t0 = broadcast_time**: All price snapshots use the event broadcast
   time as t0, not event time or edit time.

2. **HYPE 15m / BTC,ETH 1m**: HYPE uses Hyperliquid 15m candles with
   nearest_candle_open selection (450s max lag). BTC and ETH use Binance
   1m klines with first_after_target selection (120s max lag).

3. **w1_003 / w1_004 share observation**: Both samples reference the same
   BTC price at 2026-05-25T16:12:00Z. The price was fetched once and
   reused via run-level SnapshotCache. w1_004 is marked observation_reused.

4. **Price response != event attribution**: The observed price movement
   may be influenced by confounding factors. This dataset provides raw
   returns only — it does not assign causality.

## Known Limitations

- HYPE data uses 15m candles (not 1m). Signed lag of -120s means the
  nearest candle open is 2 minutes before broadcast time.
- 24h windows may be pending if data was generated before full maturity.
- Some samples may have duplicate broadcast times (e.g., w1_003/w1_004).
- No attribution score or confidence is calculated at this layer.

## Downstream Consumption

Attribution analysis should use `sample_price_links` to join samples
with their observations. Use `price_observations` as the canonical
price data. The `price_observation_key` ensures dedup across samples.

*Generated: 2026-06-16T07:15:01Z*
*Version: v1 | Status: raw_no_attribution*
