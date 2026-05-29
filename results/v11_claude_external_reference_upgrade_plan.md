# Claude Response

- generated_at: 2026-05-28 18:04:11 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V11_EXTERNAL_REFERENCE_UPGRADE_PROMPT.md
- prompt_sha256_16: c6489ab6fd4e95a7

# Crypto Event Intelligence 系统升级评审报告

## 一、总体判断

### 1.1 方向正确性评估

**核心判断：方向基本正确，但存在三个关键错位**

#### 错位一：产品层超前于数据质量层（严重）
- 你已经在做 TG 卡片美化、分数展示、情报分层，但**连哪些源真的有效都还没证明**
- 这就像餐厅还没确定食材新鲜度，就开始设计摆盘
- **量化视角**：样本量不足（older500 + 几周 TG 发布），就开始做产品优化，这是统计学上的过早优化
- **数据工程视角**：没有 source quality metrics，没有 source SLA，就开始做下游产品，这是架构倒置

#### 错位二：把"可读性"当成了当前主要矛盾（中等）
- 真正的主要矛盾是：**你不知道哪些事件类型在哪些市场状态下真的有研究价值**
- 用户看不懂分数，不是因为卡片设计不好，而是因为**你自己都不知道这个分数代表什么**
- 举例：Hyperliquid 大仓位变化，你有 100 个样本证明它在 BTC 上涨期 4h 超额收益显著吗？没有
- 没有统计显著性支撑的"强度分数"，本质是**伪量化**

#### 错位三：把 LLM 用在了不该用的地方（中等）
- 你在用 LLM 做事件解读、生成"综合判断"这种话
- 但 LLM 不应该用来**掩盖你没有统计结论**
- LLM 应该用在：格式转换、多语言、字段提取、异常检测的自然语言描述
- LLM 不应该用在：生成"需要结合资金费率判断"这种废话

### 1.2 是否过早做了 Telegram 产品层？

**是的，过早了。**

**证据链：**
1. 你没有 `source_effectiveness_report.csv`，不知道哪些源的信号在哪些条件下有效
2. 你没有 `event_type_performance_matrix.csv`，不知道"CEX 大额流入"在不同市值、不同波动率下的表现
3. 你没有 `false_positive_analysis.csv`，不知道哪些事件是噪音
4. 你没有 `signal_decay_curve.csv`，不知道信号的半衰期

**但不是说要停掉 TG**，而是要：
- 把 TG 当成**数据收集前端**，而不是产品
- 现在的 TG 群应该是"实验组"，不是"正式产品"
- 每条发布都是为了收集 outcome data，不是为了服务用户

### 1.3 是否应该重构成 Source Adapter / Normalizer / Composer / Router / Publisher / Archivist / Evaluator？

**应该，但不是现在全部重构。**

**分阶段判断：**

| 模块 | 优先级 | 原因 | 当前状态 | 建议 |
|------|--------|------|----------|------|
| Source Adapter | P0 | 新源接入频繁，需要标准化 | 混乱 | 立即重构 |
| Normalizer | P0 | 时间、资产、实体标准化是基础 | 基本可用 | 补充测试 |
| Archivist | P0 | 没有它就没有回测 | 基本可用 | 补充索引 |
| Evaluator | P0 | 核心能力 | 初步可用 | 扩展指标 |
| Router | P1 | 决定发不发、发哪里 | 规则简陋 | 下一版重构 |
| Composer | P2 | 影响可读性，不影响数据质量 | 可用 | 暂缓 |
| Publisher | P2 | 只是输出层 | 可用 | 暂缓 |

**最小可行版本（MVP）：**
```
Source Adapter (标准化接入) 
    ↓
Normalizer (清洗) 
    ↓
Archivist (入库) 
    ↓
Evaluator (回测) 
    ↓
[暂停，先看 2 周数据]
    ↓
Router (决策) 
    ↓
Publisher (发布)
```

### 1.4 这套架构是否过度工程？

