# v0.8.1 CEX Netflow Baseline Report

- status: needs_more_history
- baseline_rows: 37
- entity_asset_pairs: 12
- ready_pairs: 0
- max_pair_samples: 4 / 72

## Top Pairs

| entity | asset | samples | p95_abs_net_usd | avg_gross_usd | status |
|---|---|---:|---:|---:|---|
| Binance | USDT | 4 | 536731427.38 | 391208186.06 | needs_more_history |
| Binance | WLD | 4 | 1153448.05 | 355306.36 | needs_more_history |
| Binance | UNI | 4 | 123816.96 | 61810.61 | needs_more_history |
| Binance | ONDO | 4 | 80649.26 | 168136.45 | needs_more_history |
| Binance | LINK | 4 | 78059.66 | 99413.76 | needs_more_history |
| Binance | TUSD | 3 | 266207.55 | 266207.55 | needs_more_history |
| Binance | AAVE | 3 | 28819.74 | 33526.73 | needs_more_history |
| Binance | LDO | 3 | 12457.0 | 6872.17 | needs_more_history |
| Bitfinex | SHIB | 3 | 4.73 | 4.72 | needs_more_history |
| Binance | WBTC | 2 | 219267.79 | 219263.58 | needs_more_history |
| Binance | SHIB | 2 | 77393.57 | 47891.71 | needs_more_history |
| Binance | WETH | 1 | 3960.02 | 3960.02 | needs_more_history |

## Rule

Use this baseline to decide whether a CEX netflow alert is unusual. Do not raise Telegram volume until key entity/asset pairs have enough rolling samples.
