# v1.0 Signal Quality And Quant Collaboration Plan

Updated: 2026-05-28 UTC+8

Source:

- `docs/CLAUDE_V10_QUANT_COLLABORATION_PROMPT.md`
- `results/v10_claude_quant_collaboration_plan.md`
- `docs/CLAUDE_V10_QUANT_COLLABORATION_CONTINUATION_PROMPT.md`
- `results/v10_claude_quant_collaboration_continuation.md`
- `docs/CLAUDE_QUESTIONS_ACTION_PLAN_CN.md`
- `docs/CLAUDE_CONSULTATION_RULES_CN.md`

## Correction

上一版只提炼了 Claude 的方向，没有逐条回答 Claude 提出的核心问题。已补充中文逐问逐答执行方案：

- `docs/CLAUDE_QUESTIONS_ACTION_PLAN_CN.md`

后续所有 Claude 咨询必须按中文规则执行：

- `docs/CLAUDE_CONSULTATION_RULES_CN.md`

## Core Diagnosis

Claude 的核心判断很直接：

1. 当前系统已经具备数据管线和实时发布能力，但还没有证明“哪些信号真的有用”。
2. 继续接更多源之前，必须先建立每条 TG 情报的发布后评价闭环。
3. Telegram 不是只要更好看，而是要从“快讯流”变成“可追责的情报流”。
4. 量化协作者最应该帮助的是统计方法、特征工程、benchmark/regime/price-in 处理，而不是帮我们抓数据或做产品。
5. 短期不要做 Web Dashboard、复杂 ML、更多泛新闻源、用户账号、个性化筛选。

## System We Want To Reach

目标不是更多提醒，而是一个可验证的市场情报循环：

1. 从新闻、链上、稳定币/CEX 流向、Hyperliquid 持仓、衍生品指标、解锁等来源产生结构化事件。
2. 只把高信息量、低重复、可解释的事件发到 TG。
3. 每条发出的事件都记录结构化 `alert_id`。
4. 自动在 1h / 4h / 24h / 72h 计算：
   - 标的收益
   - BTC / ETH 或 sector benchmark 异常收益
   - 波动率调整收益
   - 是否 price-in
   - 是否命中该事件类型的预期方向
5. 每日生成情报质量报告。
6. 按 event_type / source / entity / regime 逐步提高阈值，削掉低质量事件。

## Immediate Product Rule

TG 群的内容优先级：

1. 动仓、资金流突变、极端衍生品拥挤、重大安全事件。
2. 静态大仓位只在异常、接近清算、知名实体、或冷却期后出现。
3. Token unlock 属于日内背景信息，不应每轮重复。
4. 不显示原始 backend score。
5. 不说买卖方向，不给交易建议。
6. 每条内容必须让用户能明白“为什么这条值得看”。

## Next 2 Weeks Backlog

### P0: TG Alert Outcome Ledger

新增本地 SQLite/CSV 评价账本：

- `data/tg_alert_log.sqlite` 或扩展现有 SQLite。
- 每条 TG 实发或待发情报写入：
  - alert_id
  - published_at_china
  - published_at_utc
  - event_type
  - event_subtype
  - asset_symbol
  - source
  - event_scope
  - magnitude_usd
  - direction_observation
  - confidence_bucket
  - telegram_message_id
  - raw_payload_json

验收：

- TG 发送脚本每发一条都可追踪。
- 即使 Telegram 发送失败，也保留 draft / skipped / failed 状态。

### P0: Post-Publish Evaluation

新增脚本，定时评价过去 72 小时已发布情报：

- `scripts/evaluate_tg_alert_outcomes.py`
- 计算 1h / 4h / 24h / 72h：
  - asset_return
  - btc_return
  - eth_return
  - abnormal_vs_btc
  - abnormal_vs_eth
  - pre_1h_return
  - pre_4h_return
  - priced_in_flag
  - realized_volatility

验收：

- 每天能生成 `results/tg_alert_outcome_report.md`。
- 能回答“昨天发了几条，哪些有后续价格反应，哪些只是噪音”。

### P0: Signal Quality Report

新增每日质量报告：

