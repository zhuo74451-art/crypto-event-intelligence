????????????????????????????

?????????????????????????????????????/??????????????????????????????????????

???????? 3 ???
1. ???? Golden ??????? 100% ???
2. ETF ????????? 90 ???????????Top ETF ??/???
3. Hyperliquid ??????????????????????

??????????????????????????? 3-5 ??????????????????????????????????????????

## results/v14_adversarial_golden_validation_summary.csv

generated_at_china,sample_count,expected_publishable_rows,actual_publishable_rows,recall,precision_estimate,false_positive_rows,false_negative_rows,boundary_case_count,multi_condition_conflict_count,cohen_kappa_expected_vs_blind,top_rejection_reasons,status
2026-05-28 21:53:38 UTC+8,55,27,34,0.8148,0.6471,12,5,29,29,0.8908,observable_impact_ok:14;source_basis_ok:9;not_price_in_ok:2,pass


## results/v14_adversarial_golden_validation.csv

event_id,event_time_utc,title,content,event_subtype,asset_symbol,source,source_tier,event_time_anchor,observable_impact_type,verification_url,price_in_1h,expected_publishable,blind_label_publishable,boundary_case,conflict_type,notes,actual_publishable,validation_status,criteria_block_reason,computed_source_tier
adv_001,2026-04-02T12:00:00Z,Binance announces emergency listing halt for ABC after contract risk,Binance announces emergency listing halt for ABC after contract risk. Adversarial validation sample for publishable gating.,exchange_halt,ABC,binance,official,announcement_timestamp,exchange_halt,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,official
adv_002,2026-04-03T12:00:00Z,Aave governance executes parameter change reducing LTV for CRV collateral,Aave governance executes parameter change reducing LTV for CRV collateral. Adversarial validation sample for publishable gating.,governance,AAVE,aave_official,official,execution_timestamp,protocol_parameter_change,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,official
adv_003,2026-04-04T12:00:00Z,Tether treasury mints 1B USDT on Ethereum with transaction hash,Tether treasury mints 1B USDT on Ethereum with transaction hash. Adversarial validation sample for publishable gating.,stablecoin_supply_or_flow,USDT,etherscan,onchain_verified,block_timestamp,large_confirmed_flow,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,onchain_verified
adv_004,2026-04-05T12:00:00Z,USDC depegs after issuer confirms banking exposure,USDC depegs after issuer confirms banking exposure. Adversarial validation sample for publishable gating.,stablecoin_supply_or_flow,USDC,circle_official,official,statement_timestamp,depeg,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,official
adv_005,2026-04-06T12:00:00Z,Major exchange pauses SOL withdrawals citing network incident,Major exchange pauses SOL withdrawals citing network incident. Adversarial validation sample for publishable gating.,exchange_halt,SOL,binance,official,status_page_timestamp,withdrawal_pause,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,official
adv_006,2026-04-07T12:00:00Z,Curve pool exploit drains funds from CRV pools with attacker address,Curve pool exploit drains funds from CRV pools with attacker address. Adversarial validation sample for publishable gating.,exploit_or_theft,CRV,peckshield,onchain_or_security_research,tx_timestamp,exploit_loss,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,onchain_or_security_research
adv_007,2026-04-08T12:00:00Z,Ronin bridge exploit confirmed with attacker address and stolen funds,Ronin bridge exploit confirmed with attacker address and stolen funds. Adversarial validation sample for publishable gating.,exploit_or_theft,RON,slowmist,onchain_or_security_research,tx_timestamp,exploit_loss,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,onchain_or_security_research
adv_008,2026-04-09T12:00:00Z,Coinbase announces official listing for NEWCOIN with trading time,Coinbase announces official listing for NEWCOIN with trading time. Adversarial validation sample for publishable gating.,exchange_listing,NEW,coinbase,official,listing_time,official_listing,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,official
adv_009,2026-04-10T12:00:00Z,Protocol mainnet hard fork activated at block height,Protocol mainnet hard fork activated at block height. Adversarial validation sample for publishable gating.,upgrade_or_fork,ETH,ethereum_official,official,activation_block_time,large_operational_change,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,official
adv_010,2026-04-11T12:00:00Z,Large liquidations force close whale ETH position on Hyperliquid,Large liquidations force close whale ETH position on Hyperliquid. Adversarial validation sample for publishable gating.,whale_position,ETH,hyperliquid,onchain_verified,event_timestamp,forced_liquidation,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,onchain_verified
adv_011,2026-04-12T12:00:00Z,MakerDAO executes emergency debt ceiling parameter change,MakerDAO executes emergency debt ceiling parameter change. Adversarial validation sample for publishable gating.,governance,MKR,maker_official,official,execution_timestamp,protocol_parameter_change,https://example.com/validation,0.0,true,true,false,,,true,pass,pass,official
...
adv_048,2026-04-01T12:00:00Z,CEX delisting notice with 12 hours lead time for liquid perpetual,CEX delisting notice with 12 hours lead time for liquid perpetual. Adversarial validation sample for publishable gating.,exchange_listing,PERP,okx,official,announcement_timestamp,official_listing,https://example.com/validation,0.0,true,true,true,event_time_boundary,,true,pass,pass,official
adv_049,2026-04-02T12:00:00Z,Security firm confirms exploit amount after price fell 12 percent,Security firm confirms exploit amount after price fell 12 percent. Adversarial validation sample for publishable gating.,exploit_or_theft,ALT,peckshield,onchain_or_security_research,tx_timestamp,exploit_loss,https://example.com/validation,0.12,false,false,true,price_in_boundary,,false,pass,not_price_in_ok,onchain_or_security_research
adv_050,2026-04-03T12:00:00Z,Protocol shutdown confirmed by multisig transaction,Protocol shutdown confirmed by multisig transaction. Adversarial validation sample for publishable gating.,exchange_halt,DEF,etherscan,onchain_verified,block_timestamp,protocol_shutdown,https://example.com/validation,0.0,true,true,true,source_impact_boundary,,true,pass,pass,onchain_verified
adv_051,2026-04-04T12:00:00Z,ETF daily flow is 96th percentile but from normal month-end rebalance,ETF daily flow is 96th percentile but from normal month-end rebalance. Adversarial validation sample for publishable gating.,etf_or_fund_flow,BTC,farside,onchain_or_security_research,data_timestamp,large_confirmed_flow,https://example.com/validation,0.0,false,false,true,calendar_effect_conflict,,true,fail,pass,onchain_or_security_research
adv_052,2026-04-05T12:00:00Z,Official hard fork completed with fee market change,Official hard fork completed with fee market change. Adversarial validation sample for publishable gating.,upgrade_or_fork,ETH,ethereum_official,official,activation_time,large_operational_change,https://example.com/validation,0.0,true,true,true,impact_scope_boundary,,true,pass,pass,official
adv_053,2026-04-06T12:00:00Z,Whale adds large isolated short within 3 percent of liquidation,Whale adds large isolated short within 3 percent of liquidation. Adversarial validation sample for publishable gating.,whale_position,BTC,hyperliquid,onchain_verified,event_timestamp,forced_liquidation,https://example.com/validation,0.0,true,true,true,risk_threshold_boundary,,true,pass,pass,onchain_verified
adv_054,2026-04-07T12:00:00Z,Regulator files emergency injunction against exchange operations,Regulator files emergency injunction against exchange operations. Adversarial validation sample for publishable gating.,regulation,BNB,court_filing,court_or_regulatory_filing,filing_timestamp,exchange_halt,https://example.com/validation,0.0,true,true,true,source_impact_boundary,,true,pass,pass,court_or_regulatory_filing
adv_055,2026-04-08T12:00:00Z,Unverified screenshot claims exchange insolvency,Unverified screenshot claims exchange insolvency. Adversarial validation sample for publishable gating.,bankruptcy,EXCH,telegram_forward,community_or_unknown,post_timestamp,rumor,https://example.com/validation,0.0,false,false,true,source_quality_boundary,,false,pass,"source_basis_ok,observable_impact_ok",community_or_unknown

