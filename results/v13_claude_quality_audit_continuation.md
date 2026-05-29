# Claude Response

- generated_at: 2026-05-28 19:53:37 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V13_QUALITY_AUDIT_CONTINUATION_PROMPT.md
- prompt_sha256_16: 3363284cdfab6b10

# Crypto Event Intelligence v13 严厉审计意见

## 一、核心判断：当前系统哪里不可信

### 🔴 必须暂停的部分

1. **盘中雷达/观察池 - 立即暂停**
   - boost=0 说明没有任何事件类型在历史上证明了"发布后立即关注能带来信息优势"
   - 171条回测样本中，只有1条进入digest_only，12条collect_more
   - **用户会把任何"盘中推送"理解成交易信号**，无论你怎么写免责声明
   - 当前数据质量不支持任何形式的盘中内容，包括"弱雷达""观察池""结构变化"等包装

2. **whale_wallet_position 事件组 - 暂停或降级**
   - 59条中48条是HYPE污染（81.36%）
   - 单一来源tg:HyperInsight占70.83%
   - 时间跨度仅1.4天，属于burst pattern
   - 即使排除HYPE，剩余11条样本不足以验证该事件类型的有效性
   - **建议：archive所有HYPE相关，剩余whale_position暂停boost/urgent，仅保留digest**

3. **active_exploit急报 - 暂停**
   - 9条active_exploit，平均abnormal_return仅0.19%
   - 胜率44.44%，接近随机
   - 0条触发urgent阈值
   - **说明：黑客攻击事件在发布时已被price-in，或者影响太分散**
   - 当前数据不支持"急报"逻辑

### 🟡 数据质量存疑的部分

4. **other/uncategorized - 78.66%是垃圾**
   - 446条garbage，121条potential
   - 说明候选识别规则过松，或者原始快讯源质量差
   - **不应该让LLM分类这121条**，因为：
     - LLM分类成本高
     - 即使分出来，样本量也不足以验证新事件类型
     - 应该先修候选识别规则，从源头减少垃圾

5. **source三层表 - 数据不足**
   - 23个源中，18个insufficient_data
   - 只有3个promising_needs_validation
   - webhook占739条候选但只回测50条，uncategorized占42.49%
   - **说明：要么扩大回测窗口，要么承认大部分源不可用**

6. **regime分层 - 全部btc_range**
   - 171条全在同一市场状态，无法验证跨regime稳定性
   - **说明：当前时间窗口太短，或者选择的时间段恰好是震荡市**

---

## 二、值得继续的部分

### ✅ 可信的基础设施

1. **价格回填和abnormal return计算 - 可信**
   - 171条全部ok/pass
   - Binance数据完整
   - BTC/ETH对照逻辑清晰

2. **etf_or_fund_flow - 可继续观察**
   - 21条样本，5条severe price-in（23.81%）
   - 平均price-in ratio 50.15%，说明有一半收益在发布前已反映
   - **但仍有价值**：ETF流向是宏观信号，适合早报/晚报总结，不适合盘中

3. **exploit_or_theft（非active） - 可继续观察**
   - 36条样本，1条severe price-in（2.78%）
   - 平均price-in ratio 30.74%
   - **适合早报/晚报**，作为"行业安全事件回顾"

---

## 三、下一轮可执行任务（按优先级排序）

### 🔥 P0：清理污染和扩大样本（必须完成）

#### 任务1：archive HYPE污染并重新统计
**脚本名**：`scripts/archive_hype_and_recompute_stats.py`

**输入**：
- `data/backtest_v08_alt_history_with_returns.csv`
- `results/v13_hype_contamination_detail.csv`

**输出**：
- `data/backtest_v08_alt_history_clean.csv`（排除HYPE后的干净数据）
- `results/v13_post_hype_removal_summary.csv`

**关键字段**：
- event_group
- asset
- source
- abnormal_vs_btc_24h
- is_archived（新增）
- archive_reason（新增）

**验收标准**：
- HYPE相关48条标记is_archived=true，archive_reason="single_asset_burst_contamination"
- whale_wallet_position剩余11条
- 重新计算各event_group的boost/digest/collect判定
- 输出新的boost_count、digest_only_count、collect_more_count

