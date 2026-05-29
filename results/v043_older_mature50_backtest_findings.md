# v0.4.1 Auto50 Backtest Findings

- Total samples: 37

## Backfill Status
| value | count |
|---|---:|
| ok | 37 |

## Quality Status
| value | count |
|---|---:|
| pass | 37 |

## Samples By Event Type
| value | count |
|---|---:|
| macro | 10 |
| hack_security | 8 |
| other | 5 |
| institutional_flow | 3 |
| token_unlock | 3 |
| network_upgrade | 3 |
| halving | 3 |
| staking_governance | 2 |

## Event Type Abnormal Return
| event_type | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h |
| --- | --- | --- | --- | --- |
| hack_security | 0.001381 | 0.004005 | -0.002579 | -0.002648 |
| halving | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| institutional_flow | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| macro | 0.000239 | 0.001424 | -0.001497 | 0.001187 |
| network_upgrade | -0.000421 | 0.001607 | 0.001334 | 0.000589 |
| other | -0.001623 | 0.002348 | 0.000348 | 0.006548 |
| staking_governance | -0.000375 | 0.000613 | -0.007946 | -0.007456 |
| token_unlock | 0.000147 | 0.000618 | -0.007309 | -0.005572 |

## Event Type Win Rate
| event_type | win_rate_vs_btc_1h | win_rate_vs_btc_4h | win_rate_vs_btc_24h | win_rate_vs_btc_72h |
| --- | --- | --- | --- | --- |
| hack_security | 0.875000 | 0.875000 | 0.250000 | 0.250000 |
| halving | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| institutional_flow | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| macro | 0.200000 | 0.300000 | 0.100000 | 0.200000 |
| network_upgrade | 0.000000 | 0.333333 | 0.333333 | 0.333333 |
| other | 0.000000 | 0.600000 | 0.400000 | 0.600000 |
| staking_governance | 0.500000 | 0.500000 | 0.000000 | 0.000000 |
| token_unlock | 0.333333 | 0.333333 | 0.000000 | 0.000000 |

## Best 10 Events By 24h Abnormal Vs BTC
| event_id | title | event_type | asset_symbol | abnormal_vs_btc_24h |
| --- | --- | --- | --- | --- |
| cand_00375 | Standard Chartered: $4T tokenized by 2028 | hack_security | ETH | 0.005345 |
| cand_00449 | Ethereum Foundation 研究员 Carl Beek 与 Julian Ma 于周一宣布离职。其中，Carl Beek 在以太坊工作约 7 年，曾参与 Beacon Chain 及以太坊 PoS 升级；Julian Ma 在以 | network_upgrade | ETH | 0.004003 |
| cand_00484 | Adshares桥攻击者归还256枚ETH，覆盖86%被盗资金 | hack_security | ETH | 0.003653 |
| cand_00456 | Ethereum's Vitalik Buterin Explains How AI Could Make Smart Contracts Truly Secure | macro | ETH | 0.003498 |
| cand_00423 | 🚨MORE ETHEREUM FOUNDATION RESEARCHERS RESIGN  Ethereum Foundation researchers Carl Beek and Julian Ma have resigned, add | other | ETH | 0.001794 |
| cand_00478 | Stablecoins aren't just a US story.  @John1wu spoke to @LowBeta on what @avax is quietly building across Asia and LatAm: | other | AVAX | 0.001016 |
| cand_00469 | Michael Saylor的策略现已持有超过4%的比特币总供应量 | other | BTC | 0.000000 |
| cand_00324 | Leopold Aschenbrenner bets $13.6b on miners | institutional_flow | BTC | 0.000000 |
| cand_00193 | JUST IN: 100,000 blocks remain until the next Bitcoin Halving. https://t.co/y8wcvN854g | halving | BTC | 0.000000 |
| cand_00213 | Shiba Inu sees 3b SHIB hit exchanges | network_upgrade | BTC | 0.000000 |

## Worst 10 Events By 24h Abnormal Vs BTC
| event_id | title | event_type | asset_symbol | abnormal_vs_btc_24h |
| --- | --- | --- | --- | --- |
| cand_00275 | XRP price slips 2% on profit taking | token_unlock | XRP | -0.021927 |
| cand_00400 | Crude Oil Prices: Brent and WTI Rise as Markets Respond to Trump-Xi Trade Talks | macro | XRP | -0.013665 |
| cand_00160 | 以太坊质押比例上升至31%，长期持有者信心依旧 | staking_governance | ETH | -0.009022 |
| cand_00016 | 5/18 Ethereum ETF Net Flow: $-84.14m $ETHA (BlackRock): –$55.40m $FETH (Fidelity): –$14.70m $ETHW (Bitwise): $0.00m $TET | staking_governance | ETH | -0.006870 |
| cand_00047 | Lookonchain：过去4天内发生3起重大黑客攻击事件 | hack_security | ETH | -0.006251 |
| cand_00094 | 链上监测：过去4天内发生三起重大黑客事件 | hack_security | ETH | -0.006014 |
| cand_00124 | #PeckShieldAlert @dcfgod reports that @EchoProtocol_ was hacked on @monad   The hacker minted 1k $eBTC ($76.7M) &, utili | hack_security | ETH | -0.005919 |
| cand_00117 | Exploit Alert 🚨  According to @dcfgod, @EchoProtocol_ on @monad has been exploited.  The attacker reportedly minted 1,00 | hack_security | ETH | -0.005800 |
| cand_00105 | 链上监测：黑客在Monad平台上铸造1000枚EBTC并洗钱 | hack_security | ETH | -0.005645 |
| cand_00329 | Messari报告：2026年Q1 Solana链上应用总收入达3.422亿美元 | macro | SOL | -0.004804 |

## Suspicious Extreme Return Samples
_No rows._

## Preliminary Notes
- Strongest 24h event_type in this run: network_upgrade.
- Event types with fewer than 5 valid samples are too small to judge: halving, institutional_flow, network_upgrade, staking_governance, token_unlock.
- No suspicious_extreme_return rows were flagged.
