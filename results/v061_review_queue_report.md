# v0.6.1 Review Queue Report

This report is for manual QA before any TG publishing is connected.

## Counts
- total: 500
- publish review queue: 69
- other review queue: 210
- discard audit sample: 80

## Publish Decision Distribution
| value | count |
|---|---:|
| discard | 431 |
| human_review | 69 |

## Event Type L1 Distribution
| value | count |
|---|---:|
| other_review | 210 |
| regulation_macro | 132 |
| whale_position | 37 |
| institutional_flow | 36 |
| project_business | 19 |
| hack_security | 18 |
| network_upgrade | 10 |
| market_structure | 7 |
| onchain_data | 6 |
| token_supply | 5 |
| staking_governance | 5 |
| stablecoin_flow | 5 |
| exchange_listing | 4 |
| legal_enforcement | 4 |
| halving | 2 |

## Discard Reason Distribution
| value | count |
|---|---:|
| missing_entity,duplicate_non_primary,other_review,low_crypto_relevance | 148 |
| (blank) | 69 |
| duplicate_non_primary | 61 |
| duplicate_non_primary,low_crypto_relevance | 39 |
| low_crypto_relevance | 28 |
| low_relevance | 16 |
| duplicate_non_primary,other_review,low_crypto_relevance | 14 |
| opinion_or_analysis,low_crypto_relevance | 10 |
| missing_entity,duplicate_non_primary,opinion_or_analysis,other_review,low_crypto_relevance | 9 |
| missing_entity,low_crypto_relevance | 9 |
| missing_entity,duplicate_non_primary,low_crypto_relevance | 8 |
| other_review | 8 |
| other_review,low_crypto_relevance | 7 |
| missing_entity,duplicate_non_primary,ai_only_non_crypto,low_crypto_relevance | 7 |
| missing_entity,duplicate_non_primary,other_review | 6 |
| scraped_footer_noise | 6 |
| missing_entity,other_review,low_crypto_relevance | 5 |
| ai_only_non_crypto | 4 |
| opinion_or_analysis | 4 |
| duplicate_non_primary,scraped_footer_noise | 4 |
| duplicate_non_primary,ai_only_non_crypto,low_crypto_relevance | 3 |
| missing_entity,duplicate_non_primary,ai_only_non_crypto,other_review,low_crypto_relevance | 3 |
| generic_price_recap | 3 |
| unsupported_asset,other_review | 3 |
| duplicate_non_primary,other_review | 3 |
| duplicate_non_primary,opinion_or_analysis | 2 |
| duplicate_non_primary,opinion_or_analysis,low_crypto_relevance | 2 |
| missing_entity | 2 |
| missing_entity,duplicate_non_primary,generic_price_recap,other_review,low_crypto_relevance | 2 |
| ai_only_non_crypto,low_crypto_relevance | 1 |
| digest_or_market_recap,low_crypto_relevance | 1 |
| digest_or_market_recap | 1 |
| missing_entity,ai_only_non_crypto | 1 |
| duplicate_non_primary,ai_only_non_crypto | 1 |
| generic_price_recap,low_crypto_relevance | 1 |
| opinion_or_analysis,generic_market_commentary | 1 |
| generic_price_recap,other_review | 1 |
| missing_entity,duplicate_non_primary,opinion_or_analysis,low_crypto_relevance | 1 |
| generic_market_commentary | 1 |
| opinion_or_analysis,scraped_footer_noise,generic_price_recap | 1 |
| duplicate_non_primary,generic_price_recap | 1 |
| missing_entity,opinion_or_analysis,low_crypto_relevance | 1 |
| unsupported_asset,duplicate_non_primary | 1 |
| missing_entity,opinion_or_analysis,other_review,low_crypto_relevance | 1 |

