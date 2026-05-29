# v0.6 Filtered Preview Asset Attribution Audit

total_rows: 50.0
high_risk_rows: 11.0
medium_risk_rows: 17.0
low_risk_rows: 22.0

## Interpretation

- This audit checks whether the preview sample's asset attribution is safe enough for backtest planning.
- High-risk rows should not enter a clean v0.6 backtest without correction or explicit policy approval.
- The audit does not modify source candidates or historical v043 outputs.

## High-Risk Rows

| candidate_id | event_type | asset | route | flags | title |
|---|---|---|---|---|---|
| cand_00493 | institutional_flow | BTC | macro_policy | mentions_other_asset_but_candidate_major,possible_wrong_primary_asset,equity_or_infrastructure_not_token_event | JUST IN: Strategy $MSTR has generated an 84,987 #Bitcoin gain ($6.6 billion) so far this year, which is already 75% of t |
| cand_00178 | legal_enforcement | BTC | research_only | btc_default_without_explicit_btc | 美国司法部：俄亥俄州居民因加密庞氏骗局被判9年监禁 |
| cand_00253 | regulation_macro | BTC | macro_policy | mentions_other_asset_but_candidate_major,equity_or_infrastructure_not_token_event | HIVE soars over 35% on plans for $2.55b Toronto AI 'super factory' |
| cand_00324 | institutional_flow | BTC | research_only | mentions_other_asset_but_candidate_major,possible_wrong_primary_asset | Leopold Aschenbrenner bets $13.6b on miners |
| cand_00041 | whale_position | ETH | alpha_candidate | market_wide_alpha_candidate,market_wide_forced_major_asset,mentions_other_asset_but_candidate_major,possible_wrong_primary_asset,market_wide_without_clear_macro_terms | 近三天囤积的 ETH 数量增长至 6627.79 枚，价值 1427.6 万美元😆  「曾在 2016 年以均价 $3.45 建仓 11004 枚 $ETH 并获利 3038 万美金的聪明钱」10 小时前再次于链上买入 1344.18 枚 |
| cand_00183 | project_business | BTC | research_only | btc_default_without_explicit_btc | 明尼苏达州银行可提供比特币保管服务 |
| cand_00095 | regulation_macro | BTC | macro_policy | equity_or_infrastructure_not_token_event | 美SEC或最快本周推出代币化股票监管框架，华尔街加速布局链上证券 |
| cand_00232 | stablecoin_flow | BTC | macro_policy | market_wide_forced_major_asset,btc_default_without_explicit_btc | 亚洲主导稳定币支付，近三分之二交易量来自亚洲 |
| cand_00479 | stablecoin_flow | BTC | macro_policy | market_wide_forced_major_asset,btc_default_without_explicit_btc | Tempo集成Morpho借贷协议，扩展稳定币支付功能 |
| cand_00137 | regulation_macro | BTC | macro_policy | equity_or_infrastructure_not_token_event,market_wide_without_clear_macro_terms | Ostium与纳斯达克达成合作，推出股票永续合约 |
| cand_00081 | onchain_data | BTC | alpha_candidate | market_wide_alpha_candidate,market_wide_forced_major_asset,equity_or_infrastructure_not_token_event | CryptoSlate 文章表示，RWA 代币化市场链上规模已接近 300 亿美元，但真正进入 DeFi 协议的活跃 TVL 仅约 24.7 亿美元，不到 10%。文章援引 DefiLlama 数据称，债券和货币市场基金、黄金、大宗商品及股 |

## Recommended Use

- Use `asset_attribution_risk=low` rows as the safest preview subset.
- Treat `medium` rows as review candidates.
- Exclude or fix `high` rows before any clean backtest branch.
