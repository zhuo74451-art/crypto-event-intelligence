# v0.8 Historical Signal Replay Findings

This report replays older historical event candidates through the same price backfill logic to increase signal sample size. It is research/quality analysis only and is not trading advice.

- total_backfill_rows: 171
- quality_rows: 171

## Backfill Status

| value | count |
|---|---:|
| ok | 171 |

## Quality Status

| value | count |
|---|---:|
| pass | 171 |

## Samples By Event Type

| value | count |
|---|---:|
| whale_position | 59 |
| hack_security | 36 |
| institutional_flow | 21 |
| other | 20 |
| staking_governance | 10 |
| network_upgrade | 9 |
| stablecoin_flow | 7 |
| exchange_listing | 4 |
| halving | 4 |
| project_business | 1 |

## Samples By Asset

| value | count |
|---|---:|
| HYPE | 70 |
| BNB | 24 |
| ADA | 23 |
| SOL | 19 |
| XRP | 14 |
| AAVE | 10 |
| LINK | 8 |
| TRX | 1 |
| SHIB | 1 |
| UNI | 1 |

## Event Type Performance

| event_type | rows | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| whale_position | 59 | 0.49% | 1.33% | 7.91% | 9.58% | 89.83% | 98.31% |
| hack_security | 36 | 0.03% | 0.17% | 0.94% | 1.03% | 63.89% | 50.00% |
| institutional_flow | 21 | -0.04% | 0.59% | 1.36% | 1.84% | 90.48% | 57.14% |
| other | 20 | 0.43% | 0.58% | 4.22% | 5.45% | 90.00% | 85.00% |
| staking_governance | 10 | 0.30% | 0.73% | 5.07% | 6.58% | 80.00% | 80.00% |
| network_upgrade | 9 | 0.30% | 0.35% | 1.09% | 2.05% | 100.00% | 55.56% |
| stablecoin_flow | 7 | 0.57% | 0.87% | 2.66% | 2.47% | 85.71% | 57.14% |
| exchange_listing | 4 | 0.24% | -0.13% | 0.93% | -0.02% | 100.00% | 50.00% |
| halving | 4 | -0.00% | -0.06% | 0.74% | 2.28% | 100.00% | 100.00% |
| project_business | 1 | -0.47% | 2.55% | 2.78% | 9.86% | 100.00% | 100.00% |

## Benchmark-Aware Event Type Performance

BTC rows use `abnormal_vs_eth`; non-BTC rows use `abnormal_vs_btc`. This reduces BTC benchmark self-comparison flattening.

| event_type | rows | avg_benchmark_aware_1h | avg_benchmark_aware_4h | avg_benchmark_aware_24h | avg_benchmark_aware_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| whale_position | 59 | 0.49% | 1.33% | 7.91% | 9.58% | 89.83% | 98.31% |
| hack_security | 36 | 0.03% | 0.17% | 0.94% | 1.03% | 63.89% | 50.00% |
| institutional_flow | 21 | -0.04% | 0.59% | 1.36% | 1.84% | 90.48% | 57.14% |
| other | 20 | 0.43% | 0.58% | 4.22% | 5.45% | 90.00% | 85.00% |
| staking_governance | 10 | 0.30% | 0.73% | 5.07% | 6.58% | 80.00% | 80.00% |
| network_upgrade | 9 | 0.30% | 0.35% | 1.09% | 2.05% | 100.00% | 55.56% |
| stablecoin_flow | 7 | 0.57% | 0.87% | 2.66% | 2.47% | 85.71% | 57.14% |
| exchange_listing | 4 | 0.24% | -0.13% | 0.93% | -0.02% | 100.00% | 50.00% |
| halving | 4 | -0.00% | -0.06% | 0.74% | 2.28% | 100.00% | 100.00% |
| project_business | 1 | -0.47% | 2.55% | 2.78% | 9.86% | 100.00% | 100.00% |

## Best 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 20.66% | whale_position | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】HYPE 空单 浮亏扩大！ |
| 20.66% | whale_position | HYPE | 【疑似HYPE上币内幕「 HYPE 多仓 TOP 1」】HYPE 多单 浮盈收窄！ |
| 20.34% | hack_security | HYPE | SEC Chair Paul Atkins Signals a New Era for Crypto — XRP Leads the Conversation |
| 20.20% | whale_position | HYPE | 随着 $HYPE 来到 $49，去年 11 月份以 $38.6 的价格追高开多 138 万枚 $HYPE ($6740 万) 的鲸鱼，目前浮盈 $1400 万了。  好奇这老哥是准备要到啥价位才会平仓，他这个 HYPE 多单已经开了 7 个 |
| 19.82% | whale_position | HYPE | 【疑似HYPE上币内幕「 HYPE 多仓 TOP 1」】HYPE 多单 浮盈收窄！ |
| 19.53% | whale_position | HYPE | 【ZEC最大空头】HYPE 空单 摊平 啦! |
| 19.40% | whale_position | HYPE | HYPE whale alert: a16z-linked wallets may rank No. 6 |
| 17.92% | whale_position | HYPE | 【疑似HYPE上币内幕「 HYPE 多仓 TOP 1」】HYPE 多单 浮盈扩大！ |
| 17.69% | other | HYPE | $HYPE fifty American dollars https://t.co/m4aAv9x9vu |
| 17.66% | whale_position | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】LIT 多单 滚仓 啦! |

