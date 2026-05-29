# Claude Response

- generated_at: 2026-05-28 20:43:36 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_V14_EXTERNAL_REFERENCE_UPGRADE_PROMPT.md
- prompt_sha256_16: 5472f243ec2bbd0d

# 完整升级方案

## 1. 当前方向判断

**正确的部分：**
- 暂停盘中雷达，专注摘要型输出
- 建立回填验证闭环
- 拆分 webhook 来源，block unknown
- 安全事件和 ETF 的严格过滤

**必须砍掉的：**
- **立即砍掉**：`other` 和 `needs_taxonomy_review` 作为事件类型。这是分类系统失败的标志，不是"待完善"，是架构错误
- **立即砍掉**：BTC/ETH 本身的事件（监管、ETF、技术升级）进入 abnormal return 计算。这些是市场本身，不是 alpha 信号
- **暂停 3 个月**：所有样本 <20 条的事件类型。数据不足就是没有统计意义，别自欺欺人
- **立即砍掉**：任何"可能重要"但无法在 1 小时内验证的事件类型

**核心方向错误：**
你们在做"事件分类系统"，但应该做的是"交易相关性过滤器"。

分类是手段，不是目的。目标是：**这条消息发出后 1-4 小时，会不会有人因此调整仓位？** 如果答案是"不会"或"不知道"，就不该进系统。

---

## 2. 应该学习的结构

### 从 `fin-thread` 学习（核心架构）：

```
Journalist (采集层) 
  ↓
Composer (加工层，这是你们的核心价值)
  ↓
Publisher (发布层)
```

**具体映射到你们的系统：**

**Journalist = 数据接入层**
- 快讯源（webhook 分来源）
- 链上监控（Hyperliquid/稳定币/CEX）
- 价格数据（Binance）
- 不做任何判断，只做标准化

**Composer = 情报加工层（你们的护城河）**
- **Stage 1: 交易相关性过滤**（AI 辅助，规则为主）
- **Stage 2: 事件结构化**（提取 symbol/金额/时间/来源）
- **Stage 3: 市场归因检查**（pre-event price-in，regime filter）
- **Stage 4: 历史相似度匹配**（这个事件类型历史上有用吗？）
- **Stage 5: 生成可读摘要**（AI 主导，但有模板约束）

**Publisher = 发布决策层**
- 根据 Composer 输出的"可信度分数"决定：
  - 不发（<60 分）
  - 进入摘要池（60-80 分）
  - 单条推送（>80 分，且历史验证 >10 次）
- 发布后立即启动 follow-up 任务

### 从 `daily_stock_analysis` 学习（产品形态）：

**不要学的：**
- 决策面板（你们不做交易决策）
- 技术指标（不是你们的价值点）

**必须学的：**
```
1. Watchlist 机制
   → 你们的版本：用户可订阅特定 symbol/事件类型/来源

2. 多渠道通知的优先级设计
   → 早晚报（Telegram 群组）
   → 高置信度单条（Telegram 私聊）
   → 周报（Email）

3. 风险提醒的独立模块
   → 安全事件必须独立推送，不能混在摘要里

4. 催化剂日历
   → 你们的版本：已知的 unlock/升级/财报时间
```

---

## 3. Telegram 产品形态

**最终形态（3 个月后）：**

### A. 早报（UTC 00:00，覆盖亚洲早盘前）
```
📊 Crypto Event Intelligence - 早报
时间范围：昨日 16:00 UTC - 今日 00:00 UTC

【高置信度事件】(历史验证 >10 次，胜率 >60%)
• [CEX 上币] Binance 将上线 $TOKEN (来源: 官方公告)
  历史同类事件：1h +8.2% (中位数), 4h +12.1%
  
【安全警报】
• [Active Exploit] $PROTOCOL 遭攻击，损失 $2.3M
  影响资产：$TOKEN (-15% in 10min)

【观察池】(样本不足或置信度 60-80%)
• 3 条 CEX 异常资金流
• 2 条监管传闻（未官方确认）

📈 市场背景：BTC 24h +2.1%, ETH +1.8% (正常波动)
```

### B. 晚报（UTC 12:00，覆盖欧美盘前）
同结构，时间范围 00:00-12:00 UTC

### C. 高置信度单条推送（实时）
```
🚨 [CEX 上币] Binance 上线 $TOKEN

• 官方公告：[链接]
• 历史数据：同类事件 15 次，1h 中位数 +8.2%
• 当前价格：$1.23 (Binance 现货开盘)
• 风险提示：历史有 3 次 (20%) 出现 -5% 以上回撤

⏱ 将在 1h/4h 后回填结果
```

