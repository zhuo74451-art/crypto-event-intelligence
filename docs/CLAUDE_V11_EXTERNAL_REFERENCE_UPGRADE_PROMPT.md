# 给 Claude 的咨询：借鉴外部项目后，重新判断 Crypto Event Intelligence 的升级方向

请用完整中文回答。不要迎合我，也不要只给泛泛规划。你要像一个有经验的产品负责人、量化研究负责人、数据工程负责人联合评审这个项目。

## 项目目标

我们在做一个加密事件情报系统，不是交易系统，不自动下单，不提供买入/卖出/做多/做空建议。

目标是把快讯、链上异动、交易所/稳定币资金流、巨鲸仓位、衍生品拥挤度、代币解锁、CEX 公告等信息，转成结构化事件，发布到 Telegram 群，并在发布后自动回看 1h / 4h / 24h / 72h 的价格表现和 BTC/ETH benchmark 异常收益。

最终想达成的不是“更多消息”，而是：

1. 过滤掉大量交易无关或低质量快讯。
2. 把真正可能有研究价值的信息，变成用户易读的中文情报。
3. 每条情报都有结构化账本。
4. 每条情报都能自动回看效果。
5. 逐步知道哪些来源、事件类型、资产、市场状态下的信息真的有用。
6. 形成一个可被量化研究人员检查的数据包和方法论。

## 当前系统现状

当前已完成：

1. 本地 CSV / SQLite / Python 架构。
2. 原始快讯导入、时间标准化、中国时间统一、事件候选生成。
3. asset / entity / event_type / event_subtype 初步规则识别。
4. Binance 价格回填，计算 BTC / ETH 异常收益。
5. quality report、backtest summary、mature filter、stratified auto50。
6. 真实快讯 older500、小样本回测链路。
7. Telegram 发布链路。
8. 第一批一手 watcher：
   - Ethereum 地址大额转账。
   - 稳定币 mint/burn。
   - CEX netflow。
   - Hyperliquid 大仓位和仓位变化。
   - Binance 大户多空比。
   - Token unlock。
9. TG 盘中雷达：
   - 不是每条都发。
   - 按 interrupt / board / archive / discard 路由。
   - 盘中雷达只发高质量动仓/异动。
   - 静态解锁和静态大仓位默认转早晚报或降权。
10. 每条 TG 情报有 `tg_alert_ledger.csv` 结构化记录。
11. 已接入发布后 outcome evaluation：
   - 1h / 4h / 24h / 72h。
   - asset_return。
   - BTC/ETH abnormal return。
   - pre-event price-in。
   - BTC regime。
12. 已有质量报告：
   - `tg_alert_quality_daily.md`
   - `tg_signal_policy_live.csv`
   - `tg_radar_decision_log.csv`
   - `tg_radar_decision_report.md`
13. 早报 / 午报 / 晚报已定时。
14. 早午晚报现在优先读取结构化 ledger，避免 unknown。
15. 群里已经能看到更清晰的中文卡片，但可读性和内容分层仍需继续提升。

## 最近发现的问题

1. TG 卡片仍可能太像“字段堆叠”，用户不知道哪些是真正关键点。
2. 分数、强度、置信度如果没有解释，会对普通用户不透明。
3. 事件和详情容易重复。
4. 解读不能只是废话，例如“需要结合价格和资金费率综合判断”，这种话信息量低。
5. 盘中雷达需要每 1-2 小时做短摘要，覆盖白天用户查看 TG 和交易的高频时间段，但不能机械刷屏。
6. 静态事实，比如某个 token 解锁，不应每轮盘中都带，只适合早晚报或首次提醒。
7. 需要优先动仓变化，其次静态大仓位。
8. 用户不会认真反馈，所以不能把“用户反馈按钮”作为核心闭环。
9. 样本太少就应该用历史回测扩样本，而不是等用户反馈。
10. 目前源不少，但要证明源是否真的有效。

## 外部项目参考

量化同事给了三个链接：

1. `ZhuLinsen/daily_stock_analysis/docs/README_EN.md`
2. `samgozman/fin-thread`
3. 一个知乎文章，提到类似 Wind / z 类金融情报能力和可参考的 skill prompt 思路。

我初步判断：

