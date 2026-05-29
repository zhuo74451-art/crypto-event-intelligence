# v0.8 Historical Signal Replay Findings

This report replays older historical event candidates through the same price backfill logic to increase signal sample size. It is research/quality analysis only and is not trading advice.

- total_backfill_rows: 20
- quality_rows: 20

## Backfill Status

| value | count |
|---|---:|
| ok | 20 |

## Quality Status

| value | count |
|---|---:|
| pass | 20 |

## Samples By Event Type

| value | count |
|---|---:|
| hack_security | 7 |
| other | 7 |
| institutional_flow | 2 |
| network_upgrade | 2 |
| token_unlock | 1 |
| halving | 1 |

## Samples By Asset

| value | count |
|---|---:|
| ADA | 7 |
| BNB | 5 |
| DOGE | 3 |
| XRP | 2 |
| SOL | 2 |
| AVAX | 1 |

## Event Type Performance

| event_type | rows | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| hack_security | 7 | -0.11% | 0.05% | -0.53% | 0.62% | 0.00% | 71.43% |
| other | 7 | 0.21% | 0.18% | -0.76% | 0.47% | 14.29% | 71.43% |
| institutional_flow | 2 | 0.04% | 0.13% | -0.60% | -1.25% | 0.00% | 0.00% |
| network_upgrade | 2 | 0.21% | 0.25% | -0.34% | -0.66% | 0.00% | 0.00% |
| token_unlock | 1 | 0.04% | 0.19% | -2.19% | -1.67% | 0.00% | 0.00% |
| halving | 1 | 0.16% | 0.25% | -0.89% | -0.43% | 0.00% | 0.00% |

## Benchmark-Aware Event Type Performance

BTC rows use `abnormal_vs_eth`; non-BTC rows use `abnormal_vs_btc`. This reduces BTC benchmark self-comparison flattening.

| event_type | rows | avg_benchmark_aware_1h | avg_benchmark_aware_4h | avg_benchmark_aware_24h | avg_benchmark_aware_72h | win_rate_24h | win_rate_72h |
|---|---:|---:|---:|---:|---:|---:|---:|
| hack_security | 7 | -0.11% | 0.05% | -0.53% | 0.62% | 0.00% | 71.43% |
| other | 7 | 0.21% | 0.18% | -0.76% | 0.47% | 14.29% | 71.43% |
| institutional_flow | 2 | 0.04% | 0.13% | -0.60% | -1.25% | 0.00% | 0.00% |
| network_upgrade | 2 | 0.21% | 0.25% | -0.34% | -0.66% | 0.00% | 0.00% |
| token_unlock | 1 | 0.04% | 0.19% | -2.19% | -1.67% | 0.00% | 0.00% |
| halving | 1 | 0.16% | 0.25% | -0.89% | -0.43% | 0.00% | 0.00% |

## Best 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 0.10% | other | AVAX | Stablecoins aren't just a US story.  @John1wu spoke to @LowBeta on what @avax is quietly building across Asia and LatAm: |
| -0.11% | other | SOL | 🔥 UPDATE: Solana’s RWA market just crossed $2.8B, a new all-time high. https://t.co/cUH5EbjwVi |
| -0.23% | institutional_flow | ADA | Bank of England, FCA Set Out ‘Shared Vision’ for Tokenization - Decrypt |
| -0.28% | network_upgrade | ADA | Cardano Price Analysis: ADA Bears Eye $0.20 Support |
| -0.34% | hack_security | ADA | Ethereum Founder Vitalik Buterin Says AI Verification Could Help Secure Crypto Networks - Decrypt |
| -0.34% | hack_security | BNB | XRP’s Recent Strategic Setup Could Mark The End For Bears - Crypto Analyst Says \| Bitcoinist.com |
| -0.35% | hack_security | BNB | Analyst Predicts Bitcoin And Ethereum Price For The Rest Of 2026, What To Expect \| Bitcoinist.com |
| -0.39% | network_upgrade | ADA | Bitcoin Faces Greater Quantum Computing Risk Than Ethereum, Citi Warns - Decrypt |
| -0.56% | other | DOGE | ⚡️ NEW: Revolut unveiled a physical crypto card with Dogecoin branding and LED tap-to-pay functionality for users in the |
| -0.58% | hack_security | BNB | The XRP Asian Breakout: Japan And South Korea Lead The Charge \| Bitcoinist.com |

