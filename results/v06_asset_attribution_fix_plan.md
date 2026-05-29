# v0.6 Asset Attribution Fix Plan

This is a non-destructive plan. It does not edit candidates or run backtests.

## Summary

| action | count |
|---|---:|
| keep_for_clean_preview | 22 |
| route_macro_or_research_holdout | 10 |
| exclude_from_clean_backtest | 9 |
| needs_entity_rule_review | 8 |
| keep_for_manual_review | 1 |

## High/Medium Risk Actions

| candidate_id | risk | action | asset | route | reason | title |
|---|---|---|---|---|---|---|
| cand_00493 | high | exclude_from_clean_backtest |  | research_only | non-token/equity/infrastructure reference: MSTR | JUST IN: Strategy $MSTR has generated an 84,987 #Bitcoin gain ($6.6 billion) so far this year, which |
| cand_00178 | high | exclude_from_clean_backtest |  | research_only | BTC default without explicit BTC reference | 美国司法部：俄亥俄州居民因加密庞氏骗局被判9年监禁 |
| cand_00253 | high | exclude_from_clean_backtest |  | research_only | non-token/equity/infrastructure reference: HIVE | HIVE soars over 35% on plans for $2.55b Toronto AI 'super factory' |
| cand_00025 | medium | route_macro_or_research_holdout | BTC | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 燕子回来了！💪  「先定 10 个大目标」老哥晒图展示其 $BTC 空单已浮盈 1222.5 万美元，但具体仓位和开仓点位并未露出  05.06 时他止损 BTC 空单最大亏损约 286.7 万美元， |
| cand_00117 | medium | needs_entity_rule_review | ETH | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | Exploit Alert 🚨  According to @dcfgod, @EchoProtocol_ on @monad has been exploited.  The attacker re |
| cand_00047 | medium | needs_entity_rule_review | ETH | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | Lookonchain：过去4天内发生3起重大黑客攻击事件 |
| cand_00011 | medium | needs_entity_rule_review | ETH | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | 黑客攻击Monad Echo协议，损失约7600万美元 |
| cand_00324 | high | exclude_from_clean_backtest |  | research_only | non-token/equity/infrastructure reference: HIVE | Leopold Aschenbrenner bets $13.6b on miners |
| cand_00124 | medium | needs_entity_rule_review | BTC | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | #PeckShieldAlert @dcfgod reports that @EchoProtocol_ was hacked on @monad   The hacker minted 1k $eB |
| cand_00105 | medium | needs_entity_rule_review | BTC | alpha_candidate | protocol exploit proxy assets require primary-asset policy review | 链上监测：黑客在Monad平台上铸造1000枚EBTC并洗钱 |
| cand_00041 | high | route_macro_or_research_holdout | ETH | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 近三天囤积的 ETH 数量增长至 6627.79 枚，价值 1427.6 万美元😆  「曾在 2016 年以均价 $3.45 建仓 11004 枚 $ETH 并获利 3038 万美金的聪明钱」10 小 |
| cand_00098 | medium | route_macro_or_research_holdout | WLD | research_only | market-wide row should not be alpha_candidate without explicit primary asset | WorldCoin团队将1318枚WLD存入Coinbase |
| cand_00079 | medium | route_macro_or_research_holdout | ONDO | research_only | market-wide row should not be alpha_candidate without explicit primary asset | Ondo项目方多签钱包过去2个月向Coinbase等交易所累计转移超3.28亿枚ONDO |
| cand_00023 | medium | keep_for_manual_review | BTC | macro_policy | medium risk; review before clean backtest | 比特币ETF总净流出达6.49亿美元，创2026年第三大流出 |
| cand_00213 | medium | needs_entity_rule_review | SHIB | research_only | multiple assets or entity mismatch requires dictionary/rule review | Shiba Inu sees 3b SHIB hit exchanges |
| cand_00029 | medium | needs_entity_rule_review | HYPE | alpha_candidate | multiple assets or entity mismatch requires dictionary/rule review | Defillama：Hyperliquid仍维持链上永续合约市场领先地位 |
| cand_00183 | high | exclude_from_clean_backtest |  | research_only | BTC default without explicit BTC reference | 明尼苏达州银行可提供比特币保管服务 |
| cand_00329 | medium | route_macro_or_research_holdout | SOL | research_only | market-wide row should not be alpha_candidate without explicit primary asset | Messari报告：2026年Q1 Solana链上应用总收入达3.422亿美元 |
| cand_00357 | medium | route_macro_or_research_holdout | BTC | research_only | market-wide row should not be alpha_candidate without explicit primary asset | ZachXBT offers $10,000 bounty for evidence against Hong Kong market maker HSBG |
| cand_00142 | medium | route_macro_or_research_holdout | BTC | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 加密市场24小时清算金额达8.55亿美元 |
| cand_00095 | high | exclude_from_clean_backtest |  | research_only | unresolved high risk attribution | 美SEC或最快本周推出代币化股票监管框架，华尔街加速布局链上证券 |
| cand_00232 | high | exclude_from_clean_backtest |  | research_only | BTC default without explicit BTC reference | 亚洲主导稳定币支付，近三分之二交易量来自亚洲 |
| cand_00230 | medium | route_macro_or_research_holdout | HYPE | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 【知名交易员Loracle「 HYPE 空仓 TOP 1」】HYPE 空单 摊平 啦! |
| cand_00009 | medium | route_macro_or_research_holdout | HYPE | research_only | market-wide row should not be alpha_candidate without explicit primary asset | 交易员Loracle加仓HYPE空单20万枚，总规模升至6810万美元 |
| cand_00026 | medium | needs_entity_rule_review | TRX | macro_policy | multiple assets or entity mismatch requires dictionary/rule review | 据 Reuters 调查报道，数据分析显示，自 2023 年以来，受制裁影响的伊朗最大加密交易所 Nobitex 已通过 Tron 和 BNB Chain 网络处理了至少 23 亿美元。报道指出，这两 |
| cand_00479 | high | exclude_from_clean_backtest |  | research_only | BTC default without explicit BTC reference | Tempo集成Morpho借贷协议，扩展稳定币支付功能 |
| cand_00137 | high | exclude_from_clean_backtest |  | research_only | unresolved high risk attribution | Ostium与纳斯达克达成合作，推出股票永续合约 |
| cand_00081 | high | route_macro_or_research_holdout | BTC | research_only | market-wide row should not be alpha_candidate without explicit primary asset | CryptoSlate 文章表示，RWA 代币化市场链上规模已接近 300 亿美元，但真正进入 DeFi 协议的活跃 TVL 仅约 24.7 亿美元，不到 10%。文章援引 DefiLlama 数据称 |

## Use

- Apply this plan only after reviewing the recommended action categories.
- Do not force unsupported assets into BTC/ETH just to make Binance backtests work.
- Keep non-token equity/infrastructure rows out of clean token-price backtests.