## Top Publish Review Rows
| candidate_id | title | primary_asset_symbol | event_type_l1 | publish_decision | relevance_score_realtime | source_count |
| --- | --- | --- | --- | --- | --- | --- |
| cand_00077 | Whale Loracle.hl (@loraclexyz) has further increased his $HYPE (5x) short position to 1.44M $HYPE, valued at $69.3M with | HYPE | whale_position | human_review | 76.5 | 2 |
| cand_00419 | White House: Bitcoin Reserve Announcement Is Imminent | BTC | regulation_macro | human_review | 76.25 | 3 |
| cand_00253 | HIVE soars over 35% on plans for $2.55b Toronto AI 'super factory' | BTC | regulation_macro | human_review | 75.75 | 3 |
| cand_00074 | Santiment：持有至少100 BTC的钱包数量增至20229 | BTC | onchain_data | human_review | 75.0 | 2 |
| cand_00025 | 燕子回来了！💪  「先定 10 个大目标」老哥晒图展示其 $BTC 空单已浮盈 1222.5 万美元，但具体仓位和开仓点位并未露出  05.06 时他止损 BTC 空单最大亏损约 286.7 万美元，这下一把子都回来了 | BTC | whale_position | human_review | 73.5 | 2 |
| cand_00484 | Adshares桥攻击者归还256枚ETH，覆盖86%被盗资金 | ETH | hack_security | human_review | 72.75 | 1 |
| cand_00493 | JUST IN: Strategy $MSTR has generated an 84,987 #Bitcoin gain ($6.6 billion) so far this year, which is already 75% of t | BTC | institutional_flow | human_review | 72.0 | 2 |
| cand_00304 | Kraken revenue hits $507m in Q1 despite slump | BTC | institutional_flow | human_review | 72.0 | 2 |
| cand_00047 | Lookonchain：过去4天内发生3起重大黑客攻击事件 | ETH | hack_security | human_review | 70.75 | 1 |
| cand_00011 | 黑客攻击Monad Echo协议，损失约7600万美元 | ETH | hack_security | human_review | 70.75 | 1 |
| cand_00117 | Exploit Alert 🚨  According to @dcfgod, @EchoProtocol_ on @monad has been exploited.  The attacker reportedly minted 1,00 | ETH | hack_security | human_review | 70.75 | 1 |
| cand_00339 | JUST IN: Pro-Bitcoin Kevin Warsh to be sworn in as Federal Reserve Chair this Friday 👀🇺🇸 https://t.co/61p7sCHfHu | BTC | regulation_macro | human_review | 70.5 | 2 |
| cand_00112 | Galaxy Digital wins New York BitLicense | BTC | regulation_macro | human_review | 70.5 | 2 |
| cand_00016 | 5/18 Ethereum ETF Net Flow: $-84.14m $ETHA (BlackRock): –$55.40m $FETH (Fidelity): –$14.70m $ETHW (Bitwise): $0.00m $TET | ETH | institutional_flow | human_review | 69.75 | 1 |
| cand_00324 | Leopold Aschenbrenner bets $13.6b on miners | BTC | institutional_flow | human_review | 69.75 | 1 |
| cand_00064 | 🔥 BULLISH: Bitwise announces it will hold $HYPE on its balance sheet, allocating 10% of its Hyperliquid ETF (BHYP) manag | HYPE | institutional_flow | human_review | 69.75 | 1 |
| cand_00160 | 以太坊质押比例上升至31%，长期持有者信心依旧 | ETH | institutional_flow | human_review | 69.75 | 1 |
| cand_00365 | Bitwise将用10%管理费购买$HYPE | HYPE | institutional_flow | human_review | 69.75 | 1 |
| cand_00478 | Stablecoins aren't just a US story.  @John1wu spoke to @LowBeta on what @avax is quietly building across Asia and LatAm: | AVAX | stablecoin_flow | human_review | 69.75 | 1 |
| cand_00482 | Bitwise to add HYPE to balance sheet using fees from Hyperliquid ETF | HYPE | institutional_flow | human_review | 69.75 | 1 |
| cand_00124 | #PeckShieldAlert @dcfgod reports that @EchoProtocol_ was hacked on @monad   The hacker minted 1k $eBTC ($76.7M) &, utili | BTC | hack_security | human_review | 69.25 | 1 |
| cand_00105 | 链上监测：黑客在Monad平台上铸造1000枚EBTC并洗钱 | BTC | hack_security | human_review | 69.25 | 1 |
| cand_00041 | 近三天囤积的 ETH 数量增长至 6627.79 枚，价值 1427.6 万美元😆  「曾在 2016 年以均价 $3.45 建仓 11004 枚 $ETH 并获利 3038 万美金的聪明钱」10 小时前再次于链上买入 1344.18 枚 | ETH | whale_position | human_review | 68.25 | 1 |
| cand_00449 | Ethereum Foundation 研究员 Carl Beek 与 Julian Ma 于周一宣布离职。其中，Carl Beek 在以太坊工作约 7 年，曾参与 Beacon Chain 及以太坊 PoS 升级；Julian Ma 在以 | ETH | network_upgrade | human_review | 68.25 | 1 |
| cand_00227 | Revolut推出首张实体加密卡，主打Dogecoin主题 | DOGE | project_business | human_review | 68.0 | 2 |