## results/v14_etf_daily_digest_with_context_summary.csv

generated_at_china,latest_date,latest_date_sort,latest_total_net_flow_usd,rolling_90d_abs_p95,abs_rank_90d,abs_percentile_90d,avg_30d_net_flow_usd,same_period_last_year_rows,same_period_last_year_avg_usd,is_dynamic_anomaly,top_3_etf_by_share,context_conclusion,status
2026-05-28 21:55:19 UTC+8,27 May 2026,2026-05-27,-733400000.0,640410000.0,2,98.9,-27486666.67,10,204560000.0,true,IBIT:72.0:+14.3pp;GBTC:14.3:+1.9pp;FBTC:8.2:-9.1pp,当前流量显著高于去年同期基线，需要进入晚报背景观察。,pass


## results/v14_etf_daily_digest_with_context.md

## BTC ETF 日频资金流背景

数据日期：27 May 2026｜生成时间：中国时间 2026-05-28 21:55:19 UTC+8
昨日净流：**-7.33 亿美元**，在过去 90 个交易日中绝对值排名第 **2**，分位数 **98.9%**。
动态阈值：90 日绝对流量 95 分位为 **6.40 亿美元**，当前判断：**异常**。

### 历史对比
- 近 30 日均值：-0.27 亿美元
- 去年同期 ±7 天均值：+2.05 亿美元
- 结论：当前流量显著高于去年同期基线，需要进入晚报背景观察。