**如果现在全做，是过度工程。如果分三期做，不是。**

**过度工程的标志：**
- 你在做"可能用得上"的抽象
- 你在做"为了优雅"的设计
- 你在做"参考了某个项目"的模仿

**合理工程的标志：**
- 每个模块都解决一个**当前已经痛的问题**
- 每个抽象都有**至少 3 个实例**支撑
- 每个接口都有**明确的测试用例**

**当前真正痛的问题：**
1. 新源接入要改 3 处代码（痛）→ Source Adapter
2. 不知道源的质量（痛）→ Source Registry + Shadow Mode
3. 回测样本太少（痛）→ 历史数据回填
4. 不知道哪些事件有效（痛）→ Evaluator 扩展
5. TG 卡片重复啰嗦（不痛，是痒）→ 暂缓

---

## 二、外部项目借鉴清单

### 2.1 daily_stock_analysis 值得学的

| 特性 | 为什么值得学 | 如何借鉴 | 优先级 |
|------|--------------|----------|--------|
| **数据源配置层** | 它有 `config/sources.yaml`，每个源有 enable/priority/cost | 做 `source_registry.csv` | P0 |
| **多模型路由** | 它根据任务类型选模型（GPT-4/Claude/本地） | 做 `llm_router.py`，快讯用 Haiku，深度分析用 Sonnet | P1 |
| **预算控制** | 它有每日 token 预算和告警 | 做 `llm_budget_tracker.csv` | P1 |
| **历史报告归档** | 它把每日报告存成 markdown，可检索 | 你已经有了，继续保持 | P2 |
| **任务状态面板** | 它有 pending/running/completed 状态 | 如果你要做 Web UI，可以学；现在不需要 | P3 |

### 2.2 daily_stock_analysis 不该学的

| 特性 | 为什么不该学 |
|------|--------------|
| **买卖建议** | 你明确说了不做交易建议，这是红线 |
| **决策面板** | 它是给个人投资者用的，你是给量化研究员用的，需求不同 |
| **股票 watchlist** | 股票是有限集合，crypto 是动态的，不能照搬 |
| **技术指标计算** | 它做 MACD/RSI，你不应该在情报系统里做，应该在回测层做 |

### 2.3 fin-thread 值得学的

| 特性 | 为什么值得学 | 如何借鉴 | 优先级 |
|------|--------------|----------|--------|
| **角色分层架构** | Journalist/Composer/Publisher 职责清晰 | 直接映射到你的模块 | P0 |
| **Scavenger 模式** | 专门处理结构化日历数据 | 你的 token unlock 可以用这个模式 | P1 |
| **Job 调度** | 它用 cron + 状态机管理周期任务 | 你现在是脚本，应该升级成 job 系统 | P1 |
| **Archivist 查询** | 它支持历史事件检索 | 你需要这个来做"相似事件历史表现" | P2 |

### 2.4 fin-thread 不该学的

| 特性 | 为什么不该学 |
|------|--------------|
| **纯新闻改写** | 它主要是改写新闻，你需要做事件抽取和结构化 |
| **无回测** | 它没有效果评估，你必须有 |
| **单一输出渠道** | 它只发 TG，你需要早午晚报 + 盘中雷达 + 研究数据包 |

### 2.5 Skill Prompt 思路值得学的

**核心价值：把稳定工作流沉淀成可复用、可测试的 Skill**

**建议沉淀的 Skill：**

1. **crypto-event-extractor**
   - 输入：原始快讯文本
   - 输出：`{asset, entity, event_type, event_subtype, magnitude, timestamp}`
   - 测试集：100 条标注好的快讯

2. **crypto-event-router**
   - 输入：结构化事件 + 历史表现
   - 输出：`{route: interrupt/board/archive/discard, reason}`
   - 测试集：50 条已知好/坏事件

3. **crypto-card-composer**
   - 输入：结构化事件 + 上下文
   - 输出：TG markdown 卡片
   - 测试集：10 种事件类型各 3 个样本

