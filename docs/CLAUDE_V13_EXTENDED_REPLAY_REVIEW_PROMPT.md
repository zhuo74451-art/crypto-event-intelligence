# Crypto Event Intelligence v13 扩展回测后续评审

你上一轮要求我们先做 P0/P1：排除 HYPE 污染、扩大历史样本、收紧候选识别、source 评分限流、regime 分层。

我已经按你的方向继续做了。请基于下面真实结果继续给下一轮意见，仍然要求：不迎合、不要空泛、中文、直接给可执行任务。尤其请判断现在应该继续扩历史，还是先改 TG 早晚报产品形态。

## 已完成新增任务

### 1. HYPE 污染排除与重新统计

新脚本：
- `scripts/archive_hype_and_recompute_stats.py`

旧 171 条结果：
- archived_rows = 48
- clean_rows = 123
- whale_wallet_position_remaining = 11
- boost_count = 0
- digest_only_count = 2
- collect_more_count = 3

扩展 281 条结果：
- archived_rows = 0
- clean_rows = 281
- whale_wallet_position_remaining = 17
- boost_count = 0
- digest_only_count = 2
- collect_more_count = 5
- insufficient_sample_count = 8

解释：扩展样本时已经在 sample 阶段排除 HYPE whale，所以扩展回测里没有需要 archive 的 HYPE whale。

### 2. 扩展历史导出与回测

远程只读导出：
- `python scripts/export_real_news_older.py --days-ago-min 7 --days-ago-max 365 --limit 5000 --output data/raw_news_real_5000_older_7_365d.csv --timeout 300`

候选管道：
- raw rows loaded = 5000
- candidates = 5000

严格筛选：
- input_candidates = 5000
- archive_count = 2055
- eligible non-benchmark alt = 281
- selected_rows = 281

完整回测：
- `results/v08_historical_replay_non_benchmark_alt_500_price_backfill.csv`
- backfill_rows = 281
- quality ok/pass
- event_type_count = 12

问题：虽然目标是 500，但严格筛选后只有 281；硬凑 500 会引入垃圾。

### 3. 扩展样本事件组表现

扩展 281 条，HYPE whale 排除后：

- exploit_or_theft：
  - sample_count = 86
  - avg_abnormal_vs_btc_24h = 0.002591
  - win_rate_24h = 0.5465
  - route = digest_only
- etf_or_fund_flow：
  - sample_count = 57
  - avg_abnormal_vs_btc_24h = 0.009409
  - win_rate_24h = 0.6316
  - route = digest_only
- needs_taxonomy_review：
  - sample_count = 42
  - avg_abnormal_vs_btc_24h = 0.027382
  - win_rate_24h = 0.8571
  - route = collect_more_after_cleaning
  - 但它不可解释，不能直接作为产品信号。
- upgrade_or_fork：
  - sample_count = 30
  - avg_24h = 0.003302
  - win_rate = 0.4667
  - route = collect_more
- whale_wallet_position：
  - sample_count = 17
  - avg_24h = -0.002254
  - win_rate = 0.6471
  - route = collect_more
- staking_or_governance：
  - sample_count = 16
  - avg_24h = 0.021847
  - win_rate = 0.625
  - route = collect_more
- stablecoin_supply_or_flow：
  - sample_count = 12
  - avg_24h = 0.015499
  - win_rate = 0.75
  - route = collect_more

仍然没有 boost。

### 4. 扩展样本 price-in

新输出：
- `results/v13_extended_price_in_summary.csv`

结果：
- exploit_or_theft：86 total，43 computed，severe_ratio 0.0581，avg_price_in_ratio 0.389246，pass
- etf_or_fund_flow：57 total，29 computed，severe_ratio 0.1228，avg 0.472553，pass
- needs_taxonomy_review：42 total，28 computed，severe_ratio 0.0952，avg 0.324278，pass
- upgrade_or_fork：30 total，21 computed，severe_ratio 0.0667，avg 0.392357，pass
- whale_wallet_position：17 total，9 computed，severe_ratio 0，avg 0.227295，pass

price-in 已不是主要问题。

### 5. 扩展样本 whale 污染

新输出：
- `results/v13_extended_whale_asset_contamination_summary.csv`

结果：
- whale_rows = 17
- asset_groups = 7
- status = pass

HYPE whale 污染已从扩展样本中解决。

### 6. source 三层表与 source 限流

新输出：
- `data/source_identity_layers_v13_extended.csv`
- `data/source_scores_v13_extended.csv`
- `results/v13_extended_source_throttle_rules.csv`

source 评分结果：
- source_rows = 25
- trust_count = 0
- block_count = 15
- 最高分：
  - webhook score=35 throttle
  - news:bitmex_ann score=30 throttle
  - news:binance_ann score=30 throttle
  - news:okx_ann score=30 throttle
  - news:kucoin_ann score=30 throttle
- tg:HyperInsight score=10 block
- news:jin10 score=0 block

解释：没有任何 source >70。当前源不能支持高置信推送。

### 7. regime 分层

新输出：
- `results/v13_extended_regime_layer_summary.csv`

结果：
- input_rows = 281
- output_rows = 15
- status = warning
- regime_ready_event_group_count = 0
- data_missing_rows = 0
- 所有样本仍然是 btc_range。

关键发现：
- 281 条回测样本的 event_time_utc 实际集中在 2026-05-16 到 2026-05-21。
- 即使导出参数是 7-365 天，严格筛选后的有效样本仍集中在很短窗口。
- 这可能意味着：
  1. 远程库可用历史不够长；
  2. 导出使用的时间字段不是源事件时间；
  3. 高质量候选集中在近期；
  4. 规则过度偏向近期样本。

### 8. active_exploit 急报

扩展 hack 分类：
- hack_rows = 86
- active_exploit = 28
- hack_unclear = 31
- fund_recovery = 18
- security_disclosure = 5
- regulatory_enforcement = 3
- protocol_pause = 1

急报候选：
- hack_or_exploit_rows = 12
- urgent_candidate_count = 5

但这些候选仍需要人工/规则复核金额来源，不能直接发。

## 我需要你继续判断

请直接回答并给下一轮任务：

1. 严格筛选后只有 281 条，是否应该继续扩大导出到 10000/20000，还是先修导出时间字段/源时间字段？
2. 全部 regime 仍是 btc_range，最可能的根因是什么？下一步怎么验证？
3. source_score 没有任何 >70，是否说明 TG 当前只能发“事件归档型早晚报”，不能发任何雷达？
4. needs_taxonomy_review 42 条表现最好但不可解释，下一步应该怎么拆？是否值得用 LLM 分类这 42 条？
5. etf_or_fund_flow 和 exploit_or_theft 是否可以成为早晚报固定板块？
6. source 限流规则是否过严？webhook 93 条 clean_backtested 但 score 35，应该拆子源还是继续 throttle？
7. active_exploit urgent_candidate_count=5，下一步是接外部安全源，还是先做金额/上下文校验？
8. 请给下一轮 5-10 个具体脚本/表/验收标准。不要泛泛说。

产品方向上，也请明确：
- TG 下一版到底发什么；
- 哪些模块必须停止；
- 哪些数据质量门槛达到后才能恢复盘中内容。
