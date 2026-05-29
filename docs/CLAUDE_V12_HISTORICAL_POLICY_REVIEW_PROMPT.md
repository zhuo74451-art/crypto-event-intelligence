# 给 Claude 的 v12 历史样本与路由策略复审请求

你是这个项目的外部项目经理和技术评审。请直接指出问题，不要迎合。

项目目标：

我们在做 Crypto Event Intelligence，加密事件情报系统。目标不是交易机器人，也不是喊单，而是把新闻、链上、CEX/稳定币流向、Hyperliquid 仓位、衍生品指标、解锁等信息转成结构化事件，做历史回测和发布后评价，再决定哪些事件值得进入 Telegram 情报流。

当前产品形态：

- Telegram 群里发中文情报卡片和盘中雷达。
- 本地 CSV / SQLite / Python 脚本为主。
- 服务器只负责 watcher、路由、发送、评价。
- 不做买卖建议，不做自动下单。

这轮我们按你的意见做了什么：

1. 不再等用户反馈，改用历史数据扩样本。
2. 只读导出服务器历史快讯：
   - `data/raw_news_real_2000_older.csv`
   - 时间窗口：当前 UTC 往前 7-180 天
   - pipeline 读取前 2000 条。
3. 跑候选生成、自动建议、成熟过滤：
   - `data/event_candidates_real_2000_older_review.csv`
   - `data/event_candidates_real_2000_older_review_suggested.csv`
   - `data/event_candidates_real_2000_older_mature_review_suggested.csv`
4. 修了一个关键分类问题：
   - 之前 `hack_security` 会被正文里的旧背景事实污染，例如文章正文提到 “Bitfinex hack recovery” 就误判。
   - 现在改成标题优先，正文 hack 只在没有常见旧案背景词时才触发。
5. 拆了 `other`：
   - 新增 `candidate_event_subtype`。
   - 事件样本和回填结果保留 `event_subtype/source_type`。
   - 新增粗粒度分类：`stablecoin_flow`、`project_business`、`onchain_data`、`market_structure`、`ai_infra` 等。
6. 非 BTC/ETH、非 macro 的成熟 alt 历史回测：
   - 之前 older500 只能得到 20 条可用样本。
   - 现在 older2000 得到 171 条，全部 `status=ok`、质量 `pass`。
7. 重新生成：
   - `results/event_type_performance_matrix_non_benchmark_alt.csv`
   - `data/tg_signal_policy_v11.csv`
8. 新策略已接入盘中雷达：
   - 能按历史表现调整 priority。
   - 能按历史弱信号增加 cooldown。
   - 不直接生成交易方向。

当前关键数字：

候选导入：

- total: 2000
- suggest_include_count: 1154
- suggest_fix_count: 1
- suggest_exclude_count: 845
- missing_asset_count: 835
- missing_symbol_count: 876
- unknown_event_type_count: 705
- multi_asset_count: 270
- market_wide_count: 651
- mature_72h_count: 2000

候选 event_type 分布：

- other: 705
- macro: 666
- whale_position: 158
- institutional_flow: 106
- hack_security: 106
- ai_infra: 55
- exchange_listing: 44
- network_upgrade: 43
- staking_governance: 39
- stablecoin_flow: 31
- halving: 22
- project_business: 16
- market_structure: 7
- token_unlock: 2

非基准 alt 回测：

- backfill rows: 171
- quality pass: 171
- event_type_count: 10
- event_type 分布：
  - whale_position: 59
  - hack_security: 36
  - institutional_flow: 21
  - other: 20
  - staking_governance: 10
  - network_upgrade: 9
  - stablecoin_flow: 7
  - exchange_listing: 4
  - halving: 4
  - project_business: 1

事件子类型分布：

- whale_wallet_position: 59
- exploit_or_theft: 36
- etf_or_fund_flow: 21
- needs_taxonomy_review: 20
- staking_or_governance: 10
- upgrade_or_fork: 9
- stablecoin_supply_or_flow: 7
- listing_delisting: 4
- halving: 4
- rwa_tokenization: 1

非基准矩阵：

- matrix_rows: 56
- insufficient_sample_count: 52
- promising_needs_validation_count: 3

v11 路由策略：

- policy_rows: 62
- boost_count: 1
- digest_only_count: 3
- collect_more_count: 35
- review_benchmark_count: 23
- 当前唯一 boost 是 `whale_wallet_position`，34 个 24h 样本，`avg_abnormal_primary_24h≈0.0873`，`win_rate≈0.9412`，但仍标记为 `promising_needs_validation`。

现在我需要你做的不是泛泛规划，而是逐条评审以下问题，并给出可落地修改建议：

1. 这次扩大历史样本和拆 `other` 的方向是否正确？哪里仍然错？
2. `whale_wallet_position` 出现非常强的历史表现，是否可能是样本选择偏差、HYPE 污染、新闻追涨、价格先动后报道造成的？应该如何验证？
3. 现在 `other` 仍有 20/171 回测样本、候选里仍有 705 条，下一步应该拆哪些具体子类型？请给出关键词和字段建议。
4. `hack_security/exploit_or_theft` 现在 36 条，但历史表现偏弱。是应该降低实时权重，还是因为分类仍脏？如何区分真实安全事件、旧案追踪、制裁/司法新闻、协议暂停？
5. 我们是否应该把 `source_type` 从来源名称改成更稳定的 `source_id/source_family/source_channel` 三层？如果要改，具体字段怎么设计？
6. 当前 strategy policy 只给 1 个 boost，是否过于保守？哪些条件下才允许 boost/downrank/digest_only？
7. 我们现在还没有真正做 price-in 检查和 regime 分层。这一步应该怎么接入现有 CSV 回测链路？请给字段和最小规则。
8. 候选里 missing_asset/missing_symbol 很多。应该优先修资产识别，还是接受它们进入 archive/shadow？哪些资产必须补 symbol_map？
9. 当前 TG 盘中雷达应该如何使用这份历史 policy？哪些东西绝对不该发盘中，只能进早午晚报？
10. 如果今天继续做，你认为最该落地的 5 个脚本/表是什么？请按优先级给字段、验收标准。
11. 请用用户视角再挑刺：如果用户是白天看 TG 的交易/研究用户，现有雷达、早午晚报、急报分别应该怎么分工？
12. 请明确指出不该继续做的方向，尤其是会制造噪音、伪量化或过度工程的事情。

输出要求：

- 全中文。
- 术语第一次出现请解释。
- 不要只给概念，要给具体文件、字段、规则、验收标准。
- 请严厉一点，指出真实问题。
- 不要生成买卖建议或交易信号。