4. **crypto-source-evaluator**
   - 输入：source_id + 2 周 outcome data
   - 输出：质量报告 + 建议
   - 测试集：5 个已知好源 + 5 个已知坏源

**不该做成 Skill 的：**
- 价格计算（这是确定性逻辑，不需要 LLM）
- 数据库查询（同上）
- 统计检验（同上）

---

## 三、不该照搬的部分

### 3.1 不要照搬 daily_stock_analysis 的交易决策层

**原因：**
- 它的目标用户是散户，需要"买入/卖出/持有"建议
- 你的目标用户是量化研究员，需要"这个事件在历史上 X% 概率涨"
- 如果你做了交易建议，就变成了"荐股"，有合规风险

### 3.2 不要照搬 fin-thread 的纯转发模式

**原因：**
- 它是新闻聚合器，你是事件情报系统
- 它不需要证明有效性，你需要
- 它可以发 100 条，你只能发 10 条

### 3.3 不要为了"参考项目有"就加功能

**反例：**
- daily_stock_analysis 有 Web UI，所以我们也要做？**不，你现在不需要**
- fin-thread 有多语言，所以我们也要做？**不，你的用户只看中文**

---

## 四、推荐目标架构

### 4.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Source Layer (P0)                        │
├─────────────────────────────────────────────────────────────┤
│ Source Adapter (标准化接入)                                   │
│  ├─ Watcher Adapter (链上、CEX、衍生品)                       │
│  ├─ News Adapter (快讯源)                                     │
│  └─ Calendar Adapter (解锁、事件日历)                         │
│                                                              │
│ Source Registry (source_registry.csv)                       │
│  ├─ source_id, type, latency, cost, confidence              │
│  └─ enable, shadow_mode, last_eval_date                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Normalization Layer (P0)                    │
├─────────────────────────────────────────────────────────────┤
│ Normalizer                                                   │
│  ├─ 时间标准化 (UTC+8)                                        │
│  ├─ 资产标准化 (BTC/WBTC/Bitcoin → BTC)                      │
│  ├─ 实体标准化 (Binance/币安 → binance)                      │
│  └─ 事件类型标准化                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer (P0)                        │
├─────────────────────────────────────────────────────────────┤
│ Archivist                                                    │
│  ├─ event_ledger.csv (所有事件)                              │
│  ├─ tg_alert_ledger.csv (已发布事件)                         │
│  ├─ outcome_ledger.csv (效果数据)                            │
│  └─ source_quality_ledger.csv (源质量)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Evaluation Layer (P0)                      │
├─────────────────────────────────────────────────────────────┤
│ Evaluator                                                    │
│  ├─ Outcome Evaluator (1h/4h/24h/72h 表现)                  │
│  ├─ Source Evaluator (源质量评估)                            │
│  ├─ Event Type Evaluator (事件类型有效性)                    │
│  └─ Market Regime Evaluator (市场状态分层)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Decision Layer (P1)                       │
├─────────────────────────────────────────────────────────────┤
│ Router                                                       │
│  ├─ 基于历史表现的路由规则                                    │
│  ├─ 基于市场状态的动态阈值                                    │
│  └─ 基于源质量的置信度调整                                    │
│                                                              │
│ 输出：interrupt / board / archive / discard                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer (P2)                    │
├─────────────────────────────────────────────────────────────┤
│ Composer (生成 TG 卡片)                                       │
│ Publisher (发布到 TG)                                         │
│ Reporter (生成早午晚报)                                       │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 最小可行版本（接下来 2 周）

**只做 P0 层：**
1. Source Adapter：标准化新源接入
2. Source Registry：登记所有源
3. Archivist：补充索引和查询
4. Evaluator：扩展评估指标

**暂停 P1/P2 层：**
- Router 继续用现在的简单规则
- Composer 继续用现在的模板
- 不做 Web UI
- 不做复杂的 LLM 解读

