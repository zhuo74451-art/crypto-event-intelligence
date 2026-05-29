# v0.8 Historical Signal Replay Findings

This report replays older historical event candidates through the same price backfill logic to increase signal sample size. It is research/quality analysis only and is not trading advice.

- total_backfill_rows: 281
- quality_rows: 281

## Backfill Status

| value | count |
|---|---:|
| ok | 281 |

## Quality Status

| value | count |
|---|---:|
| pass | 281 |

## Samples By Event Type

| value | count |
|---|---:|
| hack_security | 86 |
| institutional_flow | 57 |
| other | 42 |
| network_upgrade | 30 |
| whale_position | 17 |
| staking_governance | 16 |
| stablecoin_flow | 12 |
| project_business | 9 |
| exchange_listing | 5 |
| halving | 4 |
| market_structure | 2 |
| onchain_data | 1 |

## Samples By Asset

| value | count |
|---|---:|
| BNB | 60 |
| ADA | 53 |
| SOL | 41 |
| HYPE | 38 |
| AAVE | 35 |
| XRP | 25 |
| LINK | 10 |
| DOGE | 6 |
| ONDO | 4 |
| AVAX | 3 |
| UNI | 3 |
| TRX | 1 |
| SHIB | 1 |
| WLD | 1 |

## Event Type Performance

| event_type | rows | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| hack_security | 86 | 0.01% | 0.11% | 0.26% | 0.48% | 54.65% | 44.19% |
| institutional_flow | 57 | -0.07% | 0.36% | 0.94% | 3.67% | 63.16% | 52.63% |
| other | 42 | 0.11% | 0.23% | 2.74% | 5.95% | 85.71% | 78.57% |
| network_upgrade | 30 | 0.05% | 0.03% | 0.33% | 2.27% | 46.67% | 56.67% |
| whale_position | 17 | -0.09% | -0.06% | -0.23% | 1.56% | 64.71% | 82.35% |
| staking_governance | 16 | 0.26% | 0.43% | 2.18% | 4.34% | 62.50% | 62.50% |
| stablecoin_flow | 12 | 0.33% | 0.60% | 1.55% | 1.73% | 75.00% | 58.33% |
| project_business | 9 | 0.03% | 1.34% | 1.16% | 4.16% | 44.44% | 77.78% |
| exchange_listing | 5 | 0.15% | 0.18% | 0.78% | 0.66% | 80.00% | 80.00% |
| halving | 4 | 0.01% | -0.02% | 0.27% | 1.52% | 75.00% | 75.00% |
| market_structure | 2 | 0.15% | -0.04% | -1.35% | -0.35% | 0.00% | 50.00% |
| onchain_data | 1 | -0.12% | -0.03% | -0.97% | 1.17% | 0.00% | 100.00% |

## Benchmark-Aware Event Type Performance

BTC rows use `abnormal_vs_eth`; non-BTC rows use `abnormal_vs_btc`. This reduces BTC benchmark self-comparison flattening.

| event_type | rows | avg_benchmark_aware_1h | avg_benchmark_aware_4h | avg_benchmark_aware_24h | avg_benchmark_aware_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| hack_security | 86 | 0.01% | 0.11% | 0.26% | 0.48% | 54.65% | 44.19% |
| institutional_flow | 57 | -0.07% | 0.36% | 0.94% | 3.67% | 63.16% | 52.63% |
| other | 42 | 0.11% | 0.23% | 2.74% | 5.95% | 85.71% | 78.57% |
| network_upgrade | 30 | 0.05% | 0.03% | 0.33% | 2.27% | 46.67% | 56.67% |
| whale_position | 17 | -0.09% | -0.06% | -0.23% | 1.56% | 64.71% | 82.35% |
| staking_governance | 16 | 0.26% | 0.43% | 2.18% | 4.34% | 62.50% | 62.50% |
| stablecoin_flow | 12 | 0.33% | 0.60% | 1.55% | 1.73% | 75.00% | 58.33% |
| project_business | 9 | 0.03% | 1.34% | 1.16% | 4.16% | 44.44% | 77.78% |
| exchange_listing | 5 | 0.15% | 0.18% | 0.78% | 0.66% | 80.00% | 80.00% |
| halving | 4 | 0.01% | -0.02% | 0.27% | 1.52% | 75.00% | 75.00% |
| market_structure | 2 | 0.15% | -0.04% | -1.35% | -0.35% | 0.00% | 50.00% |
| onchain_data | 1 | -0.12% | -0.03% | -0.97% | 1.17% | 0.00% | 100.00% |