---

#### 任务2：扩大历史回测窗口到500-1000条
**脚本名**：`scripts/export_extended_history_candidates.py`

**输入**：
- `data/candidates.csv`（当前2000条）
- 时间范围：2024-01-01 至 2024-12-31（或更早）

**输出**：
- `data/candidates_extended_500.csv`（500条）
- `data/candidates_extended_1000.csv`（1000条）
- `results/v13_extended_export_summary.csv`

**关键字段**：
- published_at
- event_group
- asset
- source
- 确保覆盖：
  - BTC牛市（2024-02至03）
  - BTC回调（2024-04至05）
  - 震荡市（2024-06至08）
  - 年底行情（2024-11至12）

**验收标准**：
- 至少覆盖3个不同regime（btc_bull、btc_bear、btc_range）
- 每个event_group至少30条样本（如果历史数据允许）
- 非uncategorized占比>60%

---

#### 任务3：修正候选识别规则，减少garbage
**脚本名**：`scripts/tighten_candidate_identification_rules.py`

**输入**：
- `results/v13_other_quality_report.csv`（446条garbage）
- 当前候选识别规则（在`src/candidate_identifier.py`）

**输出**：
- `src/candidate_identifier_v2.py`（新规则）
- `results/v13_rule_tightening_comparison.csv`

**关键改进**：
- 必须包含明确资产ticker（不能只有"加密货币""数字资产"等泛指）
- 排除纯宏观新闻（除非明确提及BTC/ETH/具体alt）
- 排除纯行业动态（如"某公司招聘""某会议召开"）
- 排除纯技术更新（如"某链升级完成"，除非伴随TVL/价格异动）

**验收标准**：
- 用新规则重新跑2000条候选
- garbage占比从78.66%降到<50%
- 不能误伤已验证的有效事件类型（etf_flow、exploit等）

---

### 🔥 P1：source评分和限流（必须完成）

#### 任务4：给source打分并设置限流规则
**脚本名**：`scripts/score_and_throttle_sources.py`

**输入**：
- `data/source_identity_layers.csv`
- `data/backtest_v08_alt_history_clean.csv`（排除HYPE后）

**输出**：
- `data/source_scores.csv`
- `results/v13_source_throttle_rules.csv`

**关键字段**：
```
source, 
total_candidates, 
backtested_count, 
valid_event_ratio,  # 非garbage占比
boost_count, 
digest_count,
avg_abnormal_return_24h,
source_score,  # 0-100
daily_quota,  # 每日最多进入候选的条数
burst_window_limit,  # 1小时内最多条数
recommended_action  # trust/validate/throttle/block
```

**评分逻辑**：
- valid_event_ratio > 60%：+30分
- boost_count > 0：+20分
- avg_abnormal_return_24h > 5%：+20分
- backtested_count > 20：+15分
- 单一资产占比 < 30%：+15分

**限流规则**：
- score < 30：block
- score 30-50：daily_quota=5, burst_window_limit=2
- score 50-70：daily_quota=20, burst_window_limit=5
- score > 70：daily_quota=50, burst_window_limit=10

**验收标准**：
- tg:HyperInsight应该被throttle或block（因为HYPE污染）
- webhook需要拆分子源（如果可能）
- 至少识别出2-3个高分源（score>70）

---

### 🔥 P2：regime分层验证（重要）

#### 任务5：基于扩展数据重新计算regime分层
**脚本名**：`scripts/recompute_regime_layers_extended.py`

**输入**：
- `data/backtest_extended_500_with_returns.csv`（任务2输出，回填价格后）
- BTC历史价格和波动率

**输出**：
- `results/v13_regime_layer_extended_report.csv`
- `results/v13_regime_layer_extended_summary.csv`

**关键字段**：
- event_group
- regime（btc_bull/btc_bear/btc_range/btc_high_vol）
- event_count_in_regime
- avg_abnormal_return_24h_in_regime
- win_rate_in_regime
- cross_regime_stability_score  # 新增：跨regime表现一致性