---

## 五、Telegram 产品形态建议

### 5.1 最终用户体验应该长什么样？

**用户画像：量化研究员 or 专业交易员**

**他们的一天：**
- 08:00 起床，看早报（昨晚到今晨的重要事件）
- 09:00-12:00 工作，TG 静音，偶尔瞥一眼
- 12:00 午休，看午报（上午的异动摘要）
- 14:00-18:00 工作，TG 静音
- 18:00 下班前，看晚报（今日总结）
- 21:00-23:00 复盘，看历史事件表现

**他们希望看到：**
1. **早报（08:00）**：昨晚到今晨的 Top 5 事件，每个事件 3 行
2. **午报（12:00）**：上午的 Top 3 异动，每个事件 2 行
3. **晚报（18:00）**：今日 Top 10 事件 + 市场总结
4. **盘中急报（随时）**：只有真正重大的异动（每天 0-3 条）
5. **周报（周日晚）**：本周事件回顾 + 哪些类型事件有效

**他们讨厌看到：**
1. 每小时刷屏的"盘中雷达"
2. 重复的静态信息（某 token 有大仓位，每小时提醒一次）
3. 没有结论的废话（"需要综合判断"）
4. 看不懂的分数（"强度 8.5"是什么意思？）
5. 事后证明是噪音的事件（某地址转账，价格没动）

### 5.2 盘中雷达、急报、早午晚报三者分工

| 类型 | 频率 | 内容 | 阈值 | 示例 |
|------|------|------|------|------|
| **盘中急报** | 每天 0-3 条 | 极端异动，需要立即关注 | 历史 95 分位 + 高置信度源 | "BTC 1 小时流入 Binance 2 万枚，历史上此类事件 4h 下跌概率 78%" |
| **早报** | 每天 08:00 | 昨晚到今晨 Top 5 | 历史 80 分位 | "ETH 昨晚大额解锁 50 万枚，历史上解锁日平均跌 2.3%" |
| **午报** | 每天 12:00 | 上午 Top 3 异动 | 历史 75 分位 | "上午 Hyperliquid BTC 多头持仓增加 15%，当前多空比 2.1" |
| **晚报** | 每天 18:00 | 今日 Top 10 + 总结 | 历史 70 分位 | "今日 BTC 净流入 CEX 5000 枚，链上活跃度下降 12%" |
| **周报** | 周日 20:00 | 本周回顾 + 有效性分析 | 全部 | "本周 CEX 流入事件 12 次，其中 8 次后续下跌，有效率 67%" |

**关键原则：**
- 盘中急报：宁缺毋滥，只发"不发就是失职"的事件
- 早午晚报：固定时间，用户可预期
- 周报：帮用户建立"哪些事件真的有用"的认知

### 5.3 TG 卡片设计

**反例（当前）：**
```
📊 事件类型：CEX 大额流入
🪙 资产：BTC
💰 金额：5000 BTC
📍 实体：Binance
⏰ 时间：2024-01-15 10:30
📈 强度：8.5
🎯 置信度：0.82
📝 解读：大额流入可能带来抛压，需要结合资金费率和持仓量综合判断。
```

**问题：**
- 强度 8.5 是什么意思？
- 置信度 0.82 是什么意思？
- 解读是废话

**正例（改进）：**
```
🚨 BTC 大额流入 Binance

金额：5000 BTC（约 2.5 亿美元）
时间：10:30
来源：链上监控（高可信度）

📊 历史表现：
类似事件（>3000 BTC 流入）在过去 3 个月出现 18 次
- 4 小时内下跌概率：67%（12/18）
- 平均跌幅：-1.8%
- 当前 BTC 处于上涨趋势，历史上此状态下跌幅收窄至 -0.9%

⚠️ 注意：这是历史统计，不是交易建议
```

**改进点：**
1. 去掉"强度""置信度"这种黑盒分数
2. 用"历史上 X 次，Y% 概率"替代
3. 说明当前市场状态
4. 明确这是统计，不是建议

