# Crypto Event Intelligence v0.6 - 架构与产品评估

我会按你的 10 个问题逐一回答，然后给出整体架构判断和下一步建议。先说核心结论，再展开细节。

---

## 核心判断（先说结论）

**你现在的系统状态是健康的，但你正处在一个关键的分叉点。**

- ✅ **管道在工作**：500 条进，64 条进 human_review，436 条 discard，比例合理（~13% review rate）
- ⚠️ **auto_publish = 0**：说明你的 relevance scoring + 阈值组合**过于保守**，或者 scoring 没有给出足够的置信度区分
- 🚨 **最大风险**：`other_review` = 212（42%）和 `missing_entity` = 204（41%）。这两个不是"决策"，是"系统看不懂"。在连 TG 之前必须先压下来。

**所以在回答你的问题之前，我要先纠正一个潜在的方向错误：**

> 不要急着把 TG 接上去。你现在缺的不是"发不发"的决策，而是"看不看得懂"的能力。如果 42% 的内容系统判不出类型，那 auto_publish 永远不可能可信。

---

## 逐题回答

### Q1 + Q2 + Q10：TG 发布策略（合并回答）

**应该分两个 TG channel / topic，从 human_review 手动批准开始。**

推荐结构：

```
?? Channel A: #crypto-signals-alpha     (高置信度、单资产、可交易)
?? Channel B: #crypto-macro-regulation  (市场级、监管、宏观)
?? Channel C: #crypto-research-queue    (内部 review，不对外)
```

**为什么不要 day-1 直接 auto_publish：**
- 你的 `relevance_score_realtime` 最高也只有 81.75，且 top 20 全是 human_review，说明 scoring 函数还没有学会"什么叫高置信度"
- 在没有 ground truth（即真实的 abnormal return 标注）之前，auto_publish 的阈值是猜的
- 一次错误的 auto_publish（比如把假黑客新闻发出去）对 channel 信誉的伤害 >> 100 条正确发布的收益

**auto_publish 的最小标准（v0.6 阶段建议不启用，v0.7 启用）：**

| 维度 | 要求 |
|---|---|
| source_count | ≥ 2（多源确认） |
| primary_asset_symbol | 必须在 Binance 现货白名单 |
| event_type_l1 | 不能是 `regulation_macro` / `other_review` |
| relevance_score | ≥ 85（且需要重新校准这个分数） |
| 时效性 | 事件首次出现 < 15 分钟 |
| dedup cluster | 是 cluster 的 primary |
| 历史回测 | 该 event_type 在历史上 abnormal return p50 > 某阈值 |

**最后一条最关键**：auto_publish 应该是**数据驱动的**，不是规则驱动的。

---

### Q3：BTC/ETH 基准（在 TOTAL3 之前）

**短期实用方案，按优先级：**

1. **BTC 事件** → 用 **ETH** 作为 benchmark（市场 beta 代理）
2. **ETH 事件** → 用 **BTC** 作为 benchmark
3. **Altcoin 事件** → 用 **ETH** 作为 benchmark（不是 BTC，因为 alt 和 ETH 相关性更高）

**进阶但便宜的方案：**
- 自己构建一个 "TOP10 ex-event-asset" 等权指数，每分钟从 Binance 拉一次价格，本地缓存
- 这个比等 TOTAL3 数据源更快上线，成本几乎为零

**不要做的事：**
- 不要用纳斯达克 / SPY 做 benchmark（crypto 7×24，传统市场对不齐）
- 不要用 DXY（除非是 macro 事件专门归因）

---

### Q4 + Q5 + Q8 + Q9：可发布性边界（合并回答）

这四个问题本质是同一个：**什么算"crypto event"？** 我建议你引入一个 `tradability_tier` 字段：

| Tier | 定义 | 示例 | 处理 |
|---|---|---|---|
| T1 | 直接影响某个可交易资产 | "黑客攻击 Monad，损失 $76M" | 进 alpha channel |
| T2 | 市场级 / 监管 / 宏观 | "White House BTC Reserve" | 进 macro channel |
| T3 | 间接相关（股票、支付、采用） | "HIVE +35% on AI factory"、"Revolut crypto card" | research-only |
| T4 | 不支持的资产 | HYPE/ONDO/WLD 事件 | research-only，但**保留**，因为这是 v0.7 扩展 Binance 白名单的优先级信号 |

**具体回答：**

- **Q4 (支付/采用)**: T3，research-only。Revolut 卡不会引起 BTC abnormal return。
- **Q5 (unsupported assets)**: 进 review queue，但不发布。**关键**：统计 unsupported asset 的出现频率，这是你扩展白名单的 roadmap。
- **Q8 (miner equity / AI data center)**: T3。HIVE / MARA / RIOT 的股价新闻**不是** BTC 事件。除非新闻本身是 "MARA 增持 5000 BTC" 这种链上行为。
- **Q9 (法律/欺诈)**: 新建 L1 类型 `legal_enforcement`。理由：
  - `hack_security` 应该专指**链上漏洞利用 / 协议被攻击**
  - `regulation_macro` 应该专指**政策 / 法规 / 央行 / 政府声明**
  - "俄亥俄州居民庞氏骗局被判 9 年" 既不是协议被黑，也不是宏观政策，强行归类会污染两个 bucket 的统计