- 按 event_type 统计命中率、平均异常收益、false alarm 率。
- 按 source 统计有效率。
- 按 asset_symbol 统计重复程度。
- 标出：
  - 低质量来源
  - 低质量 event_type
  - 过度重复资产
  - price-in 严重事件

验收：

- 报告能直接指导“下一轮少发什么，多观察什么”。

### P1: Quant Data Package

为量化交流准备一个最小数据包：

- `data/quant_export/events.csv`
- `data/quant_export/alerts.csv`
- `data/quant_export/outcomes.csv`
- `data/quant_export/known_issues.md`
- `data/quant_export/data_dictionary.md`
- `data/quant_export/sample_tg_posts.md`

重点字段：

- event timestamp 和 source timestamp 分开。
- magnitude 使用 USD、成交量占比、供应量占比、历史 z-score。
- BTC/ETH 事件与 alt 事件分开。
- 明确哪些字段是规则生成，哪些字段是 API 原始值，哪些字段是估算。

### P1: Regime And Price-In Baseline

先做简单版本，不上复杂模型：

- BTC 7d realized volatility 分位数：low / medium / high。
- BTC 14d return：uptrend / downtrend / range。
- 事件前 1h / 4h 标的是否已明显反应。

验收：

- 每条事件都带 `regime_vol`、`regime_trend`、`priced_in_flag`。
- 回测汇总可以按 regime 分组。

### P2: Alert Volume Reduction

目标不是多发，而是减少低质量内容。

建议阈值：

- 每日主群 5-15 条高质量 alert 或 radar item。
- CEX / stablecoin flow 必须高于 rolling baseline 或 z-score。
- static position 必须有接近清算、仓位变化、知名实体、或异常资产暴露。
- long/short ratio 只在极端拥挤时出现。

## Quant Conversation Agenda

### Meeting Goal

不要问“能不能预测市场”。要问：

- 这套 event dataset 是否足够干净？
- 统计方法有没有明显偏差？
- 哪些 event type 最值得先做验证？
- 怎么避免 look-ahead / survivorship / selection bias？
- 哪些特征是量化研究真正需要的？

### Send Before Meeting

1. 项目一页纸简介。
2. 最近 30-90 天事件 CSV。
3. 对应 price/outcome CSV。
4. 数据字典。
5. 已知问题清单。
6. 10 条代表性 TG 情报样例。

### Exact Questions

1. 你看这个事件数据，第一眼最担心什么？
2. 这个 event_type taxonomy 是否能支撑统计分析？
3. abnormal return 应该怎么选 benchmark？
4. BTC / ETH 事件应该怎么和 altcoin 事件分开？
5. pre-event price-in 应该用什么阈值？
6. regime 最小可用版本怎么定义？
7. 用这些事件做 walk-forward test，该怎么切 train/test？
8. 哪些指标能说明这套情报真的有用？
9. 如果你只花 10 小时，会先验证哪 3 个假设？
10. 哪些数据你认为缺了就没法严肃分析？

## Do Not Build Yet

暂时不要做：

- Web Dashboard。
- 复杂 ML / LLM 分类。
- 大规模泛新闻源扩展。
- 用户登录、个性化订阅。
- 实时 WebSocket 高频价格系统。
- 交易策略、下单系统。
- 用户反馈按钮或评分系统。

原因：这些不能解决当前最核心问题：我们还不知道哪些情报真的有效。

## Success Criteria

接下来 2 周的验收标准：

1. 每条 TG 情报都有结构化 alert log。
2. 每条 TG 情报都能自动在 1h / 4h / 24h / 72h 追踪结果。
3. 每天有一份情报质量报告。
4. 能按 event_type / source / asset / regime 看命中率和异常收益。
5. 能准备一份给量化人员看的数据包。
6. 能明确砍掉至少一类低质量 alert。

## Hard Principle

如果一个新功能不能提高以下至少一项，就暂缓：

- 提高情报命中率。
- 降低重复噪音。
- 提高数据可验证性。
- 帮助量化人员判断事件是否有研究价值。
- 帮用户更快理解“这条为什么值得看”。