### 5.4 分数/强度/置信度的表达

**不要用的表达：**
- ❌ "强度 8.5"（用户不知道 8.5 是什么）
- ❌ "置信度 0.82"（用户不知道 0.82 是高还是低）
- ❌ "重要性 ★★★★☆"（主观且无信息量）

**应该用的表达：**
- ✅ "历史上类似事件 18 次，67% 下跌"（清晰）
- ✅ "样本量：18 次（中等可信）"（透明）
- ✅ "数据来源：链上监控（高可信度）vs 社交媒体（低可信度）"（可解释）

**模板：**
```
历史表现（基于 {N} 个样本）：
- {时间窗口} 内 {方向} 概率：{X}%
- 平均幅度：{Y}%
- 样本量评价：{充足/中等/不足}
```

---

## 六、数据质量和回测建议

### 6.1 当前最严重的数据质量问题

**问题 1：样本量不足**
- older500 只有 500 条快讯
- TG 发布只有几周数据
- 无法做统计显著性检验

**解决方案：**
1. 回填历史数据：至少 3 个月的链上数据、CEX 数据
2. 对每个事件类型，至少要有 30 个样本才能发布
3. 样本不足的事件类型，只进 shadow mode

**问题 2：没有源质量评估**
- 不知道哪些源延迟高
- 不知道哪些源误报率高
- 不知道哪些源在哪些市场状态下失效

**解决方案：**
```python
# source_quality_metrics.csv
source_id, total_events, false_positive_rate, avg_latency, effectiveness_score, last_eval_date
onchain_watcher, 1200, 0.15, 30s, 0.72, 2024-01-15
news_source_A, 3000, 0.45, 120s, 0.31, 2024-01-15
```

**问题 3：没有分层回测**
- 没有按市值分层（大盘币 vs 小盘币）
- 没有按波动率分层（高波 vs 低波）
- 没有按 BTC 状态分层（上涨 vs 下跌 vs 震荡）

**解决方案：**
```python
# event_performance_stratified.csv
event_type, asset_tier, volatility_regime, btc_regime, sample_size, win_rate_4h, avg_return_4h
cex_inflow, large_cap, high_vol, btc_up, 45, 0.58, -0.8%
cex_inflow, large_cap, high_vol, btc_down, 38, 0.71, -2.1%
cex_inflow, small_cap, high_vol, btc_up, 12, 0.42, +1.2%
```

### 6.2 回测方法论建议

**当前问题：**
- 你在用"4h 后涨跌"做评估，但没有考虑：
  - 事件发布时间（是否已经 price-in）
  - 同时发生的其他事件（混淆因素）
  - 市场整体状态（beta 风险）

**改进方案：**

**1. 事件时间窗口标准化**
```python
# 不要用"发布后 4h"，要用"事件发生后 4h"
event_time = normalize_event_time(raw_event)  # 链上事件用区块时间，快讯用发布时间
t0 = event_time
t1 = t0 + 1h
t4 = t0 + 4h
t24 = t0 + 24h
```

**2. 控制混淆因素**
```python
# 如果 4h 内有其他重大事件,标记为 confounded
if has_other_major_event(t0, t4):
    outcome['confounded'] = True
    outcome['use_in_analysis'] = False
```

**3. 多重假设检验校正**
```python
# 你在测试 N 个事件类型 × M 个时间窗口,需要 Bonferroni 校正
significance_threshold = 0.05 / (N * M)
```

**4. 样本量要求**
```python
# 最小样本量计算
def min_sample_size(expected_win_rate, confidence=0.95, power=0.8):
    # 假设要检测 win_rate > 0.55（比随机好）
    # 需要至少 30-50 个样本
    return max(30, calculate_power_analysis(expected_win_rate, confidence, power))
```

### 6.3 需要补充的评估指标

