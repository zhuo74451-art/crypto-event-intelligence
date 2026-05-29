# v0.8 Historical Signal Replay Findings

This report replays older historical event candidates through the same price backfill logic to increase signal sample size. It is research/quality analysis only and is not trading advice.

- total_backfill_rows: 120
- quality_rows: 120

## Backfill Status

| value | count |
|---|---:|
| ok | 120 |

## Quality Status

| value | count |
|---|---:|
| pass | 120 |

## Samples By Event Type

| value | count |
|---|---:|
| macro | 94 |
| hack_security | 10 |
| institutional_flow | 6 |
| staking_governance | 3 |
| halving | 3 |
| network_upgrade | 2 |
| whale_position | 2 |

## Samples By Asset

| value | count |
|---|---:|
| BTC | 82 |
| HYPE | 15 |
| ETH | 13 |
| ONDO | 3 |
| XRP | 2 |
| WLD | 2 |
| SOL | 1 |
| DOGE | 1 |
| BNB | 1 |

## Event Type Performance

| event_type | rows | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| macro | 94 | -0.00% | 0.18% | 0.09% | 2.98% | 11.70% | 19.15% |
| hack_security | 10 | 0.07% | 0.18% | -0.34% | -0.35% | 10.00% | 10.00% |
| institutional_flow | 6 | -0.07% | 0.66% | 1.95% | 12.95% | 33.33% | 50.00% |
| staking_governance | 3 | -0.01% | 0.10% | -1.26% | -1.05% | 0.00% | 0.00% |
| halving | 3 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| network_upgrade | 2 | -0.06% | 0.24% | 0.20% | 0.09% | 50.00% | 50.00% |
| whale_position | 2 | -0.56% | -0.28% | -2.56% | 13.20% | 0.00% | 100.00% |

## Benchmark-Aware Event Type Performance

BTC rows use `abnormal_vs_eth`; non-BTC rows use `abnormal_vs_btc`. This reduces BTC benchmark self-comparison flattening.

| event_type | rows | avg_benchmark_aware_1h | avg_benchmark_aware_4h | avg_benchmark_aware_24h | avg_benchmark_aware_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| macro | 94 | -0.07% | -0.23% | 0.08% | 2.96% | 42.55% | 47.87% |
| hack_security | 10 | 0.15% | -0.08% | -0.38% | -0.43% | 10.00% | 10.00% |
| institutional_flow | 6 | -0.11% | 0.51% | 2.20% | 13.18% | 66.67% | 83.33% |
| staking_governance | 3 | -0.01% | 0.10% | -1.26% | -1.05% | 0.00% | 0.00% |
| halving | 3 | 0.01% | -0.03% | 0.77% | 0.78% | 100.00% | 100.00% |
| network_upgrade | 2 | 0.00% | 0.18% | 0.38% | 0.20% | 100.00% | 100.00% |
| whale_position | 2 | -0.56% | -0.28% | -2.56% | 13.20% | 0.00% | 100.00% |

## Best 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 6.50% | macro | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】CBRS 空单 止盈 啦! |
| 6.22% | institutional_flow | HYPE | Bitwise to add HYPE to balance sheet using fees from Hyperliquid ETF |
| 6.21% | institutional_flow | HYPE | Bitwise将用10%管理费购买$HYPE |
| 5.04% | macro | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】SNDK 空单 平仓止盈! |
| 2.00% | macro | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】HYPE 空单 摊平 啦! |
| 2.00% | macro | HYPE | 【疑似HYPE上币内幕「 HYPE 多仓 TOP 1」】HYPE 多单 浮盈扩大！ |
| 1.92% | macro | HYPE | Bitwise HYPE ETF pledges 10% fees to buybacks |
| 1.88% | macro | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】HYPE 空单 摊平 啦! |
| 1.88% | macro | HYPE | 【Abraxas Capital主地址】HYPE 空单 割肉 啦! |
| 0.82% | macro | HYPE | 美联储新主席即将宣誓就职，谷歌与黑石合作推出AI云公司 |

