# Claude 问题逐条执行方案

更新：2026-05-28 UTC+8

目的：把 Claude 对项目提出的每个关键问题转成我们自己的明确方案，避免只“摘录观点”而没有落地动作。

## 0. 后续 Claude 对话规则

以后给 Claude 的提示词默认加上：

1. 请使用中文回答。
2. 如必须使用英文术语，请在第一次出现时给中文解释。
3. 不要输出乱码示例，不要用英文模板替代中文业务表达。
4. 结论必须落到可执行任务、字段、脚本、验收标准。
5. 如果质疑当前方向，直接指出，并给替代路径。

## 1. “超额收益到底相对什么？”

问题本质：现在 `abnormal_vs_btc` / `abnormal_vs_eth` 不够严谨。BTC 事件相对 BTC 回测会被压成 0，ETH 事件相对 ETH 也类似。

我们的方案：

- BTC 事件：默认不看 `vs_btc`，改看 `vs_eth` 和 `vs_alt_basket`。
- ETH 事件：默认看 `vs_btc`，可补 `vs_alt_basket_ex_eth`。
- Altcoin 事件：默认看 `vs_btc` 和 `vs_eth`。
- 小币事件：增加 `vs_sector`，例如 L1、DeFi、Meme、交易所币、RWA。
- 后续高级版：用过去 30 天估算该资产对 BTC 的 beta，计算 beta 调整后的异常收益。

需要新增字段：

- `benchmark_primary`
- `benchmark_secondary`
- `abnormal_primary_1h/4h/24h/72h`
- `abnormal_secondary_1h/4h/24h/72h`
- `beta_to_btc_30d`
- `beta_adjusted_abnormal_1h/4h/24h/72h`

验收标准：

- BTC 样本不再用 `abnormal_vs_btc` 作为主结论。
- 汇总报告中明确显示“本事件使用哪个 benchmark”。

## 2. “什么才算一个事件？”

问题本质：`event_type` 太粗，很多事件被混进同一个桶，回测结果不可解释。

我们的方案：

新增 `event_subtype`，把事件拆成更可检验的小类：

- `whale_position_static_large`：静态大仓位。
- `whale_position_size_change`：仓位明显变化。
- `whale_position_near_liquidation`：接近清算。
- `cex_netflow_inflow_spike`：交易所流入异常。
- `cex_netflow_outflow_spike`：交易所流出异常。
- `stablecoin_mint`：稳定币增发。
- `stablecoin_cex_inflow`：稳定币流入交易所。
- `funding_extreme_positive`：资金费率极端偏正。
- `funding_extreme_negative`：资金费率极端偏负。
- `long_short_crowding_extreme`：多空拥挤极端。
- `token_unlock_team_large`：团队/贡献者大额解锁。
- `token_unlock_investor_large`：投资人大额解锁。
- `security_exploit_confirmed`：已确认攻击/盗币。
- `security_soft_warning`：安全软信号。

新增文件：

- `data/event_hypothesis_registry.csv`

字段：

- `event_type`
- `event_subtype`
- `hypothesis_cn`
- `expected_observation`
- `required_fields`
- `minimum_threshold`
- `known_false_positives`
- `tg_priority`

验收标准：

- 新发 TG 情报至少 80% 带 `event_subtype`。
- 回测汇总按 `event_subtype` 输出，而不是只按 `event_type`。

## 3. “事件是导致价格变化，还是价格变化导致事件被注意？”

问题本质：很多快讯是滞后的。价格先动，快讯后发，这种不能当作提前情报。

我们的方案：

所有事件拆三个时间：

- `event_time`：链上/公告/事件实际发生时间。
- `source_time`：数据源或快讯发布时间。
- `publish_time`：我们发到 TG 的时间。

回测 t0 默认使用：

- 研究历史快讯：`source_time`。
- TG 实盘：`publish_time`。
- 链上一手监控：如果我们能直接监控到，使用 `detected_time`。

新增 price-in 检查：