## Worst 24h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -2.19% | token_unlock | XRP | XRP price slips 2% on profit taking |
| -1.57% | other | XRP | $1.80 or $1.00? Analyst Maps Out XRP's Next Big Move - U.Today |
| -1.43% | other | DOGE | 吴说获悉，Revolut 宣布推出首张实体加密卡，采用 Dogecoin 主题设计，并配备支付时可点亮的 LED 显示。该卡可在支持 Visa 与 Mastercard 的商户使用，首批面向英国及欧洲经济区（不含匈牙利、瑞士和葡萄牙）用户开 |
| -0.97% | other | SOL | Defillama：Hyperliquid仍维持链上永续合约市场领先地位 |
| -0.96% | institutional_flow | ADA | Binance Retail Investor Bitcoin Inflows Drop By 73%, What's Next for BTC? |
| -0.90% | hack_security | ADA | Ethereum Institutional Adoption Expands: ETH Held In Corporate Reserves Climbs To New Landmark \| Bitcoinist.com |
| -0.89% | halving | ADA | Soluna Q1 Revenue Rises 58% as Data Center Hosting Surpasses Crypto Mining |
| -0.78% | other | DOGE | Revolut推出首张实体加密卡，主打Dogecoin主题 |
| -0.62% | hack_security | BNB | Patrick Witt Teases ‘Breakthrough’ On US Bitcoin Reserve |
| -0.61% | hack_security | BNB | HYPE Jumps On Bitwise’s Hyperliquid ETF Move—Galaxy Secures BitLicense In NY \| Bitcoinist.com |

## Best 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| 1.59% | other | AVAX | Stablecoins aren't just a US story.  @John1wu spoke to @LowBeta on what @avax is quietly building across Asia and LatAm: |
| 1.47% | other | SOL | 🔥 UPDATE: Solana’s RWA market just crossed $2.8B, a new all-time high. https://t.co/cUH5EbjwVi |
| 1.26% | hack_security | BNB | The XRP Asian Breakout: Japan And South Korea Lead The Charge \| Bitcoinist.com |
| 1.24% | hack_security | BNB | Analyst Predicts Bitcoin And Ethereum Price For The Rest Of 2026, What To Expect \| Bitcoinist.com |
| 1.17% | other | SOL | Defillama：Hyperliquid仍维持链上永续合约市场领先地位 |
| 1.15% | hack_security | BNB | HYPE Jumps On Bitwise’s Hyperliquid ETF Move—Galaxy Secures BitLicense In NY \| Bitcoinist.com |
| 1.00% | hack_security | BNB | Patrick Witt Teases ‘Breakthrough’ On US Bitcoin Reserve |
| 0.82% | hack_security | BNB | XRP’s Recent Strategic Setup Could Mark The End For Bears - Crypto Analyst Says \| Bitcoinist.com |
| 0.41% | other | DOGE | ⚡️ NEW: Revolut unveiled a physical crypto card with Dogecoin branding and LED tap-to-pay functionality for users in the |
| 0.09% | other | DOGE | Revolut推出首张实体加密卡，主打Dogecoin主题 |

## Worst 72h Events

| abnormal_vs_btc | event_type | asset | title |
|---:|---|---|---|
| -1.67% | token_unlock | XRP | XRP price slips 2% on profit taking |
| -1.42% | institutional_flow | ADA | Binance Retail Investor Bitcoin Inflows Drop By 73%, What's Next for BTC? |
| -1.41% | other | XRP | $1.80 or $1.00? Analyst Maps Out XRP's Next Big Move - U.Today |
| -1.12% | network_upgrade | ADA | Cardano Price Analysis: ADA Bears Eye $0.20 Support |
| -1.08% | institutional_flow | ADA | Bank of England, FCA Set Out ‘Shared Vision’ for Tokenization - Decrypt |
| -0.56% | hack_security | ADA | Ethereum Institutional Adoption Expands: ETH Held In Corporate Reserves Climbs To New Landmark \| Bitcoinist.com |
| -0.55% | hack_security | ADA | Ethereum Founder Vitalik Buterin Says AI Verification Could Help Secure Crypto Networks - Decrypt |
| -0.43% | halving | ADA | Soluna Q1 Revenue Rises 58% as Data Center Hosting Surpasses Crypto Mining |
| -0.19% | network_upgrade | ADA | Bitcoin Faces Greater Quantum Computing Risk Than Ethereum, Citi Warns - Decrypt |
| -0.03% | other | DOGE | 吴说获悉，Revolut 宣布推出首张实体加密卡，采用 Dogecoin 主题设计，并配备支付时可点亮的 LED 显示。该卡可在支持 Visa 与 Mastercard 的商户使用，首批面向英国及欧洲经济区（不含匈牙利、瑞士和葡萄牙）用户开 |

## Practical Read

- No event_type has at least 10 rows yet; treat all per-type conclusions as weak.
- BTC events versus BTC benchmark can flatten abnormal-vs-BTC; use the benchmark-aware table before reading BTC-heavy buckets.
- This is historical replay for source-quality learning, not a live publishing rule.