# v1.1 外部项目借鉴后的升级方案

更新时间：2026-05-28 UTC+8

输入：

- `docs/CLAUDE_V11_EXTERNAL_REFERENCE_UPGRADE_PROMPT.md`
- `results/v11_claude_external_reference_upgrade_plan.md`
- `docs/CLAUDE_V11_EXTERNAL_REFERENCE_UPGRADE_CONTINUATION_PROMPT.md`
- `results/v11_claude_external_reference_upgrade_plan_continuation.md`

## 结论

方向基本正确，但当前最容易跑偏的地方是：产品层和卡片层推进太快，数据质量和源有效性证明还不够。

Telegram 不应该被当成最终产品来优先打磨，而应该先被当成“实验前端”和“结构化数据采集前端”。每条发出去或没发出去的情报，都必须能回答：

1. 为什么被选中或被过滤？
2. 来自哪个源？
3. 属于什么事件类型？
4. 发布后 1h / 4h / 24h / 72h 表现如何？
5. 是否已经 price-in？
6. 在什么 BTC / 市场状态下有效或失效？

## 对 Claude 建议的修正

Claude 建议“搭建最小 Telegram Bot 并收集真实用户反馈”。这条不直接采纳，原因：

1. 我们已经有 Telegram 发布链路和定时任务。
2. 用户不会稳定、认真反馈，不能把点赞/踩作为核心闭环。
3. 当前真正可靠的反馈是历史回测和发布后 outcome。

因此改成：

- 保留 TG 群作为实验前端。
- 不依赖用户反馈按钮。
- 用 `tg_alert_ledger.csv`、`tg_radar_decision_log.csv`、`tg_alert_outcomes.csv`、`tg_alert_quality_daily.md` 作为核心反馈闭环。
- 用户视角只用于内容密度、阅读顺序、发送时间窗口，不作为统计依据。

## 外部项目怎么借鉴

### daily_stock_analysis

借鉴：

1. 数据源配置层。
2. 定时报告体系。
3. LLM 调用和预算控制。
4. 历史报告归档。

不借鉴：

1. 买卖建议。
2. 股票技术指标面板。
3. 股票 watchlist 思维。
4. 面向散户投资决策的“决策面板”。

是否部署：

- 不建议真实部署。
- 最多本地读代码/跑样例，提炼报告结构、调度、LLM 封装。

### fin-thread

借鉴：

1. Journalist / Composer / Publisher / Archivist / Job 这种角色分层。
2. 去重和推送频率控制。
3. Telegram 新闻频道的节奏。
4. 结构化 source/job 组织方式。

不借鉴：

1. 纯新闻改写模式。
2. 无回测、无 outcome 的转发流。
3. 单一 TG 输出渠道。

是否部署：

- 可以影子部署 3-7 天，但不是主线。
- 目的不是抄代码，而是观察：
  - 它怎么控制刷屏。
  - 它怎么做标题和摘要。
  - 它如何去重。
  - 它发出来的内容与我们系统差异在哪里。

## 推荐目标架构

短期不全量重构，只做会立即减痛的部分。

### P0：必须马上强化

1. Source Adapter：所有源输出统一事件字段。
2. Source Registry：登记所有源的延迟、成本、可信度、状态、是否 shadow mode。
3. Archivist：统一事件账本、发送账本、过滤账本、结果账本。
4. Evaluator：输出源、事件类型、资产、市况分层下的效果。

### P1：下一阶段

1. Router：基于历史表现和当前状态决定 interrupt / board / digest / archive / discard。
2. Shadow Mode：新源先跑不发群，过质量门槛再上线。
3. LLM Router：按任务选择小模型/强模型，记录成本。

### P2：暂缓

1. Web Dashboard。
2. 用户反馈按钮。
3. 复杂 ML。
4. 大规模泛新闻源。
5. 个性化订阅。

## Telegram 形态

### 急报

每天 0-3 条。

只发：

1. 极端链上/交易所资金异动。
2. 大仓位突变或接近清算。
3. 重大安全事件。
4. 明确超出 rolling baseline 的异常。

### 盘中雷达

每 1-2 小时可以跑，但不一定每次发。

只发这段时间真正新增的有效信号：

1. 动仓变化优先。
2. 静态大仓位降权。
3. 静态解锁只进早晚报或首次出现。
4. 冷却期内不重复。

### 早午晚报

固定中国时间。

重点：

1. 早报：昨夜到今早 Top 5。
2. 午报：上午 Top 3。
3. 晚报：全天 Top 10 + 质量回看。
4. 周报：本周哪些事件类型/源有效。

## 卡片表达规则

不要再用黑盒表达：

- 强度 8.5。
- 置信度 0.82。
- 重要性 ★★★★。
- “需要综合判断”。

改成：

1. 历史类似事件样本数。
2. 同类事件过去表现。
3. 当前事件为什么异常。
4. 数据源可信度。
5. 当前市况限制。
6. 明确说明“历史统计，不构成交易建议”。

示例：

```text
BTC 大额流入 Binance

金额：约 2.5 亿美元
异常性：高于近 30 天同类流入 95% 分位
历史样本：过去 90 天类似事件 18 次
4h 后异常收益：均值 -0.8%，12/18 次为负
当前市况：BTC 14 日趋势向上，历史跌幅通常收窄

仅供市场结构观察，不构成交易建议。
```

## 数据质量重点

接下来先补四张核心表：

