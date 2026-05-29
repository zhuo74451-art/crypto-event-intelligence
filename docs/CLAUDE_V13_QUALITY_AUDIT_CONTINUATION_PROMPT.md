# Crypto Event Intelligence v13 质量审计后续评审

你是这个项目的外部项目经理和严厉审查人。请不要迎合我，也不要写空泛战略。直接指出当前系统还哪里不可信、哪里应暂停、哪里值得继续投入，并给出下一轮可执行任务。

## 项目目标

我们在做一个加密事件情报系统：把历史快讯、链上/交易所/衍生品等信号转成结构化事件，回填事件发布后 1h/4h/24h/72h 的资产收益和相对 BTC/ETH 的异常收益，用历史结果决定哪些事件类型适合进入 Telegram 群的摘要、观察池、急报或后续验证。

这不是交易系统，不自动下单，不提供买卖/做多/做空建议。当前核心是：用历史数据提升信息筛选和 TG 内容质量。

## 已完成链路

- 真实历史快讯导出、标准化、候选识别、事件构建。
- Binance 价格回填，BTC/ETH 对照收益，abnormal return。
- v08 非 BTC/ETH、非宏观 alt 历史回放 200 条：
  - 回填行数：171
  - 全部 ok/pass
  - 覆盖 10 个事件组
- v12 严格策略：
  - boost_count = 0
  - digest_only_count = 1
  - collect_more_count = 12
  - whale_wallet_position 因 HYPE/单资产/短窗口污染被阻止进入 boost。

## 你上一轮要求的 v13 任务与真实结果

### 1. price-in 检查

脚本：`scripts/validate_price_in_effect.py`

输出：
- `results/v13_price_in_report.csv`
- `results/v13_price_in_summary.csv`
- `results/v13_price_in_report.md`

关键结果：
- output_rows = 171
- whale_wallet_position：
  - total = 59
  - computed = 46
  - severe = 8
  - severe_ratio = 0.1356
  - avg_price_in_ratio = 0.403954
  - status = pass
- exploit_or_theft：
  - total = 36
  - computed = 24
  - severe = 1
  - severe_ratio = 0.0278
  - avg_price_in_ratio = 0.307427
  - status = pass
- etf_or_fund_flow：
  - total = 21
  - severe = 5
  - severe_ratio = 0.2381
  - avg = 0.501532
  - status = pass

初步解释：HYPE 污染不主要是发布前 6h 已 price-in，更像是单资产、单源、短窗口集中导致的样本污染。

### 2. other 质量分级

脚本：`scripts/grade_other_quality.py`

输出：
- `results/v13_other_quality_report.csv`
- `results/v13_other_quality_summary.csv`
- `results/v13_other_quality_report.md`

当前结果：
- uncategorized_rows = 567
- garbage = 446，占 78.66%，建议 archive
- potential = 121，占 21.34%，继续分类
- low = 0

问题：这个分级可能过硬，直接把大量无资产/低相关内容归为 archive，但能有效减少垃圾样本。

### 3. HYPE 专项污染分析

脚本：`scripts/analyze_hype_contamination_detail.py`

输出：
- `results/v13_hype_contamination_detail.csv`
- `results/v13_hype_contamination_summary.csv`
- `results/v13_hype_contamination_report.md`

结果：
- hype_whale_rows = 48
- unique_days = 2
- max_daily_count = 29
- max_daily_ratio = 0.6042
- top_source_count = 34
- top_source_ratio = 0.7083
- top3_source_ratio = 0.9792
- mean_abnormal_vs_btc_24h = 0.09567
- median = 0.079823
- time_pattern = burst
- source_pattern = single_source_dominated
- return_pattern = consistent
- recommended_action = archive_or_digest_only

### 4. whale_position 通用资产污染

脚本：`scripts/analyze_whale_position_asset_contamination.py`

输出：
- `results/v13_whale_asset_contamination_report.csv`
- `results/v13_whale_asset_contamination_summary.csv`
- `results/v13_whale_asset_contamination_report.md`

结果：
- status = fail
- whale_rows = 59
- asset_groups = 6
- downgrade_asset_count = 1
- flagged_asset_count = 6
- top_asset = HYPE
- top_asset_share = 0.8136
- HYPE：
  - event_count = 48
  - asset_share = 0.8136
  - unique_sources = 4
  - top_source = tg:HyperInsight
  - top_source_share = 0.7083
  - timespan_days = 1.4012
  - burst_window_share = 1.0

### 5. source 三层表

脚本：`scripts/build_source_identity_layers.py`

输出：
- `data/source_identity_layers.csv`
- `results/v13_source_identity_summary.csv`
- `results/v13_source_identity_layers.md`

结果：
- source_rows = 23
- candidate_rows = 2000
- backfill_rows = 171
- noisy_source_count = 0
- promising_needs_validation_count = 3
- insufficient_data_count = 18

前几大源：
- webhook：739 candidates，50 backtested，uncategorized_ratio 0.4249，top_event_type uncategorized
- news:jin10：654 candidates，0 backtested，top_event_type macro
- tg:HyperInsight：128 candidates，41 backtested，top_event_type whale_position
- news:cryptonews：82 candidates，11 backtested

### 6. regime 分层

脚本：`scripts/build_regime_layer_report.py`

输出：
- `results/v13_regime_layer_report.csv`
- `results/v13_regime_layer_summary.csv`
- `results/v13_regime_layer_report.md`

结果：
- input_rows = 171
- output_rows = 10
- status = warning
- regime_ready_event_group_count = 0
- data_missing_rows = 0
- 当前 171 条全部落在 btc_range，没有跨 regime 可验证性。

### 7. active_exploit 急报触发器

脚本：
- `scripts/validate_hack_classification.py`
- `scripts/build_active_exploit_urgent_candidates.py`

修正后结果：
- hack_rows = 36
- hack_unclear = 19
- active_exploit = 9
- fund_recovery = 5
- regulatory_enforcement = 2
- security_disclosure = 1
- active_exploit avg_abnormal_vs_btc_24h = 0.001885
- active_exploit win_rate = 0.4444
- urgent_candidate_count = 0
- digest_only_count = 5

说明：修掉了日期/币价被误识别成金额的问题；按当前阈值没有真正急报。

## 当前 TG 产品策略

- 暂停“盘中强推/boost”，因为 boost=0。
- 保留早报、午报、晚报。
- 盘中只发低频“观察池/结构雷达”，但要避免被用户理解成交易信号。
- active_exploit 只保留极少急报触发器，当前历史数据没有触发。

## 需要你继续判断

请基于上面真实结果，给出下一轮完整中文建议。重点回答：

1. v13 结果是否说明我们应该继续暂停盘中雷达？还是可以换一种“弱雷达/观察池”表达？
2. `other` 里 78.66% garbage 是否应该直接 archive？剩下 121 条 potential 下一步怎么处理，是否需要 LLM 分类？
3. HYPE/whale 污染已经确认，下一步是彻底排除 HYPE，还是对 HYPE 单独建桶？
4. source 三层表结果是否足够，应该如何给源打分和限流？
5. regime 分层全部 btc_range，是否说明应该导出更长历史窗口？导出多长、多少条、怎么分层？
6. active_exploit 急报触发器当前 0 条，阈值是否合理？应该接哪些字段或外部源才能让它可靠？
7. 现在最值得继续实现的 5-10 个具体任务是什么？请给脚本名、输入、输出、关键字段、验收标准。
8. 从用户视角看，TG 群接下来应该发什么、不该发什么？卡片里哪些信息必须删掉或换表达？

请直接输出可执行方案，不要写管理学套话。术语尽量用中文，并解释必要术语。