## Best 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 20.34% | hack_security | HYPE | SEC Chair Paul Atkins Signals a New Era for Crypto — XRP Leads the Conversation |
| 16.39% | other | HYPE | 🔥 BITWISE SAYS HYPE IS UNDERVALUED  Bitwise CIO Matt Hougan says the market is wrongly valuing Hyperliquid as only a per |
| 15.61% | stablecoin_flow | HYPE | HYPE突破50 USDT，24H涨幅5.25% |
| 15.53% | other | HYPE | Evaded (@ICanPlug) made $2.1M in just 2 days!  Yesterday, he opened 10x longs on 36,875 $ZEC($21.59M) and 287,618 $HYPE( |
| 15.51% | other | HYPE | Evaded (@ICanPlug) made $2.1M in just 2 days!  Yesterday, he opened 10x longs on 36,875 $ZEC($21.59M) and 287,618 $HYPE( |
| 15.01% | staking_governance | HYPE | 链上监测：鲸鱼在过去10小时内购买206,325枚HYPE并质押 |
| 14.18% | staking_governance | HYPE | Anchorage (@Anchorage) linked wallet further withdrew 44,510 $HYPE worth $2.16M from #Gate.  They have bought 2.385M $HY |
| 11.48% | institutional_flow | HYPE | 🚨HYPERLIQUID ETFs SEE $22M INFLOWS IN FIRST WEEK  The first U.S. spot $HYPE ETFs have pulled in $22.3M in net inflows si |
| 10.64% | other | HYPE | I don't think we'll ever see altseason back.   Most of the altcoins will die and have literally no purpose in this ecosy |
| 9.57% | institutional_flow | HYPE | Hyperliquid ETF pulls $5M in days, 21Shares says |

## Worst 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -4.54% | whale_position | ONDO | 仅在过去 2 个月时间里，Ondo 项目方的多签钱包就向 Coinbase 等交易所累计转移了超过 3.28 亿枚 $ONDO ($9842 万)。  地址： https://t.co/eqO2dMOrZL https://t.co/3c8 |
| -4.51% | whale_position | ONDO | Ondo项目方多签钱包过去2个月向Coinbase等交易所累计转移超3.28亿枚ONDO |
| -4.28% | institutional_flow | DOGE | Dogecoin Teases 27% Breakout out of Bollinger Bands as ETF Inflows Hit 3-Week Streak - U.Today |
| -2.87% | whale_position | ONDO | 余烬监测：ondo项目方多签钱包向Coinbase转入超3.28亿枚ondo |
| -2.19% | staking_governance | XRP | XRP price slips 2% on profit taking |
| -1.90% | other | AAVE | 🚨 🚨  20,000 $WETH (42,749,158 USD) transferred from unknown wallet to #Aave  https://t.co/FOjHHUI5nI |
| -1.81% | institutional_flow | AAVE | Bitcoin ETFs Shed $649M in a Day as Long-Term BTC Holders ‘Limit Downside Potential’ - Decrypt |
| -1.79% | hack_security | AAVE | AI Slop Floods Bug Bounty Programs as Companies Struggle with Fake Reports - Decrypt |
| -1.62% | network_upgrade | XRP | Ripple CTO Explains XRPL Hard Forks - U.Today |
| -1.57% | market_structure | XRP | $1.80 or $1.00? Analyst Maps Out XRP's Next Big Move - U.Today |

## Best 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 29.68% | institutional_flow | HYPE | Bitwise to add HYPE to balance sheet using fees from Hyperliquid ETF |
| 28.33% | institutional_flow | HYPE | Bitwise将用10%管理费购买$HYPE |
| 26.92% | network_upgrade | HYPE | 吴说获悉，Hyperliquid 宣布，约一个月后其活跃验证者集合将从 24 个增至 27 个，网络仍将保持当前的无需许可（permissionless）验证机制。官方提醒验证者在主网上线前充分熟悉测试网与相关技术细节，并表示验证者需自质押 |
| 26.64% | other | HYPE | A wallet linked to Anchorage (@Anchorage) bought 397,000 $HYPE ($18M) from #Bybit and #OKX.  Over the past month, the wa |
| 26.32% | institutional_flow | HYPE | Lookonchain：与a16z关联的钱包0xb5e4今日买入37.2万枚HYPE |
| 25.68% | institutional_flow | HYPE | David Schwartz rejects XRP meme coin investment hype after FUZZY rumors |
| 24.80% | other | HYPE | A massive $HYPE buy!  Wallet 0xb5E4, linked to #a16z, bought another 372,000 $HYPE($16.91M) over the past 3 hours.  Sinc |
| 23.11% | staking_governance | HYPE | Hyperliquid price nears ATH as HYPE rallies 24% in 6 days |
| 22.81% | other | HYPE | Persistence pays off!  More than 6 months ago, trader 0x082e opened a 5x long on 1.38M $HYPE ($66.3M), becoming the larg |
| 22.34% | institutional_flow | HYPE | Bitwise HYPE ETF pledges 10% fees to buybacks |

## Worst 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -5.92% | institutional_flow | DOGE | Dogecoin Teases 27% Breakout out of Bollinger Bands as ETF Inflows Hit 3-Week Streak - U.Today |
| -4.22% | other | UNI | CoinDesk 20 performance update: Uniswap (UNI), up 3.7%, leads index higher |
| -3.45% | other | DOGE | I spoke with @jvisserlabs to break down why all-time highs in the stock market are flashing warning signs, how the Iran |
| -2.55% | network_upgrade | XRP | XRP Upgrade Nears Rollout With Critical Fixes Across Several Features - U.Today |
| -1.97% | network_upgrade | XRP | Ripple CTO Explains XRPL Hard Forks - U.Today |
| -1.92% | other | AAVE | 🚨 🚨  20,000 $WETH (42,749,158 USD) transferred from unknown wallet to #Aave  https://t.co/FOjHHUI5nI |
| -1.90% | institutional_flow | XRP | Goldman Sachs Liquidates $154 Million XRP Position via ETF, Pivots to Hyperliquid Treasury - U.Today |
| -1.77% | other | XRP | 🇺🇸 NEW: Sen. Elizabeth Warren questioned OCC approvals for crypto trust charters tied to Coinbase, Ripple and Paxos, per |
| -1.69% | network_upgrade | XRP | Ripple CTO explains XRPL hard forks before 3.1.3 deadline |
| -1.67% | staking_governance | XRP | XRP price slips 2% on profit taking |

## Practical Read

- Among event types with at least 10 rows, strongest 24h average: `other` at 2.74%.
- Among event types with at least 10 rows, strongest 72h average: `other` at 5.95%.
- Benchmark-aware strongest 24h average: `other` at 2.74%.
- Benchmark-aware strongest 72h average: `other` at 5.95%.
- BTC events versus BTC benchmark can flatten abnormal-vs-BTC; use the benchmark-aware table before reading BTC-heavy buckets.
- This is historical replay for source-quality learning, not a live publishing rule.