**当前有的：**
- asset_return_4h
- btc_abnormal_return_4h
- pre_event_price_in

**需要补充的：**

| 指标 | 用途 | 计算方法 |
|------|------|----------|
| **Sharpe Ratio** | 风险调整后收益 | `mean(returns) / std(returns) * sqrt(252)` |
| **Max Drawdown** | 最大回撤 | 从峰值到谷底的最大跌幅 |
| **Win Rate** | 胜率 | `sum(return > 0) / total` |
| **Profit Factor** | 盈亏比 | `sum(positive_returns) / abs(sum(negative_returns))` |
| **False Positive Rate** | 误报率 | 事件发生但价格无反应的比例 |
| **Signal Decay** | 信号衰减 | 1h/4h/24h 收益的衰减曲线 |
| **Regime Dependency** | 状态依赖性 | 不同 BTC 状态下的表现差异 |

---

## 七、LLM 使用和成本控制建议

### 7.1 LLM 应该用在哪里

**应该用的地方（有价值）：**

| 任务 | 模型 | 原因 | 成本 |
|------|------|------|------|
| **快讯事件抽取** | Claude Haiku | 非结构化文本 → 结构化字段 | 低 |
| **实体消歧** | Claude Haiku | "币安" vs "Binance" → binance | 低 |
| **异常检测描述** | Claude Haiku | 把统计异常翻译成自然语言 | 低 |
| **多源信息融合** | Claude Sonnet | 3 个源说了同一件事,合并成 1 条 | 中 |
| **历史相似事件检索** | Embedding + 向量搜索 | 找到历史上类似的事件 | 中 |
| **周报生成** | Claude Sonnet | 汇总一周数据,生成分析报告 | 中 |

**不应该用的地方（浪费钱或有害）：**

| 任务 | 为什么不该用 LLM | 应该用什么 |
|------|------------------|------------|
| **价格计算** | 确定性逻辑,LLM 会算错 | Pandas |
| **统计检验** | LLM 不懂 p-value | Scipy |
| **生成交易建议** | LLM 会胡说,有合规风险 | 不做 |
| **生成"综合判断"废话** | 没有信息量,浪费 token | 删掉 |
| **每条事件都做深度解读** | 成本高,用户不看 | 只在周报做 |

### 7.2 成本控制策略

**当前问题：**
- 你没有 token 预算
- 你没有按任务类型分配模型
- 你可能在用 Sonnet 做 Haiku 能做的事

**改进方案：**

**1. 模型分级使用**
```python
# llm_router.py
def route_llm_task(task_type, text_length):
    if task_type == "event_extraction" and text_length < 500:
        return "haiku"  # $0.25 / 1M tokens
    elif task_type == "multi_source_fusion":
        return "sonnet"  # $3 / 1M tokens
    elif task_type == "weekly_report":
        return "sonnet"
    else:
        return "haiku"
```

**2. 每日预算控制**
```python
# llm_budget_tracker.csv
date, task_type, model, tokens_used, cost_usd, budget_usd, remaining_usd
2024-01-15, event_extraction, haiku, 1200000, 0.30, 5.00, 4.70
2024-01-15, weekly_report, sonnet, 50000, 0.15, 5.00, 4.55
```

**3. 缓存和复用**
```python
# 对于重复的事件类型,缓存 prompt 结果
@lru_cache(maxsize=1000)
def extract_event(text_hash):
    # 如果见过相同的文本,直接返回
    pass
```

**4. 批处理**
```python
# 不要每条事件调用一次 API,攒够 10 条一起调用
batch_events = []
for event in new_events:
    batch_events.append(event)
    if len(batch_events) >= 10:
        results = llm_batch_extract(batch_events)
        batch_events = []
```

**预期成本（每月）：**
- 快讯事件抽取：500 条/天 × 30 天 × 500 tokens × $0.25/1M = $1.88
- 盘中急报生成：3 条/天 × 30 天 × 1000 tokens × $0.25/1M = $0.02
