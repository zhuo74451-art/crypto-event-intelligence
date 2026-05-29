# v0.6 Clean Low-Risk Preview

input_rows: 50
selected_low_risk_rows: 22
excluded_medium_risk_rows: 17
excluded_high_risk_rows: 11

## Interpretation

- This file is a conservative preview subset only.
- It excludes medium/high asset-attribution risk rows.
- It is too small for statistical event-type conclusions.
- It can be used as a sanity-check sample before deciding whether to build a v0.6-filtered backtest branch.

## By Event Type

| event_type | count |
|---|---:|
| regulation_macro | 6 |
| institutional_flow | 6 |
| project_business | 4 |
| onchain_data | 2 |
| whale_position | 1 |
| hack_security | 1 |
| stablecoin_flow | 1 |
| network_upgrade | 1 |

## By Asset

| asset | count |
|---|---:|
| BTC | 7 |
| ETH | 6 |
| HYPE | 4 |
| DOGE | 2 |
| AVAX | 1 |
| SOL | 1 |
| ONDO | 1 |

## Selected Rows

| candidate_id | event_type | asset | route | title |
|---|---|---|---|---|
| cand_00077 | whale_position | HYPE | alpha_candidate | Whale Loracle.hl (@loraclexyz) has further increased his $HYPE (5x) short position to 1.44M $HYPE, valued at $69.3M with |
| cand_00419 | regulation_macro | BTC | macro_policy | White House: Bitcoin Reserve Announcement Is Imminent |
| cand_00074 | onchain_data | BTC | alpha_candidate | Santiment：持有至少100 BTC的钱包数量增至20229 |
| cand_00484 | hack_security | ETH | alpha_candidate | Adshares桥攻击者归还256枚ETH，覆盖86%被盗资金 |
| cand_00304 | institutional_flow | BTC | macro_policy | Kraken revenue hits $507m in Q1 despite slump |
| cand_00112 | regulation_macro | BTC | macro_policy | Galaxy Digital wins New York BitLicense |
| cand_00339 | regulation_macro | BTC | macro_policy | JUST IN: Pro-Bitcoin Kevin Warsh to be sworn in as Federal Reserve Chair this Friday 👀🇺🇸 https://t.co/61p7sCHfHu |
| cand_00016 | institutional_flow | ETH | research_only | 5/18 Ethereum ETF Net Flow: $-84.14m $ETHA (BlackRock): –$55.40m $FETH (Fidelity): –$14.70m $ETHW (Bitwise): $0.00m $TET |
| cand_00064 | institutional_flow | HYPE | research_only | 🔥 BULLISH: Bitwise announces it will hold $HYPE on its balance sheet, allocating 10% of its Hyperliquid ETF (BHYP) manag |
| cand_00160 | institutional_flow | ETH | research_only | 以太坊质押比例上升至31%，长期持有者信心依旧 |
| cand_00365 | institutional_flow | HYPE | research_only | Bitwise将用10%管理费购买$HYPE |
| cand_00478 | stablecoin_flow | AVAX | research_only | Stablecoins aren't just a US story.  @John1wu spoke to @LowBeta on what @avax is quietly building across Asia and LatAm: |
| cand_00482 | institutional_flow | HYPE | research_only | Bitwise to add HYPE to balance sheet using fees from Hyperliquid ETF |
| cand_00449 | network_upgrade | ETH | research_only | Ethereum Foundation 研究员 Carl Beek 与 Julian Ma 于周一宣布离职。其中，Carl Beek 在以太坊工作约 7 年，曾参与 Beacon Chain 及以太坊 PoS 升级；Julian Ma 在以 |
| cand_00227 | project_business | DOGE | research_only | Revolut推出首张实体加密卡，主打Dogecoin主题 |
| cand_00456 | regulation_macro | ETH | macro_policy | Ethereum's Vitalik Buterin Explains How AI Could Make Smart Contracts Truly Secure |
| cand_00134 | project_business | DOGE | macro_policy | Revolut launches first physical crypto card |
| cand_00423 | project_business | ETH | research_only | 🚨MORE ETHEREUM FOUNDATION RESEARCHERS RESIGN  Ethereum Foundation researchers Carl Beek and Julian Ma have resigned, add |
| cand_00457 | project_business | SOL | research_only | 🔥 UPDATE: Solana’s RWA market just crossed $2.8B, a new all-time high. https://t.co/cUH5EbjwVi |
| cand_00392 | onchain_data | ONDO | alpha_candidate | 🔥 BULLISH: Tokenized stocks on Ondo Finance crossed $1.5B in TVL, with Ondo’s top five assets making up 25% of the secto |
| cand_00402 | regulation_macro | BTC | macro_policy | NYDIG warns US crypto market-structure bill could 'fail' if August window is missed |
| cand_00414 | regulation_macro | BTC | macro_policy | 代币化国债总额创历史新高达137亿美元 |
