# v0.6.2 Review Queue Rule Suggestions

This report suggests rule/dictionary improvements. It does not change publishing decisions by itself.

## Queue Sizes
- scored rows: 500
- publish review rows: 72
- other review rows: 210
- discard audit rows: 80

## Suspected False Positives In Publish Review
| candidate_id | title | primary_asset_symbol | event_type_l1 | publish_decision | relevance_score_realtime | suspected_issue |
| --- | --- | --- | --- | --- | --- | --- |
| cand_00026 | 据 Reuters 调查报道，数据分析显示，自 2023 年以来，受制裁影响的伊朗最大加密交易所 Nobitex 已通过 Tron 和 BNB Chain 网络处理了至少 23 亿美元。报道指出，这两个区块链的创始人孙宇晨与赵长鹏均为特朗普 | TRX | regulation_macro | human_review | 61.75 | macro_or_non_crypto_noise |

## Possible Missed Crypto Rows In Other Review
| candidate_id | title | detected_entity_names | discard_reason |
| --- | --- | --- | --- |
| cand_00359 | Ask him if he’s tried @PhoenixTrade |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00190 | This is what will make or break any perps exchange more then anything else. |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00194 | Accounts that have clicked buttons on @PhoenixTrade can reply |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00221 | Anthropic：所有Claude计划的代币限制翻倍 |  | missing_entity,duplicate_non_primary,other_review,low_crypto_relevance |
| cand_00296 | 上海黄金交易所黄金T+D 5月18日（周一）晚盘盘初上涨0.24%报999.0元/克；上海黄金交易所白银T+D 5月18… |  | missing_entity,duplicate_non_primary,other_review |
| cand_00007 | 上海黄金交易所黄金T+D 5月18日（周一）晚盘收盘下跌0.06%报996.01元/克；上海黄金交易所白银T+D 5月1… |  | missing_entity,duplicate_non_primary,other_review |
| cand_00391 | Yeah these are all nothing 👀 😂  i look under the hood every day too. Polygon has been doing this for a while. how the he | Polygon | unsupported_asset,other_review |
| cand_00182 | 🚨 🚨  20,000 $WETH (42,749,158 USD) transferred from unknown wallet to #Aave  https://t.co/FOjHHUI5nI | Wallet|Wrapped Ether|Aave | unsupported_asset,other_review |
| cand_00393 | MACHI BIG BROTHER: HYPERLIQUIDATED  Machi Big Brother was liquidated for the majority of his trading account. He's down | Machi Big Brother | other_review,low_crypto_relevance |