### D. 安全事件独立推送（实时）
```
⚠️ [安全警报] $PROTOCOL 遭 Active Exploit

• 损失金额：$2.3M
• 影响资产：$TOKEN
• 来源：PeckShield + 链上确认
• 当前价格变化：-15% in 10min

🔍 历史同类事件：24h 内平均 -28%，72h 部分恢复至 -12%
```

**当前阶段（接下来 7 天）：**
- **只做早晚报**
- **只推送已验证 >5 次的事件类型**
- **每条事件必须有"历史参考"或标注"样本不足"**

---

## 4. 系统分层重构

```
┌─────────────────────────────────────────┐
│ Journalist Layer (采集层)                │
├─────────────────────────────────────────┤
│ • webhook_binance_ann                    │
│ • webhook_coindesk (block)               │
│ • onchain_hyperliquid                    │
│ • onchain_stablecoin                     │
│ • price_binance                          │
│                                          │
│ 输出：raw_event (标准化 JSON)            │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Composer Layer (加工层) - 5 个 Stage     │
├─────────────────────────────────────────┤
│ Stage 1: Relevance Filter                │
│   • 交易相关性检查 (规则 + AI)            │
│   • 输出：pass/block + reason            │
│                                          │
│ Stage 2: Event Structuring               │
│   • 提取 symbol/amount/time/source       │
│   • 输出：structured_event               │
│                                          │
│ Stage 3: Market Attribution Check        │
│   • pre-event price-in (前 30min 波动)   │
│   • regime filter (BTC 24h 波动 >5%)     │
│   • 输出：attribution_score (0-100)      │
│                                          │
│ Stage 4: Historical Similarity Match     │
│   • 匹配历史同类事件                      │
│   • 计算历史胜率/中位数收益               │
│   • 输出：historical_confidence (0-100)  │
│                                          │
│ Stage 5: Summary Generation              │
│   • 用模板 + AI 生成可读摘要              │
│   • 输出：user_facing_text               │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Publisher Layer (发布决策层)             │
├─────────────────────────────────────────┤
│ 决策逻辑：                                │
│ • confidence < 60: block                 │
│ • 60-80: 进入摘要池                       │
│ • >80 且历史验证 >10 次: 单条推送         │
│ • 安全事件: 独立推送 (无论分数)           │
│                                          │
│ 输出：telegram_message + follow_up_task  │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│ Evaluation Layer (评估层)                │
├─────────────────────────────────────────┤
│ • 1h/4h/24h/72h 价格回填                 │
│ • 计算 abnormal return vs BTC/ETH        │
│ • 更新 source_score / event_type_score   │
│ • 生成质量报告                            │
│                                          │
│ 输出：feedback loop to Composer          │
└─────────────────────────────────────────┘
```

**关键变化：**
1. **Composer 从 1 步变 5 步**，每步输出可审计
2. **Stage 3 (归因检查) 是新增的**，解决"价格已经动了"的问题
3. **Stage 4 (历史匹配) 是核心护城河**，不是简单的事件分类
4. **Publisher 有明确的分数阈值**，不是"感觉重要就发"

---

## 5. 事件类型优先级

### 第一优先级（立即做，已有数据支撑）：
1. **CEX 上币公告**（Binance/Coinbase/OKX 官方）
   - 样本充足，验证逻辑清晰
   - 1h 时间窗口明确
   
2. **Active Exploit（已确认的安全事件）**
   - 有金额、有链上证据、有二次来源确认
   - 24h 时间窗口
   
3. **大额稳定币铸造/销毁**（>$50M）
   - 链上数据可验证
   - 4h 时间窗口

### 第二优先级（样本积累到 20 条后再上线）：
4. **CEX 大额异常流入/流出**（>$10M，头部交易所）
5. **Hyperliquid 大额清算**（>$5M）
6. **ETF 资金流**（仅 BTC/ETH，仅头部发行方，仅 >$100M）

### 立即砍掉：
- ❌ 监管传闻（无法验证）
- ❌ 技术升级预告（时间窗口太长）
- ❌ 社区情绪（无法量化）
- ❌ 合作公告（噪音太多）
- ❌ 代币解锁（除非 >总供应量 5%）
- ❌ 所有 `other` 和 `needs_taxonomy_review`

---

## 6. 质量闸门定义

### 进入系统的最低标准（Composer Stage 1）：
```python
def is_trading_relevant(event):
    """交易相关性检查"""
    
    # 硬性规则（任一不满足直接 block）
    if not event.has_clear_symbol():  # 必须有明确的交易标的
        return False, "no_tradable_symbol"
    
    if not event.has_verifiable_source():  # 来源必须可验证
        return False, "unverifiable_source"
    
    if event.is_btc_eth_itself() and event.type not in ["active_exploit"]:
        return False, "base_asset_event"  # BTC/ETH 本身的事件不进abnormal return
    
    if event.time_to_impact > 24h:  # 影响时间窗口 >24h
        return False, "impact_too_far"
    
    # AI 辅助判断（用于边界情况）
    if event.is_ambiguous():
        ai_score = call_claude_relevance_check(event)
        if ai_score < 0.7:
            return False, f"ai_low_confidence_{ai_score}"
    
    return True, "pass"
```