## Worst 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -1.03% | hack_security | ADA | GitHub Internal Repositories Breached via VS Code Extension |
| -0.80% | hack_security | AAVE | Digital Assets Like Ordinals Used in Tax Evasion Schemes: Chainalysis |
| -0.73% | hack_security | ADA | Bitcoin Momentum Weakens as BTC Price Support at $75K Becomes Key |
| -0.70% | hack_security | XRP | Ripple CLO Alderoty Breaks Down What Clarity Act Really Means for US Market - U.Today |
| -0.61% | hack_security | ADA | South Carolina Governor Signs Bill Protecting Bitcoin Miners and Banning CBDC Payments |
| -0.59% | hack_security | ADA | EU Reviews Stablecoin Interest Ban in Potential MiCA Overhaul |
| -0.59% | hack_security | ADA | OpenAI Opens First Overseas AI Lab in Singapore With $234M Commitment |
| -0.55% | staking_governance | TRX | TRX 固定促銷，享年化收益 8%！ |
| -0.55% | whale_position | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】HYPE 空单 摊平 啦! |
| -0.55% | whale_position | HYPE | 【疑似HYPE上币内幕「 HYPE 多仓 TOP 1」】HYPE 多单 浮盈收窄！ |

## Best 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 18.92% | hack_security | HYPE | SEC Chair Paul Atkins Signals a New Era for Crypto — XRP Leads the Conversation |
| 18.43% | whale_position | HYPE | 【疑似HYPE上币内幕「 HYPE 多仓 TOP 1」】HYPE 多单 浮盈扩大！ |
| 18.28% | whale_position | HYPE | 【疑似HYPE上币内幕「 HYPE 多仓 TOP 1」】HYPE 多单 浮盈收窄！ |
| 17.97% | whale_position | HYPE | 随着 $HYPE 来到 $49，去年 11 月份以 $38.6 的价格追高开多 138 万枚 $HYPE ($6740 万) 的鲸鱼，目前浮盈 $1400 万了。  好奇这老哥是准备要到啥价位才会平仓，他这个 HYPE 多单已经开了 7 个 |
| 17.59% | whale_position | HYPE | 【ZEC最大空头】HYPE 空单 摊平 啦! |
| 17.50% | whale_position | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】LIT 多单 新开仓! |
| 17.48% | whale_position | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】LIT 多单 滚仓 啦! |
| 17.46% | whale_position | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】LIT 多单 滚仓 啦! |
| 17.21% | whale_position | HYPE | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】LIT 多单 滚仓 啦! |
| 17.20% | whale_position | HYPE | Whale Loracle.hl (@loraclexyz) has started opening a $LIT (3x) long position, currently valued at ~$1M and it’s still in |

## Worst 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -4.22% | other | UNI | CoinDesk 20 performance update: Uniswap (UNI), up 3.7%, leads index higher |
| -1.64% | hack_security | AAVE | Digital Assets Like Ordinals Used in Tax Evasion Schemes: Chainalysis |
| -1.42% | hack_security | AAVE | Morning Minute: Markets Flip Green Overnight Ahead of NVDA Earnings - Decrypt |
| -1.31% | hack_security | AAVE | AI Watchdog Warns of 'Rogue Deployment' Risk at Top Labs, With Capabilities Growing Fast - Decrypt |
| -1.22% | institutional_flow | AAVE | Trump's Truth Social Pulls Bitcoin ETF Application From SEC Review - Decrypt |
| -1.22% | stablecoin_flow | AAVE | Crypto Wealth Firm Nexo Sponsors $3 Million Golf Tournament at Trump International Scotland - Decrypt |
| -1.19% | staking_governance | LINK | 'China's Buffett' Buys Into Circle in Surprise Portfolio Addition - U.Today |
| -1.19% | hack_security | ADA | OpenAI Opens First Overseas AI Lab in Singapore With $234M Commitment |
| -1.05% | institutional_flow | ADA | Crypto News Today (May 20): Bitcoin Struggling Below $80K, SOL & XRP ETFs Green as ETH and BTC ETFs Bleed - 99Bitcoins |
| -1.00% | hack_security | ADA | EU Reviews Stablecoin Interest Ban in Potential MiCA Overhaul |

## Practical Read

- Among event types with at least 10 rows, strongest 24h average: `whale_position` at 7.91%.
- Among event types with at least 10 rows, strongest 72h average: `whale_position` at 9.58%.
- Benchmark-aware strongest 24h average: `whale_position` at 7.91%.
- Benchmark-aware strongest 72h average: `whale_position` at 9.58%.
- BTC events versus BTC benchmark can flatten abnormal-vs-BTC; use the benchmark-aware table before reading BTC-heavy buckets.
- This is historical replay for source-quality learning, not a live publishing rule.