**验收标准**：
- 每个event_group至少在2个不同regime中有10+条样本
- 识别出"regime-stable"事件类型（跨regime表现一致）
- 识别出"regime-dependent"事件类型（只在特定市场状态有效）

---

### 🟡 P3：TG产品调整（基于P0-P2结果）

#### 任务6：设计"早报/晚报"内容模板
**脚本名**：`scripts/generate_digest_templates.py`

**输入**：
- `data/backtest_v08_alt_history_clean.csv`
- 当前TG卡片模板

**输出**：
- `templates/morning_digest_template.md`
- `templates/evening_digest_template.md`
- `results/v13_digest_content_rules.csv`

**早报内容（8:00-9:00）**：
- 过去24h的ETF流向（如果有）
- 过去24h的重大exploit/theft（金额>1000万美元）
- 过去24h的交易所异动（大额转入转出）
- **禁止**：任何"今日关注""盘中观察"等前瞻性表达

**晚报内容（20:00-21:00）**：
- 当日事件回顾（按event_group分类）
- 当日资产表现总结（涨跌幅top10）
- **禁止**：任何"明日预期""后续关注"等前瞻性表达

**卡片必须删除的字段**：
- "建议关注"
- "潜在影响"
- "交易机会"
- 任何emoji（🚀📈📉等）
- 任何颜色标记（红/绿）

**卡片必须保留的字段**：
- 事件时间
- 事件类型
- 相关资产
- 事件描述（客观陈述）
- 数据来源
- 免责声明（每条都要有）

**验收标准**：
- 用历史数据生成10条早报、10条晚报样例
- 人工审核：是否有任何可能被理解成交易建议的表达

---

#### 任务7：设计"观察池"替代方案（如果P0-P2结果支持）
**脚本名**：`scripts/design_watchlist_alternative.py`

**前置条件**：
- 任务1-5完成后，至少有1个event_group满足：
  - 样本量>30
  - 跨regime稳定
  - avg_abnormal_return_24h > 3%
  - win_rate > 55%

**如果前置条件不满足，跳过此任务**

**如果满足，设计方案**：
- 名称改为"事件记录"或"信息归档"，不用"观察池""雷达"等词
- 推送频率：每日最多3条
- 推送时机：仅在早报/晚报时段
- 卡片表达：
  - ❌ "该事件可能影响XX价格"
  - ✅ "该事件已记录，历史上类似事件在24h内平均abnormal return为X%（样本量N，胜率Y%）"

---

### 🟡 P4：active_exploit改进（如果有价值）

#### 任务8：接入链上实时监控（可选）
**脚本名**：`scripts/integrate_onchain_exploit_monitor.py`

**问题**：当前active_exploit依赖快讯，发布时已price-in

**改进方向**：
- 接入链上监控API（如Arkham、Paidun、Certik）
- 在黑客地址转移资产时触发，而不是等快讯发布
- 但这需要：
  - 额外成本（API费用）
  - 更复杂的验证逻辑（避免误报）
  - 可能仍然无法带来alpha（因为链上数据是公开的）

**建议**：
- 先完成P0-P2任务
- 如果扩展数据后active_exploit仍然无效，放弃急报逻辑
- 仅保留在早报/晚报中总结重大安全事件

---

### 🟢 P5：长期优化（P0-P2完成后再考虑）

#### 任务9：多资产组合事件识别
**脚本名**：`scripts/identify_multi_asset_events.py`

**目标**：识别"同时影响多个资产"的事件（如监管政策、交易所故障）

**输入**：
- 扩展历史数据（500-1000条）

**输出**：
- `results/v13_multi_asset_events.csv`

**关键字段**：
- event_id
- affected_assets（列表）
- avg_abnormal_return_across_assets
- correlation_with_btc

**验收标准**：
- 识别出至少10个多资产事件
- 验证这些事件是否比单资产事件更稳定

---

#### 任务10：用户反馈收集机制
**脚本名**：`scripts/setup_user_feedback_collection.py`

**目标**：在TG群中收集用户对早报/晚报的反馈

**实现**：
- 每条早报/晚报下方添加inline button："有用👍" "无用👎"
- 记录到数据库
- 每周生成反馈报告