### 进入摘要池的标准（Composer Stage 4 输出）：
```python
confidence_score = (
    attribution_score * 0.3 +      # 30%: 价格归因清晰
    historical_confidence * 0.5 +   # 50%: 历史验证充分
    source_quality * 0.2            # 20%: 来源可信度
)

if confidence_score >= 60:
    进入摘要池
```

### 单条推送的标准：
```python
if (confidence_score >= 80 and 
    historical_sample_size >= 10 and
    historical_win_rate >= 0.6):
    单条推送
```

### 安全事件特殊通道：
```python
if (event.type == "active_exploit" and
    event.amount_usd >= 1_000_000 and
    event.has_onchain_confirmation() and
    event.has_secondary_source()):
    独立推送（无论 confidence_score）
```

---

## 7. AI 成本控制策略

### 当前问题：
你们可能在用 Claude 做"能用规则解决的事"。

### 成本优化方案：

**只在这 3 个地方用 AI：**

#### 1. Composer Stage 1 的边界情况（每天 <100 次调用）
```python
# 只有规则无法判断时才调用
if event.is_ambiguous():  # 例如：文本提到交易但不确定是否相关
    prompt = f"""
    这条消息是否与加密货币交易直接相关？
    
    消息：{event.text}
    
    只回答 YES/NO 和 1 句理由。
    """
    # 用 Claude Haiku (最便宜)
```

#### 2. Composer Stage 5 的摘要生成（每天 <50 次调用）
```python
# 但要用严格模板约束
prompt = f"""
用以下模板改写事件：

[事件类型] 标题
• 关键信息 1
• 关键信息 2
• 历史参考：{historical_stats}

原始文本：{event.text}
结构化数据：{event.structured}

严格遵守模板，不要添加推测。
"""
# 用 Claude Sonnet (平衡性价比)
```

#### 3. 质量报告的异常分析（每周 1 次）
```python
# 分析为什么某些事件类型表现异常
prompt = f"""
分析以下事件类型的表现异常：

事件类型：{event_type}
历史胜率：{win_rate}
本周胜率：{this_week_win_rate}
样本：{sample_events}

可能的原因是什么？给 3 个假设。
"""
# 用 Claude Opus (最贵，但每周只 1 次)
```

**不要用 AI 的地方：**
- ❌ symbol 提取（用正则 + 交易所 API 校验）
- ❌ 金额解析（用正则）
- ❌ 时间标准化（用 dateparser）
- ❌ 来源分类（用域名白名单）
- ❌ 事件类型分类（用关键词规则）

**成本估算：**
- 当前方案：每天 <200 次 AI 调用
- 假设 Claude Haiku $0.25/1M tokens，Sonnet $3/1M tokens
- 每次调用平均 1K tokens
- **每天成本：<$1**

---

## 8. 可读卡片模板原则

### 核心原则：
1. **结论先行**：第一行就说清楚"发生了什么"
2. **数据支撑**：第二部分给历史参考
3. **风险提示**：第三部分说"可能出错的地方"
4. **可验证性**：第四部分说"我们会怎么验证"

### 模板 A：高置信度单条推送

```
🎯 [事件类型] 一句话标题

━━━━━━━━━━━━━━━━
📋 事件详情
• 标的：$SYMBOL
• 关键信息 1
• 关键信息 2
• 来源：[链接]

━━━━━━━━━━━━━━━━
📊 历史参考 (基于 {N} 次同类事件)
• 1h 中位数：+X.X%
• 4h 中位数：+X.X%
• 胜率：XX% (>0 的比例)
• 最大回撤：-X.X%

━━━━━━━━━━━━━━━━
⚠️ 风险提示
• [具体风险点，例如：历史有 20% 出现反向]
• [市场环境，例如：当前 BTC 波动较大]

━━━━━━━━━━━━━━━━
⏱ 验证计划
将在 1h/4h 后回填价格变化
```

### 模板 B：早晚报中的事件条目

```
• [事件类型] 标题
  ├ 关键信息（1 行）
  ├ 历史：1h +X.X%, 4h +X.X% (N 次样本)
  └ 来源：[简短来源]
```

### 模板 C：安全事件独立推送