### daily_stock_analysis 可借鉴点

它更像股票日评系统，有完整链路：

- watchlist。
- 多数据源。
- AI 分析。
- 决策面板。
- 每日报告。
- 多渠道推送。
- 历史报告。
- 回测。
- 工作区/任务状态。

我们不能照搬它的买卖建议和股票决策面板，但可以学：

1. 多源数据配置层。
2. 每日/定时报告体系。
3. 导入体验。
4. 模型路由和预算控制。
5. 任务状态和历史报告。

### fin-thread 可借鉴点

它更接近我们，是自动金融新闻 Telegram 频道。架构上有：

- Journalist：抓来源。
- Composer：组合、过滤、改写。
- Publisher：发布。
- Archivist：入库和查询。
- Scavenger：经济日历等特殊来源。
- Job：周期任务。

我们可以映射为：

- Watcher / Source Adapter。
- Normalizer。
- Composer。
- Router。
- Publisher。
- Archivist。
- Evaluator。

这可能比我们现在的脚本堆叠更清楚。

### Skill prompt 思路

我们也许应该把稳定工作流沉淀成项目 Skill，而不是每次临时提示词：

- crypto-event-card-composer
- crypto-event-router
- crypto-source-evaluator
- crypto-onchain-watcher
- crypto-backtest-validator

## 当前我的倾向

我倾向于：

1. 不急着部署外部项目。
2. 先拆它们的结构和产品思路。
3. 把我们的系统抽象为 Source Adapter / Normalizer / Composer / Router / Publisher / Archivist / Evaluator。
4. 做 `source_registry.csv`，登记每个源的延迟、可信度、成本、字段、是否适合盘中推送。
5. 做影子源评估：新源先跑不发群，48 小时后用质量报告决定是否接入 TG。
6. 把 TG 主群从“快讯流”改成“情报雷达 + 少量急报 + 早午晚摘要”。
7. 继续强化历史回测和发布后效果回看。

## 请你重点回答

请你不要只说“方向对”。请明确判断：

1. 这个方向是否正确？如果不正确，错在哪里？
2. 我们是不是过早做了 Telegram 产品层，而数据质量层还不够？
3. 我们是不是应该先把架构重构成 Source Adapter / Normalizer / Composer / Router / Publisher / Archivist / Evaluator？
4. 这套架构是否会过度工程？如果会，最小可行版本怎么拆？
5. daily_stock_analysis 哪些东西值得学，哪些不应该学？
6. fin-thread 哪些东西值得学，哪些不应该学？
7. 这些外部项目是否值得本地部署看效果？如果值得，部署谁、看什么指标、看多久？如果不值得，为什么？
8. Telegram 群里的最终用户体验应该长什么样？
9. 盘中雷达、急报、早午晚报三者应该如何分工？
10. 对“分数/强度/置信度”应该怎么表达，才能让用户理解又不构成交易建议？
11. 哪些事件应该直接丢弃？哪些应该入盘中雷达？哪些只进早晚报？
12. 新源接入应该怎么设计 shadow mode 和准入门槛？
13. Claude/LLM 应该用在什么地方，哪些地方不应该用，如何控制成本？
14. 下一版升级方案应该怎么分阶段做？
15. 接下来 7 天最应该做的 10 个具体任务是什么？每个任务要有验收标准。
16. 如果你是量化同事，你最担心这套系统的哪些统计问题？
17. 如果你是 TG 群用户，你最讨厌它发什么，最希望看到什么？
18. 如果你是工程负责人，你会要求先清理哪些架构债？
19. 现在还缺哪些关键数据源？哪些源不要接？
20. 给出你认为最合理的 v1.1 / v1.2 / v1.3 路线图。

## 输出格式要求

请用中文输出，结构清晰，至少包含：

1. 总体判断。
2. 外部项目借鉴清单。
3. 不该照搬的部分。
4. 推荐目标架构。
5. Telegram 产品形态建议。
6. 数据质量和回测建议。
7. LLM 使用和成本控制建议。
8. 是否需要部署外部项目验证。
9. 未来 7 天任务清单。
10. v1.1 / v1.2 / v1.3 路线图。
11. 最严厉的反对意见和风险清单。

请尽量具体，不要输出空泛口号。
