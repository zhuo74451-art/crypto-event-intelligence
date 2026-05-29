# v0.8 Historical Signal Replay Findings

This report replays older historical event candidates through the same price backfill logic to increase signal sample size. It is research/quality analysis only and is not trading advice.

- total_backfill_rows: 200
- quality_rows: 200

## Backfill Status

| value | count |
|---|---:|
| ok | 200 |

## Quality Status

| value | count |
|---|---:|
| pass | 200 |

## Samples By Event Type

| value | count |
|---|---:|
| macro | 160 |
| hack_security | 20 |
| institutional_flow | 5 |
| other | 4 |
| network_upgrade | 3 |
| token_unlock | 3 |
| halving | 3 |
| staking_governance | 2 |

## Samples By Asset

| value | count |
|---|---:|
| BTC | 152 |
| ADA | 20 |
| ETH | 15 |
| BNB | 7 |
| XRP | 2 |
| SOL | 2 |
| DOGE | 1 |
| AVAX | 1 |

## Event Type Performance

| event_type | rows | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| macro | 160 | 0.00% | 0.04% | -0.11% | -0.06% | 0.62% | 3.12% |
| hack_security | 20 | 0.02% | 0.17% | -0.33% | 0.07% | 10.00% | 35.00% |
| institutional_flow | 5 | 0.02% | 0.05% | -0.24% | -0.50% | 0.00% | 0.00% |
| other | 4 | -0.10% | 0.06% | -0.00% | 0.76% | 25.00% | 50.00% |
| network_upgrade | 3 | -0.04% | 0.16% | 0.13% | 0.06% | 33.33% | 33.33% |
| token_unlock | 3 | 0.01% | 0.06% | -0.73% | -0.56% | 0.00% | 0.00% |
| halving | 3 | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| staking_governance | 2 | -0.04% | 0.06% | -0.79% | -0.75% | 0.00% | 0.00% |

## Benchmark-Aware Event Type Performance

BTC rows use `abnormal_vs_eth`; non-BTC rows use `abnormal_vs_btc`. This reduces BTC benchmark self-comparison flattening.

| event_type | rows | avg_benchmark_aware_1h | avg_benchmark_aware_4h | avg_benchmark_aware_24h | avg_benchmark_aware_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| macro | 160 | -0.05% | -0.27% | 0.14% | 0.18% | 55.62% | 56.25% |
| hack_security | 20 | 0.06% | 0.04% | -0.27% | 0.11% | 20.00% | 45.00% |
| institutional_flow | 5 | -0.03% | -0.13% | 0.07% | -0.23% | 40.00% | 40.00% |
| other | 4 | -0.15% | -0.09% | -0.23% | 0.57% | 25.00% | 50.00% |
| network_upgrade | 3 | 0.04% | 0.13% | 0.51% | 0.42% | 100.00% | 100.00% |
| token_unlock | 3 | 0.11% | 0.06% | -0.13% | 0.04% | 66.67% | 66.67% |
| halving | 3 | 0.01% | -0.03% | 0.77% | 0.78% | 100.00% | 100.00% |
| staking_governance | 2 | -0.04% | 0.06% | -0.79% | -0.75% | 0.00% | 0.00% |

## Best 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 0.53% | hack_security | ETH | Standard Chartered: $4T tokenized by 2028 |
| 0.40% | network_upgrade | ETH | Ethereum Foundation 研究员 Carl Beek 与 Julian Ma 于周一宣布离职。其中，Carl Beek 在以太坊工作约 7 年，曾参与 Beacon Chain 及以太坊 PoS 升级；Julian Ma 在以 |
| 0.37% | hack_security | ETH | Adshares桥攻击者归还256枚ETH，覆盖86%被盗资金 |
| 0.35% | macro | ETH | Ethereum's Vitalik Buterin Explains How AI Could Make Smart Contracts Truly Secure |
| 0.10% | other | AVAX | Stablecoins aren't just a US story.  @John1wu spoke to @LowBeta on what @avax is quietly building across Asia and LatAm: |
| 0.00% | hack_security | BTC | White House: Bitcoin Reserve Announcement Is Imminent |
| 0.00% | institutional_flow | BTC | Leopold Aschenbrenner bets $13.6b on miners |
| 0.00% | institutional_flow | BTC | Delphi Digital：比特币在流动性趋紧背景下表现可能优于多数加密资产 |
| 0.00% | institutional_flow | BTC | Santiment：持有至少100 BTC的钱包数量增至20229 |
| 0.00% | network_upgrade | BTC | In 2019 I sincerely questioned myself whether I wanted to continue trading crypto.  Almost all markets went down, crypto |

