# Crypto Event Intelligence v14 Gate Policy Review

你现在以外部产品负责人 + 量化研究负责人视角审查这个项目。请直接指出问题，不要迎合。

## 项目目标

我们要做的是加密事件情报系统：把历史快讯、链上监控、资金流、巨鲸仓位、CEX/DEX/稳定币/安全事件等信息，转成结构化事件，回测发布后 1h/4h/24h/72h 相对 BTC/ETH 的异常收益，然后只把高质量、可解释、可复盘的市场情报发到 Telegram 群。

不是交易机器人，不自动下单，不给买卖建议。目标是让用户快速看到“值得关注的事件、证据、上下文、历史参考和风险提示”。

## 你上一轮关键批评

你说当前最大问题是用 LLM/总分思维伪装交易信号系统，要求：

1. 增加 PreFilter：价格前置、市场状态、交易时段、资产归因等硬阻断。
2. 拆分 ETF/基金流：ETF 申购赎回、机构披露、CEX netflow、ETF 宏观新闻。
3. 重构 exploit 资产归因：victim protocol / stolen assets / affected tradable assets / primary asset confidence 分离。
4. HistoricalMatcher 用结构化字段匹配，不要 embedding。
5. Composer 删除加权平均，改硬门槛。
6. TG 不展示技术分数，只展示金额、资产、来源、历史参考、价格状态。

## 本轮已经按你意见改的内容

### 1. Flow subtype 拆分

脚本：`scripts/split_flow_event_subtypes.py`

输出字段：
- `refined_subtype`
- `flow_direction`
- `data_source`
- `subtype_confidence`

57 条 flow 行拆分结果：
- `etf_creation_redemption_rows`: 9
- `etf_macro_news_rows`: 32
- `institutional_disclosure_rows`: 4
- `cex_netflow_rows`: 2
- `unclear_rows`: 10

### 2. ETF/Fund filter 加严

脚本：`scripts/filter_etf_fund_flow.py`

只保留 `refined_subtype=etf_creation_redemption` 且标题/语境有严格 ETF/fund/flow 上下文的行。

结果：
- input_rows: 57
- kept_rows: 3
- archived_rows: 54

### 3. Exploit 资产归因重构

脚本：`scripts/verify_exploit_amounts.py`

新增：
- `victim_protocol`
- `victim_protocol_token`
- `victim_protocol_chain`
- `stolen_assets`
- `affected_tradable_assets`
- `primary_tradable_asset`
- `primary_impact_type`
- `primary_asset_confidence`
- `stolen_affected_overlap`

结果：
- active_exploit_rows: 28
- urgent_eligible_count: 0

主要原因：多数 security/hack 事件是误分类、软安全话题、宏观科技安全、或无法证明受影响可交易资产。

### 4. PreFilter

脚本：`scripts/build_v14_prefilter.py`

使用历史数据里的 6h pre-event abnormal 先做 MVP 版本。因为当前没有 5min pre-event 数据。

硬阻断：
- missing tradable asset
- missing Binance symbol
- benchmark asset
- pre-event abnormal 6h abs > 2%
- exploit primary asset confidence < 70%
- chain token attribution weak

结果：
- input_rows: 281
- passed_rows: 173
- blocked_rows: 108

### 5. Composer 改门槛制

脚本：`scripts/build_v14_composer_scores.py`

删除加权平均 `composer_final_score`，改为：
- `composer_gate_passed`
- `composer_block_reason`
- `composer_route_hint`

门槛：
- trading_relevance_score >= 15/20
- attribution_score >= 12/20
- historical_confidence_score >= 10/20

HistoricalMatcher MVP：
- exact key = `event_subtype | asset_symbol | magnitude_bucket`
- similar_count < 3 给低历史置信
- 用历史 1h abnormal、false positive proxy、win_rate 算历史置信

结果：
- input_rows: 281
- gate_passed_count: 20
- pass_digest_count: 20
- interrupt_candidate_count: 15
- review_count: 5
- block_count: 256

### 6. Publisher 改用 Composer gate

脚本：`scripts/apply_v14_publish_policy.py`

如果 Composer gate 不过，直接 block。
如果 flow subtype 是 `etf_macro_news` / `institutional_disclosure` / `flow_unclear`，默认 block。

结果：
- input_rows: 281
- digest_rows: 0
- interrupt_rows: 0
- block_rows: 281

### 7. Digest preview

脚本：`scripts/build_v14_digest_preview.py`

结果：
- security_rows: 0
- fund_flow_rows: 0

也就是严格闸门下当前没有内容适合发到 TG。

## 当前主要矛盾

1. 门槛严格后没有可发布内容，这是质量正确，还是样本/数据源/规则设计仍然失败？
2. Composer gate 过的 20 条里很多是 `upgrade_or_fork`，但 Publisher 不让它们发，因为当前 digest eligible subtype 只含 exploit / ETF flow / stablecoin flow。
3. Active exploit 0 条通过，可能是安全事件识别源本身太差，也可能是资产归因规则太硬。
4. ETF/Fund flow 57 条只剩 3 条，且 Publisher 仍然 0 条，说明 flow 类可能更适合“早晚报背景”，不适合盘中发。
5. 当前 PreFilter 只有 6h pre-event abnormal，没有 5min/15min price-in，也没有 volume spike。
6. HistoricalMatcher 目前用同一批历史回测自举，可能会过拟合或给错误置信。

## 请你输出

请完整中文回答，尽量具体，不要泛泛而谈：

1. 这轮改动有没有真正朝正确方向推进？哪些地方仍然是伪进步？
2. 281 条全 block 是否合理？如果不合理，应该先放开哪一类事件？标准是什么？
3. `upgrade_or_fork` 该不该纳入 digest？哪些升级类事件值得发，哪些必须 block？
4. Active exploit 0 条 urgent 是否合理？如何修复安全事件数据源和资产归因，不靠人工逐条看？
5. Flow 类该如何拆成盘中、早报/晚报、只归档三种处理方式？
6. PreFilter 下一步最小实现应该补什么字段？5min/15min price-in、volume spike、source delay、market regime 的优先级怎么排？
7. HistoricalMatcher MVP 应该怎么避免自举过拟合？如果没有人工标签，如何用历史价格表现自动做弱标签？
8. Telegram 卡片应该怎样改，特别是在“没有可发事件”或“只有背景事件”时怎么表达才对用户有价值？
9. 接下来 1 天内最应该写哪 5 个脚本/改哪 5 个现有脚本？按优先级给清单。
10. 你作为不迎合的负责人，会砍掉或暂停哪些现有模块？