- `pre_return_15m`
- `pre_return_1h`
- `pre_return_4h`
- `priced_in_flag`
- `priced_in_reason`

初版阈值：

- 1 小时前已上涨/下跌超过 2%，标记 `priced_in_soft`。
- 1 小时前已上涨/下跌超过 5%，标记 `priced_in_hard`。
- 对高波动小币，后续改成“超过过去 30 天小时波动的 1 倍”。

验收标准：

- 每个 outcome report 都分开显示 priced-in 和 non-priced-in 样本表现。

## 4. “选择偏差怎么处理？”

问题本质：我们只回测被选中或发出的事件，会高估系统表现。

我们的方案：

保留四层样本：

1. `raw_events`：原始快讯/原始监控信号。
2. `candidate_events`：被解析成候选事件。
3. `eligible_events`：符合结构化和质量门槛。
4. `published_alerts`：最终发到 TG。

对每层都记录：

- `selection_stage`
- `selection_reason`
- `discard_reason`
- `publish_decision`

评估时输出：

- 候选池总数。
- eligible 比例。
- published 比例。
- 被丢弃但后续大涨/大跌的 missed move。

验收标准：

- 不再只拿 `published_alerts` 证明系统有效。
- 报告里必须显示“我们漏掉了哪些大波动”。

## 5. “这条情报到底帮助用户做什么决定？”

问题本质：不能说买卖，但必须明确用户读完能改善什么观察或决策准备。

我们的方案：

TG 不输出交易建议，输出“观察用途”：

- `风险提示`：安全事件、解锁、极端拥挤。
- `结构变化`：仓位变化、资金流突变、OI/资金费率变化。
- `流动性观察`：稳定币、CEX 净流入/流出。
- `事件跟踪`：公告、升级、ETF、机构流。

每条 TG 卡片增加一个用户能懂的“关注点”，但不写买卖：

- “关注后续是否出现价格跟随或资金费率回落。”
- “关注是否从静态仓位变成主动加仓/减仓。”
- “关注交易所流入是否被现货买盘吸收。”

验收标准：

- 卡片不再重复“事件/详情/解读”。
- 每条最多一个“关注点”，且必须和具体数据相关。

## 6. “怎样知道情报有用，而不是只是好看？”

问题本质：用户反馈不可靠，应该看发布后的客观表现。

我们的方案：

新增 TG 情报评价账本：

- `data/tg_alert_log.sqlite`
- `data/tg_alert_outcomes.csv`
- `results/tg_alert_quality_daily.md`

核心指标：

- `alert_count`：发了多少条。
- `hit_rate_1h/4h/24h`：按事件预期方向的命中率。
- `avg_abnormal_primary_1h/4h/24h`：平均主 benchmark 异常收益。
- `false_alarm_rate`：发出后价格变化小于 0.5% 的比例。
- `repeat_rate`：同资产/同类型重复比例。
- `missed_major_move_count`：大波动但未提前捕捉。

验收标准：

- 每天至少生成一份本地质量报告。
- 后续可选发“昨日情报复盘”到自己测试群，不先发主群。

## 7. “哪些数据源值得加，哪些是干扰？”

问题本质：不是源越多越好，而是能否形成可回测事件。

我们的方案：

保留/优先：

- Hyperliquid 大仓位，但重点是仓位变化和接近清算，不是静态榜单。
- CEX 净流入/净流出，但必须有滚动基线和异常倍数。
- 稳定币增发/销毁/流入交易所，但要和市场状态结合。
- 资金费率、OI、清算簇、长短比极端拥挤。
- 已知地址/实体的一手链上变动。

暂缓：

- 泛新闻源扩张。
- 泛社媒情绪。
- VC 融资公告。
- 没有历史样本的长尾小币源。

新增源必须通过三问：

1. 能否定义明确 `event_subtype`？
2. 是否有价格影响假设？
3. 是否能拿到至少 50 条历史或未来可积累样本？

验收标准：

- 每个新源必须在 `source_registry.csv` 里登记假设、字段、成本、预期用途。