**输出**：
- `results/v13_user_feedback_weekly.csv`

**关键字段**：
- event_id
- event_group
- useful_count
- useless_count
- useful_ratio

**验收标准**：
- 至少收集100条反馈
- 识别出用户最不喜欢的事件类型

---

## 四、TG群接下来应该发什么、不该发什么

### ✅ 应该发的内容

1. **早报（每日8:00-9:00，1条）**
   - 过去24h的ETF流向总结
   - 过去24h的重大安全事件（>1000万美元）
   - 过去24h的交易所大额异动
   - 纯客观陈述，无预测

2. **晚报（每日20:00-21:00，1条）**
   - 当日事件分类回顾
   - 当日资产表现总结
   - 纯客观陈述，无预测

3. **周报（每周日21:00，1条）**
   - 本周事件统计
   - 本周各event_group表现回顾
   - 数据质量报告（回填成功率、新增样本数）

### ❌ 不该发的内容

1. **任何盘中推送**
   - 无论叫"雷达""观察池""结构变化"，都不发
   - 当前数据不支持

2. **任何前瞻性表达**
   - "可能上涨""建议关注""潜在机会"
   - "后续观察""等待验证"

3. **任何交易相关词汇**
   - "买入""卖出""做多""做空"
   - "止损""止盈""仓位"

4. **任何情绪化表达**
   - emoji（🚀📈📉🔥💎）
   - "重磅""爆炸""惊人"
   - 颜色标记（红/绿）

### 📝 卡片表达规范

**当前卡片（❌错误示例）**：
```
🚀 鲸鱼地址异动
资产：HYPE
事件：某地址转入500万HYPE
建议：关注后续价格变化
风险：中等
```

**修正后卡片（✅正确示例）**：
```
事件记录 | whale_wallet_position
时间：2024-12-15 14:23 UTC
资产：HYPE
描述：地址0x123...转入500万HYPE至Binance
来源：tg:HyperInsight

历史参考：
- 样本量：11条（已排除burst污染）
- 24h平均abnormal return：+2.3%
- 胜率：54.5%

免责声明：本信息仅供记录，不构成投资建议。
```

---

## 五、最严厉的警告

### 🚨 如果以下情况发生，立即停止项目

1. **用户把早报/晚报理解成交易信号**
   - 监控用户反馈和群内讨论
   - 如果出现"根据早报买入XX""按照晚报卖出XX"等表达
   - 立即停止所有推送，重新设计表达方式

2. **P0-P2任务完成后，仍然没有任何event_group满足boost条件**
   - 说明当前数据源和事件类型不支持"信息优势"假设
   - 应该转型为"事件归档系统"，而不是"情报系统"

3. **扩展到500-1000条样本后，garbage占比仍>50%**
   - 说明候选识别逻辑根本性错误
   - 需要重新设计整个事件识别流程

4. **source评分后，没有任何源score>70**
   - 说明当前接入的快讯源质量都不足以支持该项目
   - 需要更换数据源（如彭博、路透等付费源）

---

## 六、时间表和资源需求

### 第一周（P0任务）
- 任务1：2天（archive HYPE，重新统计）
- 任务2：3天（导出500-1000条，回填价格）
- 任务3：2天（修正候选识别规则）

### 第二周（P1任务）
- 任务4：3天（source评分和限流）
- 任务5：4天（regime分层验证）

### 第三周（P2任务）
- 任务6：3天（早报/晚报模板）
- 任务7：2天（观察池替代方案，如果适用）
- 任务8：2天（评估active_exploit改进方向）

### 资源需求
- 开发：1人全职
- 数据验证：0.5人（兼职，人工审核样本）
- 总成本：约3周开发时间

---

## 七、最终建议

### 如果你问我"这个项目还该不该继续"

**答案：继续，但要大幅降低预期**

**理由**：
1. 基础设施（价格回填、abnormal return）是可信的
2. 部分事件类型（etf_flow、exploit）有观察价值
3. 但当前数据**不支持任何形式的盘中推送**

**正确的产品定位**：
- ❌ 不是
