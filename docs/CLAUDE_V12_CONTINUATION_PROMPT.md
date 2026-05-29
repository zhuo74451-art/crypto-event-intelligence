# v12 连续复审：已按上一轮意见落地后的下一步

你上轮指出几个核心问题：

- whale_wallet_position 的强表现可能是 HYPE 污染、追涨新闻、样本选择偏差。
- other 仍然太大，必须继续拆。
- hack_security 要区分真实攻击、旧案追踪、漏洞披露、制裁司法。
- boost 条件必须更严格，不能把污染样本变成盘中强推。
- price-in 和 regime 仍未接入。

我们已经按你的意见做了以下落地：

## 1. Whale contamination 检查

新增：

- `scripts/validate_whale_position_contamination.py`
- `results/v12_whale_position_contamination_summary.csv`
- `results/v12_whale_position_contamination_report.md`

结果：

- whale_rows: 59
- unique_assets: 6
- HYPE count: 48
- hype_ratio: 0.8136
- max_single_asset: HYPE
- max_single_asset_ratio: 0.8136
- timespan_days: 1.4
- status: fail
- flags: `hype_contamination,single_asset_concentration,low_asset_diversity,short_time_span`

结论：

- whale_wallet_position 的强历史表现暂时不能信。
- 已不允许它进入 boost。

## 2. Hack classification 检查

新增：

- `scripts/validate_hack_classification.py`
- `results/v12_hack_classification_report.csv`
- `results/v12_hack_classification_summary.csv`

结果：

- hack_rows: 36
- hack_unclear: 18
- active_exploit: 9
- security_disclosure: 5
- fund_recovery: 3
- protocol_pause: 1

active_exploit:

- sample_count: 9
- avg_abnormal_vs_btc_24h: 0.022348
- win_rate_vs_btc_24h: 0.4444
- routing_hint: digest_or_collect_more

结论：

- active_exploit 样本不足且胜率不足，不允许 boost。
- exploit_or_theft 整体进 digest/collect_more，不进盘中强推。

## 3. Other reclassification

新增：

- `scripts/reclassify_other_with_new_taxonomy.py`
- `data/event_candidates_real_2000_older_v12_reclassified.csv`
- `results/v12_other_reclassification_report.csv`
- `results/v12_other_reclassification_summary.csv`

结果：

- original_other_count: 705
- reclassified_count: 138
- uncategorized_count: 567
- uncategorized_ratio: 0.8043
- status: warning

已拆出的类型：

- product_launch: 36
- regulatory_action: 31
- ecosystem_partnership: 31
- market_sentiment: 20
- tokenomics_change: 18
- community_governance: 2

结论：

- 这版关键词拆桶效果不够，705 个 other 只拆出 138 个，剩余 80% 仍无法解释。

## 4. v12 严格策略

新增：

- `scripts/apply_boost_criteria_v12.py`
- `data/tg_signal_policy_v12.csv`
- `results/v12_boost_criteria_report.csv`
- `results/v12_boost_criteria_summary.csv`

结果：

- policy_rows: 13
- boost_count: 0
- digest_only_count: 1
- collect_more_count: 12
- contamination_failed: true

关键策略：

- whale_wallet_position 原本强表现，但因 HYPE/单资产/时间窗口污染，改为 collect_more。
- exploit_or_theft 历史表现更像背景信息，digest_only。
- 其它均 collect_more。

## 5. 系统接入

已接入：

- `build_tg_market_radar_board.py` 支持 `--v12-signal-policy`
- `run_v09_market_radar_cycle.py` 会刷新：
  - non-benchmark matrix
  - whale contamination
  - hack classification
  - v11 policy
  - v12 strict policy
- 本地和服务器均验证通过。
- 最新雷达卡片已经发到 Telegram 群。

## 现在的问题

1. v12 之后没有任何 boost，这可能是正确的，也可能过于保守。你怎么看？
2. `other` 仍然 80% 未拆开，继续靠关键词可能走不动。下一步应该：
   - 先抽样分析 uncategorized 文本？
   - 做一个规则/LLM 混合分类器？
   - 还是直接把 uncategorized 全部 archive，不浪费时间？
3. whale_position 如果 HYPE 污染这么严重，是应该：
   - 单独做 HYPE 专项，不纳入通用 whale_position？
   - 还是对 Hyperliquid 所有 HYPE 大仓位加更长冷却？
4. active_exploit 只有 9 条样本，真实攻击少但重要。它应该低频急报，还是先 digest/shadow？
5. 下一步你认为应该优先做：
   - price-in 检查
   - regime 分层
   - source_id/source_family/source_channel 三层来源表
   - asset/symbol 补全
   - other 抽样分类
   - 历史窗口按 30-90 / 90-120 / 120-150 滚动回测
6. 请不要泛泛讲，直接给下一轮 5 个具体脚本/表/字段/验收标准。
7. 用户视角：TG 群现在应该继续发盘中雷达吗？还是先只发早午晚报和极少急报？

输出要求：

- 全中文。
- 术语第一次出现要解释。
- 严厉指出我们哪里还错。
- 给出明确下一步顺序。
- 不要给交易建议。