## Possible Missed Crypto Rows In Discard Audit
| candidate_id | title | detected_entity_names | discard_reason |
| --- | --- | --- | --- |
| cand_00167 | How Did Anthropic’s Claude AI Help Recover 5 BTC Locked Crypto Wallet for 11 Years? | Bitcoin|AI|Wallet | duplicate_non_primary |
| cand_00291 | In 2019 I sincerely questioned myself whether I wanted to continue trading crypto.  Almost all markets went down, crypto | Bitcoin | opinion_or_analysis,generic_market_commentary |
| cand_00053 | Bitcoin Whales Defy $77K Drop as Large Wallets Surge 11% | Bitcoin|ETF|Whale | duplicate_non_primary,opinion_or_analysis |
| cand_00080 | 仅在过去 2 个月时间里，Ondo 项目方的多签钱包就向 Coinbase 等交易所累计转移了超过 3.28 亿枚 $ONDO ($9842 万)。  地址： https://t.co/eqO2dMOrZL https://t.co/3c8 | Ondo|Coinbase|Wallet | duplicate_non_primary |
| cand_00094 | 链上监测：过去4天内发生三起重大黑客事件 | Ethereum|eBTC|US Dollar|Hacker|Lookonchain | duplicate_non_primary |
| cand_00116 | 吴说获悉，Revolut 宣布推出首张实体加密卡，采用 Dogecoin 主题设计，并配备支付时可点亮的 LED 显示。该卡可在支持 Visa 与 Mastercard 的商户使用，首批面向英国及欧洲经济区（不含匈牙利、瑞士和葡萄牙）用户开 | Dogecoin|Revolut|Crypto Card | duplicate_non_primary |
| cand_00242 | ⚡️ NEW: Revolut unveiled a physical crypto card with Dogecoin branding and LED tap-to-pay functionality for users in the | Dogecoin|Revolut|Crypto Card | duplicate_non_primary |
| cand_00070 | 余烬监测：ondo项目方多签钱包向Coinbase转入超3.28亿枚ondo | Ondo|US Dollar|Coinbase|Wallet | duplicate_non_primary |
| cand_00471 | Crypto Funds Post $1B in Outflows as Iran Tensions Weigh on Bitcoin, Ether | Bitcoin|Ethereum|Solana|BNB|XRP|Dogecoin|Cardano|Chainlink|Hyperliquid|Zcash|TRON|Bitcoin Cash|Monero | duplicate_non_primary |
| cand_00472 | XRP’s Recent Strategic Setup Could Mark The End For Bears - Crypto Analyst Says | Bitcoinist.com | Bitcoin|Ethereum|Solana|BNB|XRP|Dogecoin|Bitcoin Cash|Binance|Wallet|Hacker | scraped_footer_noise |
| cand_00049 | 韩国FUI计划收紧加密货币监管，拟对大额交易实施申报义务 | US Dollar | duplicate_non_primary |
| cand_00206 | SEC计划发布创新豁免，允许交易代币化资产 | SEC|RWA | duplicate_non_primary |
| cand_00236 | SEC to ready plan for trading crypto versions of stocks | SEC | duplicate_non_primary |
| cand_00241 | JUST IN: SEC prepares to legalize blockchain-based, tokenized stock trading. | SEC|RWA | duplicate_non_primary |

## Recurring Unknown Ticker-Like Tokens
| token | count |
| --- | --- |
| US | 61 |
| ETF | 25 |
| SMA | 14 |
| EMA | 14 |
| CLARITY | 13 |
| EOS | 12 |
| SEC | 11 |
| SPX | 10 |
| TOP | 10 |
| NAGA | 9 |
| ABC | 9 |
| SV | 9 |
| DXY | 8 |
| WMA | 8 |
| JP | 7 |
| UK | 7 |
| LATEST | 6 |
| UPDATE | 6 |
| KYC | 6 |
| VPN | 6 |
| IT | 6 |
| ES | 6 |
| SG | 6 |
| MY | 6 |
| KR | 6 |
| GAMSTOP | 6 |
| NL | 6 |
| ID | 6 |
| BHYP | 5 |
| MW | 5 |
| BREAKING | 4 |
| INTERESTING | 4 |
| TRUMP | 4 |
| BILLION | 4 |
| BIG | 4 |
| HK | 4 |
| OKX | 4 |
| SATA | 4 |
| LONGITUDE | 4 |
| LED | 4 |

## Recurring Handles
| handle | count |
| --- | --- |
| @phoenixtrade | 4 |
| @vibhu | 2 |
| @gabby_hoffman | 2 |
| @shek_dev | 2 |
| @araghchi | 2 |
| @drpezeshkian | 2 |
| @divestech | 2 |
| @colinwu | 2 |
| @profplum99 | 2 |

## Suggested Next Edits
- Add recurring project tokens only after manual confirmation that they are relevant assets, not webpage footer noise.
- Add deny rules for AI-only / non-crypto tech news that only mention crypto in scraped footer text.
- Add a pure price recap deny rule for rows that only report price movement without a new catalyst.
- Add specific L1/L2 rules for crypto payment/card stories if the product wants payment adoption events.
- Review `Machi`, `Hyperliquid`, `PhoenixTrade`, `Polygon`, `Revolut` rows manually before changing rules.