## Worst 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -2.19% | token_unlock | XRP | XRP price slips 2% on profit taking |
| -1.37% | macro | DOGE | Revolut launches first physical crypto card |
| -1.37% | macro | XRP | Crude Oil Prices: Brent and WTI Rise as Markets Respond to Trump-Xi Trade Talks |
| -1.30% | macro | ADA | SEC Exemption Tokenized Stock Trading: Report |
| -1.20% | macro | ADA | Galaxy Wins New York BitLicense for Institutional Crypto Services |
| -1.18% | macro | ADA | Binance Inflow Data Explains The Mechanics Behind Ethereum Weakness – Details \| Bitcoinist.com |
| -1.15% | macro | ADA | 3 Factors May Send Bitcoin Price Back To $80K |
| -1.12% | macro | ADA | Odds against Interest Rate Cuts High as New US Fed Chair to be Sworn in |
| -1.06% | macro | ADA | Lawyers Apologize After Fake Claude-Generated Quotes Appear in Trump Layoffs Case - Decrypt |
| -0.97% | macro | ADA | Bitcoin Traders Monitor $74K Support As Sell Pressure Increases |

## Best 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 2.30% | macro | SOL | Messari报告：2026年Q1 Solana链上应用总收入达3.422亿美元 |
| 1.59% | other | AVAX | Stablecoins aren't just a US story.  @John1wu spoke to @LowBeta on what @avax is quietly building across Asia and LatAm: |
| 1.47% | other | SOL | 🔥 UPDATE: Solana’s RWA market just crossed $2.8B, a new all-time high. https://t.co/cUH5EbjwVi |
| 1.37% | macro | BNB | 据 Reuters 调查报道，数据分析显示，自 2023 年以来，受制裁影响的伊朗最大加密交易所 Nobitex 已通过 Tron 和 BNB Chain 网络处理了至少 23 亿美元。报道指出，这两个区块链的创始人孙宇晨与赵长鹏均为特朗普 |
| 1.26% | hack_security | BNB | The XRP Asian Breakout: Japan And South Korea Lead The Charge \| Bitcoinist.com |
| 1.24% | hack_security | BNB | Analyst Predicts Bitcoin And Ethereum Price For The Rest Of 2026, What To Expect \| Bitcoinist.com |
| 1.15% | hack_security | BNB | HYPE Jumps On Bitwise’s Hyperliquid ETF Move—Galaxy Secures BitLicense In NY \| Bitcoinist.com |
| 1.13% | macro | BNB | Bitcoin Bull Market Confirmation Will Be Completed Once This Level Is Reclaimed, Analyst \| Bitcoinist.com |
| 1.00% | hack_security | BNB | Patrick Witt Teases ‘Breakthrough’ On US Bitcoin Reserve |
| 0.82% | hack_security | BNB | XRP’s Recent Strategic Setup Could Mark The End For Bears - Crypto Analyst Says \| Bitcoinist.com |

## Worst 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -1.67% | token_unlock | XRP | XRP price slips 2% on profit taking |
| -1.45% | macro | XRP | Crude Oil Prices: Brent and WTI Rise as Markets Respond to Trump-Xi Trade Talks |
| -1.42% | institutional_flow | ADA | Binance Retail Investor Bitcoin Inflows Drop By 73%, What's Next for BTC? |
| -1.41% | macro | ADA | Binance Inflow Data Explains The Mechanics Behind Ethereum Weakness – Details \| Bitcoinist.com |
| -1.38% | macro | ADA | SEC Exemption Tokenized Stock Trading: Report |
| -1.14% | macro | ADA | Hive Shares Hit Highest Price This Year After Bitcoin Miner Unveils Ontario 'AI Gigafactory' - Decrypt |
| -1.08% | institutional_flow | ADA | Bank of England, FCA Set Out ‘Shared Vision’ for Tokenization - Decrypt |
| -1.07% | macro | ADA | Odds against Interest Rate Cuts High as New US Fed Chair to be Sworn in |
| -1.06% | macro | ADA | Galaxy Wins New York BitLicense for Institutional Crypto Services |
| -0.98% | macro | ADA | 3 Factors May Send Bitcoin Price Back To $80K |

## Practical Read

- Among event types with at least 10 rows, strongest 24h average: `macro` at -0.11%.
- Among event types with at least 10 rows, strongest 72h average: `hack_security` at 0.07%.
- Benchmark-aware strongest 24h average: `macro` at 0.14%.
- Benchmark-aware strongest 72h average: `macro` at 0.18%.
- BTC events versus BTC benchmark can flatten abnormal-vs-BTC; use the benchmark-aware table before reading BTC-heavy buckets.
- This is historical replay for source-quality learning, not a live publishing rule.