---

### Q6：opinion / analysis 是否可发布

**v0.6 阶段：不可发布。** 但要细分：

| 类型 | 处理 |
|---|---|
| 匿名 KOL 推特观点 | discard |
| 具名分析师价格预测（"Delphi: BTC 可能跑赢"）| research-only |
| **具名机构发布的数据/研究**（Santiment 链上数据、Glassnode 报告） | **可发布**，但归类为 `onchain_data` 不是 opinion |
| Lookonchain / Arkham 的链上追踪 | 可发布，归类为 `whale_position` 或 `hack_security` |

**关键洞察**：你当前把 Santiment 的"100 BTC 钱包数 = 20229"判为 `whale_position` 是对的。这不是 opinion，是**衍生数据**。需要在 entity dictionary 里把 Santiment / Glassnode / Lookonchain / Arkham / Nansen 标记为 `data_source` 而不是 `analyst`。

---

### Q7：scraped 长文 / footer noise

**激进处理**。原因：

- discard reason 中 `scraped_footer_noise` 出现 8 次，看似不多
- 但 `missing_entity` 出现 317 次（63%），其中很大一部分根源是 footer 污染让 entity extractor 抓错
- 你的成本是 LLM token / 处理时间，footer noise 是纯负价值输入

**具体规则：**

1. 单条原文 > 2000 chars → 截断到前 800 + 后 200（事件通常在头尾）
2. 检测到 navigation 模式（"Home | About | Subscribe | ..."）→ 直接 discard，不进 LLM
3. 同一域名（如某新闻站）footer 模板 fingerprint 化，遇到就剥离
4. 优先 Twitter / Telegram 原帖 over 转载的新闻站

---

## 整体架构评估

### 你做对的事

1. **publish_decision 三态设计正确**（auto / review / discard）
2. **review queue 分两个**（publish_review vs other_review）非常关键，很多人会合并
3. **dedup cluster + primary** 是对的做法
4. **discard reason 可以多标签**（用逗号分隔），这给你后续做 reason 共现分析留了空间

### 你需要警惕的事

1. **relevance_score_realtime 的分布太窄**（top 都在 68-82 之间），说明 scoring 函数区分度不够。建议：
   - 让 score 范围拉开到 0-100，目标是让 top 5% 真正脱颖而出
   - 引入 source quality weight（CoinDesk vs 匿名 Twitter 应该差很多）
   - 引入 entity confidence weight

2. **`other_review` 212 条是黑洞**。这不是一个"决策"，是"系统不会判"。必须分析：
   - 这 212 条里，有多少是因为 event_type classifier 没覆盖？
   - 有多少是真正的边界情况？
   - 建议抽样 30 条人工标注，反推 classifier 缺口

3. **discard reason 组合爆炸**：你有 40+ 种 reason 组合。建议：
   - 引入 reason 优先级（primary_reason），其他作为 secondary
   - 这样 distribution 表可读性会好 10 倍

---

## v0.6.5 → v0.7 路线图建议

### v0.6.5（2 周内）—— 修地基，不接 TG

**目标**：让 `other_review` 从 42% 降到 < 15%，`missing_entity` 从 41% 降到 < 20%。

- [ ] Entity dictionary 扩充：增加 data_source 类（Santiment/Glassnode/Lookonchain/Arkham/Nansen/PeckShield）
- [ ] 新增 L1 类型：`legal_enforcement`, `onchain_data`
- [ ] Footer noise 检测器（基于模板 fingerprint）
- [ ] 引入 `tradability_tier` 字段（T1-T4）
- [ ] discard reason 优先级化（primary + secondary）
- [ ] Relevance score 重校准，让分布拉开
- [ ] 对 200 条样本做人工 ground truth 标注（这是 v0.7 一切的基础）

### v0.7（4-6 周）—— 接 TG，但只是 human_review 推送

**目标**：建立"人工批准 → 发布"的闭环，开始积累 ground truth。

- [ ] TG bot 把 human_review queue 推给运营，按钮：批准 / 拒绝 / 改类
- [ ] 批准/拒绝的数据回流到 ground truth 表
- [ ] 接入 Binance kline，对每条已发布事件做 T+15min / T+1h / T+4h abnormal return 计算
- [ ] 分两个 TG channel：alpha vs macro
- [ ] 开始有"事件 → 真实收益"的回测数据

### v0.8（v0.7 跑满 4 周后）—— 启用 auto_publish

**前提**：有 ≥ 200 条已发布事件的 abnormal return 数据。

- [ ] 用 ground truth 训练 / 校准 auto_publish 阈值
- [ ] 只对历史表现好的 (event_type × asset_tier) 组合启用 auto_publish
- [ ] 监控 auto_publish 的事后准确率，低于阈值自动回退到 human_review

---

## 一个直接的建议

你的 question backlog 是一个非常好的工程实践，但里面**缺了一个最关键的问题**：

> **Q11: 我们如何获得 ground truth？谁来标注？多大样本量？**

这个问题不解决，Q1/Q10（auto_publish 阈值）永远只能拍脑袋。建议把这个加进 backlog，下一轮提问时一并讨论。

---

需要我针对其中任何一块（比如 entity dictionary 扩充的具体清单、relevance scoring 函数的重构、abnormal return 计算的实现细节）深入展开吗？