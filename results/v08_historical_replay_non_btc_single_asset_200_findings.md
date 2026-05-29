# v0.8 Historical Signal Replay Findings

This report replays older historical event candidates through the same price backfill logic to increase signal sample size. It is research/quality analysis only and is not trading advice.

- total_backfill_rows: 1
- quality_rows: 1

## Backfill Status

| value | count |
|---|---:|
| ok | 1 |

## Quality Status

| value | count |
|---|---:|
| pass | 1 |

## Samples By Event Type

| value | count |
|---|---:|
| token_unlock | 1 |

## Samples By Asset

| value | count |
|---|---:|
| XRP | 1 |

## Event Type Performance

| event_type | rows | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| token_unlock | 1 | 0.04% | 0.19% | -2.19% | -1.67% | 0.00% | 0.00% |

## Benchmark-Aware Event Type Performance

BTC rows use `abnormal_vs_eth`; non-BTC rows use `abnormal_vs_btc`. This reduces BTC benchmark self-comparison flattening.

| event_type | rows | avg_benchmark_aware_1h | avg_benchmark_aware_4h | avg_benchmark_aware_24h | avg_benchmark_aware_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| token_unlock | 1 | 0.04% | 0.19% | -2.19% | -1.67% | 0.00% | 0.00% |

## Best 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -2.19% | token_unlock | XRP | XRP price slips 2% on profit taking |

## Worst 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -2.19% | token_unlock | XRP | XRP price slips 2% on profit taking |

## Best 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -1.67% | token_unlock | XRP | XRP price slips 2% on profit taking |

## Worst 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -1.67% | token_unlock | XRP | XRP price slips 2% on profit taking |

## Practical Read

- No event_type has at least 10 rows yet; treat all per-type conclusions as weak.
- BTC events versus BTC benchmark can flatten abnormal-vs-BTC; use the benchmark-aware table before reading BTC-heavy buckets.
- This is historical replay for source-quality learning, not a live publishing rule.