```
⚠️ [安全警报] $PROTOCOL 遭 {攻击类型}

━━━━━━━━━━━━━━━━
🚨 紧急信息
• 损失金额：${X.X}M
• 影响资产：$TOKEN
• 攻击方式：[简短描述]
• 当前价格：${X.XX} (-X.X% in Xmin)

━━━━━━━━━━━━━━━━
🔍 来源确认
• 主要来源：[PeckShield/CertiK]
• 链上确认：[Etherscan 链接]
• 官方回应：[有/无]

━━━━━━━━━━━━━━━━
📊 历史同类事件
• 24h 平均跌幅：-X.X%
• 72h 部分恢复至：-X.X%
• 样本数：N 次

━━━━━━━━━━━━━━━━
⏱ 持续监控
将跟踪后续 24h/72h 价格变化
```

### 反面案例（不要这样写）：

❌ **信息堆叠型**
```
事件：Binance 上线 TOKEN
时间：2024-01-01 10:00 UTC
来源：binance_ann
symbol: TOKEN
price: $1.23
volume_24h: $1.2M
market_cap: $50M
abnormal_return_1h: 0.082
abnormal_return_4h: 0.121
quality_score: 0.85
source_score: 0.92
...
```
→ 用户根本不知道该看什么

❌ **结论模糊型**
```
Binance 可能会上线某个代币，历史上类似事件表现不错，但也有风险，请注意。
```
→ 没有任何可执行信息

❌ **过度 AI 型**
```
在加密货币市场的波澜壮阔中，Binance 交易所今日宣布了一项重磅消息...
```
→ 废话太多，用户 3 秒就划走了

---

## 9. 统一发布策略

### 策略框架：

```python
class PublishStrategy:
    """统一的发布决策引擎"""
    
    def __init__(self):
        self.source_scores = self.load_source_scores()  # 从历史评估加载
        self.event_type_scores = self.load_event_type_scores()
        self.regime_detector = RegimeDetector()  # 市场环境检测
    
    def decide(self, event):
        """决策流程"""
        
        # Step 1: 计算综合置信度
        confidence = self.calculate_confidence(event)
        
        # Step 2: 市场环境检查
        regime = self.regime_detector.current_regime()
        if regime == "extreme_volatility":  # BTC 24h >10%
            confidence *= 0.7  # 降低所有事件的置信度
        
        # Step 3: 发布决策
        if confidence < 60:
            return "block", "low_confidence"
        
        elif confidence < 80:
            return "summary_pool", "medium_confidence"
        
        elif confidence >= 80 and event.historical_sample_size >= 10:
            return "instant_push", "high_confidence"
        
        # Step 4: 特殊通道
        if event.type == "active_exploit" and event.amount_usd >= 1_000_000:
            return "security_alert", "critical"
        
        return "block", "unknown"
    
    def calculate_confidence(self, event):
        """置信度计算"""
        
        # 1. 历史验证分数 (50%)
        historical_score = self.get_historical_score(event)
        
        # 2. 归因分数 (30%)
        attribution_score = self.check_attribution(event)
        
        # 3. 来源质量 (20%)
        source_score = self.source_scores.get(event.source, 0.5)
        
        confidence = (
            historical_score * 0.5 +
            attribution_score * 0.3 +
            source_score * 0.2
        ) * 100
        
        return confidence
    
    def get_historical_score(self, event):
        """历史验证分数"""
        
        # 查找历史同类事件
        similar_events = self.find_similar_events(event)
        
        if len(similar_events) < 5:
            return 0.3  # 样本不足，低分
        
        # 计算历史胜率
        win_rate = sum(e.abnormal_return_4h > 0 for e in similar_events) / len(similar_events)
        
        # 计算历史中位数收益
        median_return = np.median([e.abnormal_return_4h for e in similar_events])
        
        # 综合评分
        score = (
            win_rate * 0.6 +  # 胜率权重 60%
            min(median_return / 0.1, 1.0) * 0.4  # 收益权重 40%，封顶在 10%
        )
        
        return score
    
    def check_attribution(self, event):
        """归因检查"""
        
        # 检查事件发生前 30 分钟价格变化
        pre_event_return = self.get_pre_event_return(event.symbol, event.time, minutes=30)
        
        if abs(pre_event_return) > 0.05:  # 前 30 分钟已经涨跌 >5%
            return 0.2  # 可能已经 price-in
        
        # 检查 BTC 同期变化
        btc_return = self.get_btc_return(event.time, hours=1)
        
        if abs(btc_return) > 0.03:  # BTC 1h >3%
            return 0.5  # 市场整体波动大，归因不清晰
        
        return 1.0  # 归因清晰
```

### 实时 follow-up 流程：

```python
class FollowUpEngine:
    """实时跟踪引擎"""
    
    def on_event_published(self, event, publish_type):
        """事件发布后立即启动跟踪"""
        
        # 创建跟踪任务
        tasks = [
            FollowUpTask(event, horizon="1h", scheduled_at=event.time +