## 8. “AI 分类应该用多少？”

问题本质：完全 AI 分类成本和不可解释性都高；纯规则又可能漏掉语义。

我们的方案：

采用“三层分类”：

1. 规则层：确定性强的信号，必须用规则。
2. AI 辅助层：只用于标题/正文语义复杂、规则无法判断的候选。
3. 人工/延迟复核层：只处理高金额、高影响、低置信度样本。

AI 不直接决定是否发主群；它最多输出：

- `ai_event_type_suggestion`
- `ai_asset_suggestion`
- `ai_summary_cn`
- `ai_uncertainty_reason`

最终发布仍由规则阈值和质量门控制。

成本控制：

- 先批量处理候选，不逐条实时调用高级模型。
- 常见模板不用 AI。
- 相同 raw_id / title 哈希命中缓存。
- 每日设置最大调用数和最大费用。

验收标准：

- AI 输出不直接覆盖规则字段。
- 所有 AI 判断要保留原文和原因，方便审计。

## 9. “如何跟量化协作者分工？”

我们的方案：

我们负责：

- 数据抓取。
- 事件结构化。
- 时间标准化。
- 价格回填。
- TG 产品形态。
- 数据包导出。

量化负责：

- 检查样本偏差。
- 设计异常收益和 benchmark。
- 设计统计检验。
- 做样本外验证。
- 判断哪些 event_subtype 有研究价值。
- 给出字段和特征改进建议。

第一次交流不问“能不能预测”，只问：

1. 这批数据第一眼最大问题是什么？
2. 你会先验证哪 3 个事件假设？
3. benchmark 应该怎么选？
4. price-in 阈值怎么设？
5. regime 最小可用版本是什么？
6. 你需要哪些字段才能认真测？
7. 哪些样本应该直接排除？
8. 如果只做 2 周，最有价值的交付是什么？

验收标准：

- 会前给对方一个数据包，不是口头描述项目。
- 会后形成行动项，不泛聊。

## 10. “准备给量化的数据包是什么？”

新增目录：

- `data/quant_export/`

文件：

- `events.csv`：全部结构化事件。
- `alerts.csv`：发到 TG 的情报。
- `outcomes.csv`：后续收益和异常收益。
- `prices.csv`：需要复核的价格点或 OHLCV 样本。
- `data_dictionary.md`：字段解释。
- `known_issues.md`：已知问题。
- `sample_tg_posts.md`：TG 展示样例。
- `research_questions.md`：我们希望验证的问题。

验收标准：

- 对方不看代码也能理解数据。
- 每个字段能追溯来源。

## 11. “不要做什么？”

短期明确不做：

- Web 后台。
- 自动交易。
- 用户登录。
- 个性化订阅。
- 复杂机器学习。
- 泛社媒情绪大模型。
- 大规模新源扩张。
- 低延迟高频交易架构。

原因：

- 这些会消耗工程时间，但不能证明情报有效。
- 当前瓶颈是“信号质量和评价闭环”，不是“展示和功能丰富度”。

## 12. “下一步要改善哪些具体问题？”

按优先级：

1. 修正文档里中英文/编码/术语混乱问题，保证所有核心规划中文可读。
2. 新增 TG alert ledger。
3. 接入发送脚本，让每条 TG 情报有 `alert_id`。
4. 新增 outcome evaluator。
5. 新增 price-in 和 regime baseline。
6. 新增 event_subtype 和假设注册表。
7. 新增每日 signal quality report。
8. 新增 quant export package。
9. 用报告结果反向调低低质量事件。
10. 再考虑新源扩展。

## 13. 最小可交付版本定义

真正可称为下一版效果的标准：

1. TG 群继续发简洁中文雷达。
2. 后台每条发出的雷达都有结构化记录。
3. 第二天能看到这条雷达 1h/4h/24h 后是否有效。
4. 一周后能知道哪些类别该多发，哪些该少发。
5. 可以把数据包交给量化人员直接讨论。

如果没有这五点，再多接源都算堆功能。