## Top Other Review Rows
| candidate_id | title | detected_entity_names | primary_asset_symbol | discard_reason |
| --- | --- | --- | --- | --- |
| cand_00307 | NEW: Scientists warn Canadians to prepare for a U.S. “tick invasion” this summer. |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00313 | NEW: Iran claims U.S.-Israeli drones were spotted over Qeshm Island. |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00325 | JUST IN: Reagan Presidential Library in Simi Valley, CA evacuated as the wildfire rapidly expands. |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00330 | JUST IN: Meta reportedly plans to launch its 10% layoffs on Wednesday, with termination notices going out at 4 a.m. loca |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00333 | JUST IN: Meta reportedly plans to launch its 10% layoffs on Wednesday, with notices going out at 4 a.m. local time. |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00334 | Nuts that this is possible within a day.  This took startups months to land before |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00335 | As wealth grows, portfolios get more complex.   More than half of advisors use models for high-net-worth clients, helpin |  |  | missing_entity,duplicate_non_primary,other_review |
| cand_00348 | 🚨BREAKING: Trump says he has called off the scheduled strike on Iran tomorrow. https://t.co/Nvwrkvtovh |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00359 | Ask him if he’s tried @PhoenixTrade |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00364 | Renaissance https://t.co/t9XP29fMNE |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00368 | NEW: Belarus to begin joint nuclear training drills with Russia. |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00373 | .@vibhu is gpt doping |  |  | missing_entity,duplicate_non_primary,ai_only_non_crypto,other_review,low_crypto_relevance |
| cand_00374 | I sat down with @Gabby_Hoffman to discuss the ground truth of data centers, energy consumption, environmental protection |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00378 | JUST IN: NYC Mayor Mamdani to hold private meetings with Jamie Dimon &amp; David Solomon as he pushes higher taxes. |  |  | missing_entity,duplicate_non_primary,other_review |
| cand_00380 | ⛴️🚢🛳️ |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00381 | 💀💀💀 |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00390 | JUST IN: Iran’s national football team arrives in Turkey for pre-World Cup training camp, with players still awaiting vi |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00305 | 4家公募上报REITs指数基金产品 |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00306 | 巴基斯坦总理：连续表态（共 2 条） |  |  | missing_entity,duplicate_non_primary,opinion_or_analysis,other_review,low_crypto_relevance |
| cand_00309 | 乌克兰总统泽连斯基：乌克兰记录了俄罗斯试图从被占领的克里米亚出口粮食的情况，涉及美国的实体 |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00311 | 乌克兰总统泽连斯基：连续表态（共 2 条） |  |  | missing_entity,duplicate_non_primary,opinion_or_analysis,other_review,low_crypto_relevance |
| cand_00312 | 以色列国防军：在一次袭击中击毙了一名巴勒斯坦伊斯兰圣战组织指挥官 |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00322 | 消息人士：美国提出暂时豁免伊朗石油制裁 |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00323 | 航行警告！渤海北部执行军事任务 |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00326 | 黎巴嫩总统：黎巴嫩的谈判框架包括以色列撤军、停火、军队在边界的部署、难民的回归以及对黎巴嫩的经济或财政援助 |  |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |

## Manual Review Instructions
- Fill `manual_decision` with `approve_publish`, `keep_review`, `discard`, or `fix_taxonomy`.
- Fill manual taxonomy fields only when the automatic L1/L2/asset is wrong.
- Do not connect TG publishing until false positives in this queue are reviewed.