## Worst 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -4.54% | whale_position | ONDO | 仅在过去 2 个月时间里，Ondo 项目方的多签钱包就向 Coinbase 等交易所累计转移了超过 3.28 亿枚 $ONDO ($9842 万)。  地址： https://t.co/eqO2dMOrZL https://t.co/3c8 |
| -4.51% | macro | ONDO | Ondo项目方多签钱包过去2个月向Coinbase等交易所累计转移超3.28亿枚ONDO |
| -2.87% | macro | ONDO | 余烬监测：ondo项目方多签钱包向Coinbase转入超3.28亿枚ondo |
| -2.19% | staking_governance | XRP | XRP price slips 2% on profit taking |
| -1.37% | macro | DOGE | Revolut launches first physical crypto card |
| -1.37% | macro | XRP | Crude Oil Prices: Brent and WTI Rise as Markets Respond to Trump-Xi Trade Talks |
| -1.18% | macro | WLD | WorldCoin团队将1318枚WLD存入Coinbase |
| -0.99% | macro | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】HYPE 空单 摊平 啦! |
| -0.90% | staking_governance | ETH | 以太坊质押比例上升至31%，长期持有者信心依旧 |
| -0.78% | hack_security | ETH | 黑客攻击Monad Echo协议，损失约7600万美元 |

## Best 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 30.40% | macro | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】CBRS 空单 止盈 啦! |
| 29.68% | institutional_flow | HYPE | Bitwise to add HYPE to balance sheet using fees from Hyperliquid ETF |
| 28.33% | institutional_flow | HYPE | Bitwise将用10%管理费购买$HYPE |
| 25.68% | macro | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】SNDK 空单 平仓止盈! |
| 22.34% | macro | HYPE | Bitwise HYPE ETF pledges 10% fees to buybacks |
| 22.15% | macro | HYPE | 美联储新主席即将宣誓就职，谷歌与黑石合作推出AI云公司 |
| 21.61% | macro | HYPE | 交易员Loracle加仓HYPE空单20万枚，总规模升至6810万美元 |
| 21.08% | macro | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】HYPE 空单 摊平 啦! |
| 21.08% | macro | HYPE | 【疑似HYPE上币内幕「 HYPE 多仓 TOP 1」】HYPE 多单 浮盈扩大！ |
| 20.01% | macro | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】HYPE 空单 摊平 啦! |

## Worst 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -1.67% | staking_governance | XRP | XRP price slips 2% on profit taking |
| -1.45% | macro | XRP | Crude Oil Prices: Brent and WTI Rise as Markets Respond to Trump-Xi Trade Talks |
| -0.84% | staking_governance | ETH | 以太坊质押比例上升至31%，长期持有者信心依旧 |
| -0.82% | hack_security | ETH | 黑客攻击Monad Echo协议，损失约7600万美元 |
| -0.72% | hack_security | ETH | #PeckShieldAlert @dcfgod reports that @EchoProtocol_ was hacked on @monad   The hacker minted 1k $eBTC ($76.7M) &, utili |
| -0.65% | staking_governance | ETH | 5/18 Ethereum ETF Net Flow: $-84.14m $ETHA (BlackRock): –$55.40m $FETH (Fidelity): –$14.70m $ETHW (Bitwise): $0.00m $TET |
| -0.65% | macro | ETH | 黑石以太坊ETF 5月18日净流出26,269 ETH，交易量达5亿美元 |
| -0.63% | hack_security | ETH | Exploit Alert 🚨  According to @dcfgod, @EchoProtocol_ on @monad has been exploited.  The attacker reportedly minted 1,00 |
| -0.63% | hack_security | ETH | Lookonchain：过去4天内发生3起重大黑客攻击事件 |
| -0.60% | macro | ETH | 【麻吉黄立成】ETH 多单 滚仓 啦! |

## Practical Read

- Among event types with at least 10 rows, strongest 24h average: `macro` at 0.09%.
- Among event types with at least 10 rows, strongest 72h average: `macro` at 2.98%.
- Benchmark-aware strongest 24h average: `macro` at 0.08%.
- Benchmark-aware strongest 72h average: `macro` at 2.96%.
- BTC events versus BTC benchmark can flatten abnormal-vs-BTC; use the benchmark-aware table before reading BTC-heavy buckets.
- This is historical replay for source-quality learning, not a live publishing rule.