1. `data/source_registry.csv`
2. `results/source_effectiveness_report.csv`
3. `results/event_type_performance_matrix.csv`
4. `results/signal_decay_curve.csv`

同时继续强化：

1. pre-event price-in。
2. BTC/ETH benchmark 污染处理。
3. BTC / ETH 事件单独分桶。
4. 市场状态 regime 分层。
5. 混淆事件标记。

## LLM 使用原则

应该用：

1. 原始快讯结构化抽取。
2. 实体消歧。
3. 多源合并去重辅助。
4. 周报和质量报告的中文摘要。

不应该用：

1. 价格计算。
2. 统计检验。
3. 每条事件深度解读。
4. 生成交易建议。
5. 用废话掩盖没有统计结论。

成本控制：

1. 规则先筛掉 70%-90% 垃圾。
2. 低成本模型批量抽取。
3. 强模型只处理复杂合并、周报、架构咨询。
4. 所有 LLM 调用记录到成本账本。
5. 相同文本 hash 缓存。

## 未来 7 天任务

### 1. source registry

产出：

- `data/source_registry.csv`
- `scripts/build_source_registry_report.py`
- `results/source_registry_report.csv`

验收：

- 当前所有源都有 source_id、source_type、latency、cost、confidence、shadow_mode、enabled。

### 2. source effectiveness report

产出：

- `scripts/build_source_effectiveness_report.py`
- `results/source_effectiveness_report.csv`
- `results/source_effectiveness_report.md`

验收：

- 能按 source_type / source_id 输出 sent、skipped、computed_1h、computed_4h、avg_abnormal、false_positive_like_count。

### 3. event type performance matrix

产出：

- `scripts/build_event_type_performance_matrix.py`
- `results/event_type_performance_matrix.csv`

验收：

- 按 event_type / event_subtype / asset_tier / btc_regime 聚合表现。

### 4. signal decay curve

产出：

- `scripts/build_signal_decay_curve.py`
- `results/signal_decay_curve.csv`

验收：

- 每类事件输出 1h / 4h / 24h / 72h 的异常收益均值、中位数、可计算样本数。

### 5. source adapter schema

产出：

- `docs/SOURCE_ADAPTER_SCHEMA.md`
- `scripts/validate_source_adapter_outputs.py`

验收：

- watcher 输出字段统一，缺字段能报 warning。

### 6. shadow mode pipeline

产出：

- `data/shadow_events_raw.csv`
- `scripts/run_shadow_source_evaluation.py`
- `results/shadow_source_evaluation_report.md`

验收：

- 新源可跑 48 小时不发群，只产生日志和质量报告。

### 7. card evidence renderer

产出：

- `scripts/render_tg_evidence_snippet.py`

验收：

- TG 卡片能显示“历史样本数/异常性/当前市况”，不用黑盒分数。

### 8. digest quality upgrade

产出：

- 升级 `scripts/build_tg_morning_digest.py`

验收：

- 早午晚报不再像流水账，按“最重要事件 / 结构信号 / 背景信息 / 质量回看”分层。

### 9. LLM budget tracker

产出：

- `data/llm_usage_ledger.csv`
- `scripts/build_llm_usage_report.py`

验收：

- 每次 OpenRouter 调用记录 task_type、model、tokens、估算成本、cache_hit。

### 10. v1.1 readiness report

产出：

- `scripts/build_v11_readiness_report.py`
- `results/v11_readiness_report.md`

验收：

- 明确列出哪些源可以发群，哪些只能 shadow，哪些应该丢弃。

## 路线图

### v1.1：信号质量地基

目标：

- 不扩大源，先证明已有源是否有效。

做：

- source registry。
- source effectiveness。
- event type matrix。
- signal decay。
- shadow mode。
- digest 改版。

不做：

- Web。
- 用户反馈按钮。
- 复杂 ML。
- 新大源扩张。

验收：

- 每天能回答“哪些源今天有效，哪些是噪音”。

### v1.2：路由和表达升级

目标：

- 让 TG 群内容基于历史表现和当前状态自动降噪。

做：

- Router v2。
- evidence-based card。
- 早午晚报增强。
- 周报。
- LLM budget tracker。

不做：

- 交易建议。
- 个性化订阅。
- App。

验收：

- 每条推送都有 why_now 和历史样本依据。

### v1.3：量化协作包

目标：

- 能把系统输出交给量化同事严肃评审。

做：

- quant export package。
- known issues。
- data dictionary。
- event/outcome/regime 数据。
- 相似事件检索。

不做：

- 自动策略。
- 自动下单。
- 用户商业化。

验收：

- 量化同事能直接用 CSV 做独立验证。

## 最大风险

1. 样本量不足导致伪结论。
2. 事件和价格关系不是因果，只是相关。
3. LLM 生成看似专业但无统计依据的话。
4. TG 群刷屏导致用户忽略。
5. 静态背景被重复发送。
6. 源延迟太大，事件已 price-in。
7. BTC/ETH benchmark 污染。
8. 新源接太多，质量闭环跟不上。
9. 代码脚本越来越多，缺统一 schema。
10. 过早做产品包装，掩盖数据质量不足。

## 下一步只做一件事

先做 `source_registry.csv` 和 `source_effectiveness_report`。

原因：

- 不知道源质量，就无法决定该发什么。
- 不知道源质量，TG 卡片再好也只是包装。
- 不知道源质量，新接更多源只会放大噪音。
