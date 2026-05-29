# v0.6 Clean Low-Risk Preview Backtest Findings

- Total samples: 22

## Backfill Status
| value | count |
|---|---:|
| ok | 22 |

## Quality Status
| value | count |
|---|---:|
| pass | 22 |

## Samples By Event Type
| value | count |
|---|---:|
| macro | 7 |
| other | 5 |
| institutional_flow | 4 |
| hack_security | 2 |
| staking_governance | 2 |
| whale_position | 1 |
| network_upgrade | 1 |

## Event Type Abnormal Return
| event_type | avg_abnormal_vs_btc_1h | avg_abnormal_vs_btc_4h | avg_abnormal_vs_btc_24h | avg_abnormal_vs_btc_72h |
| --- | --- | --- | --- | --- |
| hack_security | 0.000256 | 0.000670 | 0.001826 | 0.001744 |
| institutional_flow | -0.001072 | 0.009848 | 0.029176 | 0.194279 |
| macro | 0.000230 | 0.000503 | -0.001455 | 0.000178 |
| network_upgrade | -0.001263 | 0.004821 | 0.004003 | 0.001768 |
| other | 0.000520 | 0.021498 | 0.014544 | 0.049294 |
| staking_governance | -0.000375 | 0.000613 | -0.007946 | -0.007456 |
| whale_position | -0.001802 | -0.003867 | -0.005774 | 0.198987 |

## Event Type Win Rate
| event_type | win_rate_vs_btc_1h | win_rate_vs_btc_4h | win_rate_vs_btc_24h | win_rate_vs_btc_72h |
| --- | --- | --- | --- | --- |
| hack_security | 0.500000 | 0.500000 | 0.500000 | 0.500000 |
| institutional_flow | 0.500000 | 0.500000 | 0.500000 | 0.750000 |
| macro | 0.285714 | 0.142857 | 0.142857 | 0.142857 |
| network_upgrade | 0.000000 | 1.000000 | 1.000000 | 1.000000 |
| other | 0.400000 | 1.000000 | 0.600000 | 1.000000 |
| staking_governance | 0.500000 | 0.500000 | 0.000000 | 0.000000 |
| whale_position | 0.000000 | 0.000000 | 0.000000 | 1.000000 |

## Best 10 Events By 24h Abnormal Vs BTC
| event_id | title | event_type | asset_symbol | abnormal_vs_btc_24h |
| --- | --- | --- | --- | --- |
| cand_00392 | 🔥 BULLISH: Tokenized stocks on Ondo Finance crossed $1.5B in TVL, with Ondo’s top five assets making up 25% of the secto | other | ONDO | 0.078828 |
| cand_00482 | Bitwise to add HYPE to balance sheet using fees from Hyperliquid ETF | institutional_flow | HYPE | 0.062180 |
| cand_00365 | Bitwise将用10%管理费购买$HYPE | institutional_flow | HYPE | 0.062091 |
| cand_00449 | Ethereum Foundation 研究员 Carl Beek 与 Julian Ma 于周一宣布离职。其中，Carl Beek 在以太坊工作约 7 年，曾参与 Beacon Chain 及以太坊 PoS 升级；Julian Ma 在以 | network_upgrade | ETH | 0.004003 |
| cand_00484 | Adshares桥攻击者归还256枚ETH，覆盖86%被盗资金 | hack_security | ETH | 0.003653 |
| cand_00456 | Ethereum's Vitalik Buterin Explains How AI Could Make Smart Contracts Truly Secure | macro | ETH | 0.003498 |
| cand_00423 | 🚨MORE ETHEREUM FOUNDATION RESEARCHERS RESIGN  Ethereum Foundation researchers Carl Beek and Julian Ma have resigned, add | other | ETH | 0.001794 |
| cand_00478 | Stablecoins aren't just a US story.  @John1wu spoke to @LowBeta on what @avax is quietly building across Asia and LatAm: | other | AVAX | 0.001016 |
| cand_00414 | 代币化国债总额创历史新高达137亿美元 | macro | BTC | 0.000000 |
| cand_00304 | Kraken revenue hits $507m in Q1 despite slump | macro | BTC | 0.000000 |

## Worst 10 Events By 24h Abnormal Vs BTC
| event_id | title | event_type | asset_symbol | abnormal_vs_btc_24h |
| --- | --- | --- | --- | --- |
| cand_00134 | Revolut launches first physical crypto card | macro | DOGE | -0.013683 |
| cand_00160 | 以太坊质押比例上升至31%，长期持有者信心依旧 | staking_governance | ETH | -0.009022 |
| cand_00227 | Revolut推出首张实体加密卡，主打Dogecoin主题 | other | DOGE | -0.007847 |
| cand_00064 | 🔥 BULLISH: Bitwise announces it will hold $HYPE on its balance sheet, allocating 10% of its Hyperliquid ETF (BHYP) manag | institutional_flow | HYPE | -0.007568 |
| cand_00016 | 5/18 Ethereum ETF Net Flow: $-84.14m $ETHA (BlackRock): –$55.40m $FETH (Fidelity): –$14.70m $ETHW (Bitwise): $0.00m $TET | staking_governance | ETH | -0.006870 |
| cand_00077 | Whale Loracle.hl (@loraclexyz) has further increased his $HYPE (5x) short position to 1.44M $HYPE, valued at $69.3M with | whale_position | HYPE | -0.005774 |
| cand_00457 | 🔥 UPDATE: Solana’s RWA market just crossed $2.8B, a new all-time high. https://t.co/cUH5EbjwVi | other | SOL | -0.001070 |
| cand_00112 | Galaxy Digital wins New York BitLicense | macro | BTC | 0.000000 |
| cand_00304 | Kraken revenue hits $507m in Q1 despite slump | macro | BTC | 0.000000 |
| cand_00339 | JUST IN: Pro-Bitcoin Kevin Warsh to be sworn in as Federal Reserve Chair this Friday 👀🇺🇸 https://t.co/61p7sCHfHu | macro | BTC | 0.000000 |

## Suspicious Extreme Return Samples
_No rows._

## Preliminary Notes
- Strongest 24h event_type in this run: institutional_flow.
- Event types with fewer than 5 valid samples are too small to judge: hack_security, institutional_flow, network_upgrade, staking_governance, whale_position.
- No suspicious_extreme_return rows were flagged.