### Top 3 ETF
| ETF | 流量 | 占比 | 环比变化 |
|---|---:|---:|---:|
| IBIT | -5.28 亿美元 | 72.0% | +14.3pp |
| GBTC | -1.05 亿美元 | 14.3% | +1.9pp |
| FBTC | -0.60 亿美元 | 8.2% | -9.1pp |

读取方式：ETF 日频流量适合放在早晚报，不适合当成盘中即时信号。重点看绝对金额、90 日分位、发行商集中度和是否属于月末/节假日结算效应。

⚠️ 仅作市场结构观察，不构成任何交易建议。


## results/v14_hyperliquid_snapshot_v2_summary.csv

generated_at_china,position_count,total_position_value_usd,previous_total_position_value_usd,total_position_change_pct,long_position_value_usd,short_position_value_usd,long_short_ratio,avg_leverage,hyperliquid_total_open_interest_usd,hyperliquid_total_oi_status,market_share_pct,near_liquidation_10pct_count,near_liquidation_10pct_value_usd,near_liquidation_5pct_count,near_liquidation_5pct_value_usd,baseline_status,baseline_age_hours,status
2026-05-28 21:55:20 UTC+8,5,329883053.54,329313423.33,+0.2%,192847013.93,137036039.61,1.407,9.0,6686970170.26,ok,4.933,0,0,0,0,partial_baseline_less_than_24h,5.24,pass


## results/v14_hyperliquid_snapshot_card_v2.md

## Hyperliquid 市场结构背景

生成时间：中国时间 2026-05-28 21:55:20 UTC+8
监控总规模：**3.30 亿美元**（基线 5.24h 前 3.29 亿美元，+0.2%）
市场占比：**4.933%**（监控仓位 / Hyperliquid 总持仓 66.87 亿美元）
多空比：**1.407 : 1**｜平均杠杆：9.0x

### 风险指标
- 距离清算价 <10%：0 个，合计 0.00 美元
- 距离清算价 <5%：0 个，合计 0.00 美元

### Top 持仓变化
| 标的 | 方向 | 规模 | 24h 变化 | 清算距离 | 实体 |
|---|---:|---:|---:|---:|---|
| HYPE | 空 | 1.03 亿美元 | -16.45 万美元 | 98.6% | loraclexyz |
| ETH | 多 | 7952.00 万美元 | 44.40 万美元 | 40.2% | Matrixport Related |
| HYPE | 多 | 7836.71 万美元 | -12.56 万美元 | 26.9% | Unknown HYPE Whale |
| BTC | 多 | 3495.99 万美元 | 20.96 万美元 | 19.0% | Unknown Hyperliquid Whale |
| BTC | 空 | 3437.52 万美元 | 20.61 万美元 | 183.1% | loraclexyz |

⚠️ 暂无完整 24h 基线，本卡只展示可用的最近历史对比；如果运行满 24h 后仍缺失，需要检查快照落盘。

读取方式：这是市场结构背景。优先观察 24h 增减、清算距离和多空结构；静态大仓位不应反复推送。

⚠️ 仅作市场结构观察，不构成任何交易建议。


## results/project_os_validation_summary.csv

overall_status,blocking_or_fail_count,review_count,total_checks
pass,0,2,28


## results/secret_leak_summary.csv

scanned_root,leak_count,status
C:\Users\PC\Desktop\Projects\事件情报系统,0,pass
