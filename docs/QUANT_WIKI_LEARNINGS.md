# Quant Wiki Learnings For Crypto Event Intelligence

Updated: 2026-05-28 UTC+8

Source:

- https://quant-wiki.com/job/quant-job/
- https://quant-wiki.com/start/event-driven/
- https://quant-wiki.com/basic/quant/%E5%9B%9E%E6%B5%8B_Backtesting/
- https://quant-wiki.com/repo/quant_learn/

## What Matters For This Project

Quant Wiki 对我们最有价值的不是岗位求职信息，而是它呈现的量化知识结构：

1. 量化不是“预测一句涨跌”，而是把可测试假设变成数据、特征、回测、风险评估和迭代流程。
2. 事件驱动是一个明确的策略/研究范式，但严肃事件驱动不是堆新闻，而是定义事件、发生时间、可交易窗口、风险来源和收益归因。
3. 回测的核心不是“历史上看起来赚了”，而是保留样本外验证、避免未来函数、避免过拟合，并在不同时间段验证稳健性。
4. 对冲基金内部常见分工可以映射到我们项目：
   - 研究/分析：定义事件假设、解释结果、筛选有价值来源。
   - 数据/工程：抓取、清洗、标准化、回填、质量检查。
   - 风险/组合：处理 benchmark、波动率、regime、容量和误报。
   - 产品/用户：把结果压缩成用户能读懂的 TG 情报。

## Implication

我们不应该把系统定位成“快讯发布器”，而应该定位成：

> Crypto event research data product + Telegram intelligence surface.

也就是：

- 后台是事件研究数据集和评价系统。
- 前台是简洁 TG 情报流。
- 每条发出去的内容都能回到数据表里复盘。

## Useful Concepts To Borrow

### 1. Event-Driven Research

我们的 event_type 需要进一步拆成可检验子类型。

当前过粗：

- whale_position
- institutional_flow
- token_unlock
- market_structure
- other

建议逐步变细：

- whale_position_static_large
- whale_position_size_change
- whale_position_near_liquidation
- cex_netflow_inflow_spike
- cex_netflow_outflow_spike
- stablecoin_treasury_mint
- stablecoin_cex_inflow
- funding_extreme_positive
- funding_extreme_negative
- long_short_crowding_extreme
- token_unlock_team_large
- token_unlock_investor_large
- security_exploit_confirmed
- security_soft_warning

拆分原则：

- 每个 subtype 都要有相对明确的价格影响假设。
- 如果无法写出假设，就先不要进入主群高优先级。

### 2. Backtest Discipline

每条历史/实时事件至少需要：

- event_time：事件实际发生时间。
- source_time：我们知道这件事的时间。
- publish_time：发到 TG 的时间。
- backtest_time：用于回测的 t0，默认应使用 source_time 或 publish_time，避免偷看未来。
- pre_event_return_1h / 4h：判断是否已 price-in。
- post_event_return_1h / 4h / 24h / 72h。
- abnormal return：相对 BTC / ETH / sector / beta-adjusted benchmark。

硬规则：

- 不能用事件真实发生时间替代用户可获得信息的时间。
- 不能只看样本内表现。
- 不能让 BTC 事件和 BTC benchmark 互相抵消后得出无意义结论。
- 不能让 `other` 桶进入严肃结论。

### 3. Quant Collaboration Language

和量化交流时，不要说：

- “我们能不能预测涨跌？”
- “这个信号是不是利好？”
- “能不能做成策略？”

应该说：

- “这是我们定义的事件样本和 source_time。”
- “这是每类事件在 1h/4h/24h/72h 的 abnormal return 分布。”
- “这是 price-in 过滤前后的差异。”
- “这是按 BTC regime 切分后的结果。”
- “这是样本外验证区间。”
- “这是 false positive、coverage、hit rate、information ratio。”

### 4. What To Prepare For A Quant Person

最小数据包：

- `events.csv`
- `alerts.csv`
- `outcomes.csv`
- `prices.csv` 或 price source 说明
- `data_dictionary.md`
- `known_issues.md`
- `sample_tg_posts.md`

必须解释：

- 每个字段如何生成。
- 哪些字段来自原始数据。
- 哪些字段来自规则。
- 哪些字段是估算。
- 哪些样本质量不可信。

### 5. Risk Framework

我们应该把风险概念引入产品和回测：

- 数据风险：源字段错、时间错、symbol 错、API 延迟。
- 统计风险：样本太少、过拟合、多重检验、样本选择偏差。
- 市场风险：regime 不同、流动性不同、BTC beta 污染。
- 产品风险：TG 发太多、用户疲劳、重复静态事实。
- 解释风险：把相关性讲成因果。

## Practical Changes To Project Plan

### P0

继续当前 v1.0 方向：

1. TG alert ledger。
2. post-publish outcome evaluation。
3. daily signal quality report。
4. quant export package。
5. price-in + regime baseline。

### P1

新增：

1. `event_subtype` 字段。
2. event hypothesis registry：
   - subtype
   - expected observation direction
   - required fields
   - minimum magnitude threshold
   - known false positives
3. event_type / subtype performance report。

### P2

建立“研究术语层”和“用户展示层”的映射：

- 研究层：`cex_netflow_inflow_spike`
- 用户层：`交易所资金流入异常`
- TG 层：`USDT 流入 Binance 明显高于近期均值，需观察后续买卖盘吸收`

## Main Takeaway

下一阶段不是继续堆功能，而是把系统做成量化人员能理解和复核的数据产品：

- 有明确事件定义。
- 有可追溯时间。
- 有样本质量。
- 有收益归因。
- 有失败样本。
- 有每日评价。

TG 群只是展示层；真正的资产是结构化事件库和 outcome ledger。
