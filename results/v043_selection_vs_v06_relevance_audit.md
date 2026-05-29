# v043 Selection vs v0.6 Relevance Audit

selected_rows: 37
matched_v06_rows: 37
v06_human_review_rows: 23
v06_discard_rows: 14
v06_discard_rate: 0.3784
safe_to_use_as_current_evidence: no
recommended_use: historical_baseline_only

## Interpretation

- The older v043 stratified selection includes rows that v0.6 relevance scoring would discard.
- Treat the existing v043 mature50 backtest as a historical baseline, not the cleanest current sample.
- Do not overwrite the historical v043 outputs; build a new v06-filtered sample if direction approves.
- Any event-type conclusion from v043 should mention the discard contamination rate.

## Discard Reason Breakdown

| primary_discard_reason | count |
|---|---:|
| duplicate_non_primary | 8 |
| low_crypto_relevance | 2 |
| generic_price_recap | 1 |
| opinion_or_analysis | 1 |
| generic_market_commentary | 1 |
| scraped_footer_noise | 1 |

## Event Type Impact

| candidate_event_type | selected_count | v06_discard_count | v06_discard_rate |
|---|---:|---:|---:|
| macro | 10 | 5 | 0.5 |
| other | 5 | 2 | 0.4 |
| halving | 3 | 2 | 0.6667 |
| token_unlock | 3 | 2 | 0.6667 |
| hack_security | 8 | 1 | 0.125 |
| institutional_flow | 3 | 1 | 0.3333 |
| network_upgrade | 3 | 1 | 0.3333 |
| staking_governance | 2 | 0 | 0.0 |

## v06 Discarded Selected Rows

| candidate_id | candidate_event_type | v06_type | primary_discard_reason | title |
|---|---|---|---|---|
| cand_00275 | token_unlock | market_structure/price_market_structure | generic_price_recap | XRP price slips 2% on profit taking |
| cand_00193 | halving | halving/halving | duplicate_non_primary | JUST IN: 100,000 blocks remain until the next Bitcoin Halving. https://t.co/y8wcvN854g |
| cand_00487 | other | institutional_flow/etf_or_fund_flow | duplicate_non_primary | Michael Saylor的策略现持有超过4%的比特币总供应量 |
| cand_00146 | institutional_flow | institutional_flow/etf_or_fund_flow | opinion_or_analysis | Delphi Digital：比特币在流动性趋紧背景下表现可能优于多数加密资产 |
| cand_00094 | hack_security | hack_security/exploit_or_theft | duplicate_non_primary | 链上监测：过去4天内发生三起重大黑客事件 |
| cand_00291 | network_upgrade | network_upgrade/upgrade_or_fork | generic_market_commentary | In 2019 I sincerely questioned myself whether I wanted to continue trading crypto.  Almost all markets went down, crypto |
| cand_00053 | halving | onchain_data/wallet_metric | duplicate_non_primary | Bitcoin Whales Defy $77K Drop as Large Wallets Surge 11% |
| cand_00455 | macro | regulation_macro/bitcoin_reserve_policy | duplicate_non_primary | 🔥HUGE: White House Executive Director says an announcement on a Strategic Bitcoin Reserve is coming soon. |
| cand_00400 | macro | regulation_macro/macro | low_crypto_relevance | Crude Oil Prices: Brent and WTI Rise as Markets Respond to Trump-Xi Trade Talks |
| cand_00388 | macro | institutional_flow/etf_or_fund_flow | scraped_footer_noise | Leading AI day trading bots in 2026: Why most fail, and what actually works |
| cand_00347 | macro | regulation_macro/macro | duplicate_non_primary | Cointelegraph：币安持有超过90亿美元比特币未平仓合约 |
| cand_00303 | macro | regulation_macro/macro | duplicate_non_primary | Kraken parent Payward grows Q1 revenue 3% as derivatives jump 51% |
| cand_00141 | token_unlock | token_supply/unlock_or_supply | low_crypto_relevance | 欧盟官员：伊朗冲突阴影下，欧盟将下调经济增长预期并上调通胀预测 |
| cand_00469 | other | institutional_flow/etf_or_fund_flow | duplicate_non_primary | Michael Saylor的策略现已持有超过4%的比特币总供应量 |
