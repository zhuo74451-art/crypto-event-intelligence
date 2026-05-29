# Claude v0.7 Watcher Server Review

# 直接评审：v0.7 First-Hand Watcher Server Rollout

## 1. 当前源优先级与下一批接入

**当前源评价：**
- ✅ **Ethereum watched address ERC20 transfers**：合理，但交易所热钱包是噪音源
- ✅ **USDT/USDC treasury mint/burn**：高价值，直接反映市场流动性预期
- ⚠️ **Hyperliquid curated large positions**：价值高但需要严格筛选规则

**优先级问题：**
你缺少最直接的**市场结构信号**。当前都是"钱在哪"，没有"价格怎么动"。

**下一批必接（按优先级）：**

1. **CEX 异常深度变化**（最优先）
   - Binance/OKX 前3档深度突变 >30%
   - 大单挂撤单（>100万美元）
   - 这是最直接的市场结构信号

2. **链上 DEX 大额 swap**
   - Uniswap V3/V2 单笔 >50万美元
   - 过滤掉 MEV bot 和套利
   - 只要 WETH/USDC/USDT/WBTC 主流对

3. **Funding rate 异常**
   - Binance/Bybit/OKX 永续合约 funding rate 突破 ±0.1%
   - 或 1小时内变化 >0.05%

4. **链上清算事件**
   - Aave/Compound/MakerDAO 大额清算 >100万美元
   - 这是风险信号，不是交易信号

**不要接的：**
- ❌ Twitter/X 监控（二手且噪音极大）
- ❌ Discord/Telegram 爬虫（法律风险+噪音）
- ❌ NFT 交易（与你的 crypto event intelligence 定位不符）


## 2. Production Gate 规则（严格版）

你当前的 gate 太松。7条候选5条 eligible = 71% 通过率，这会污染群。

**建议 Production Gate（目标通过率 20-30%）：**

```python
PRODUCTION_GATE = {
    # 硬性阻断（任一触发直接 FAIL）
    "hard_blocks": {
        "trading_advice_words": [
            "买入", "卖出", "做多", "做空", "建仓", "平仓",
            "buy", "sell", "long", "short", "enter", "exit"
        ],
        "min_amount_usd": {
            "erc20_transfer": 500_000,      # 50万美元
            "treasury_mint": 10_000_000,    # 1000万美元
            "treasury_burn": 10_000_000,
            "hyperliquid_position": 2_000_000,  # 200万美元
            "cex_netflow": 5_000_000,       # 500万美元（聚合后）
        },
        "min_confidence": 0.6,
        "blacklist_addresses": [
            # MEV bots, known arbitrage contracts
        ]
    },
    
    # 分级通过（需同时满足）
    "tier_1_publish": {  # 直接发布
        "conditions": "ANY",
        "rules": [
            {"amount_usd": ">= 5M", "confidence": ">= 0.8"},
            {"event_type": "treasury_mint", "amount_usd": ">= 50M"},
            {"strength": "high", "confidence": ">= 0.75"},
            {"raw_signal_type": "hyperliquid_position", "amount_usd": ">= 10M"}
        ]
    },
    
    "tier_2_review": {  # 记录但不发布，人工复核
        "conditions": "ALL",
        "rules": [
            {"amount_usd": ">= min_threshold", "< tier_1_threshold"},
            {"confidence": ">= 0.6", "< 0.8"},
            {"no_recent_similar_events": "1h"}  # 去重
        ]
    },
    
    # 时间窗口去重
    "dedup": {
        "same_address_same_type": "6h",
        "same_token_similar_amount": "2h",  # ±20% 金额视为相似
    },
    
    # 每日配额（防止刷屏）
    "daily_quota": {
        "max_events_per_day": 15,
        "max_per_source": {
            "erc20_transfer": 5,
            "treasury": 3,
            "hyperliquid": 4,
            "cex_netflow": 3
        }
    }
}
```

**关键变化：**
- 大幅提高金额阈值（ERC20 从不明确到50万美元）
- 增加每日配额上限（15条/天）
- 增加时间窗口去重（同类事件6小时内只发一次）
- 分层：Tier 1 直接发，Tier 2 记录待复核


## 3. 交易所热钱包监控策略

**当前问题：**
单笔转账监控 = 噪音地狱。Binance 热钱包每小时可能有上百笔充提。

**正确做法：**

```python
CEX_WALLET_STRATEGY = {
    "default_mode": "net_flow_aggregation",  # 默认只做净流量
    
    "aggregation_windows": {
        "short": "1h",   # 1小时净流入/流出
        "medium": "4h",  # 4小时净流入/流出
        "long": "24h"    # 24小时净流入/流出
    },
    
    "publish_conditions": {
        "net_inflow": {
            "1h": ">= 20M USD",   # 1小时净流入 >= 2000万
            "4h": ">= 50M USD",
            "24h": ">= 100M USD"
        },
        "net_outflow": {
            "1h": ">= 20M USD",
            "4h": ">= 50M USD",
            "24h": ">= 100M USD"
        }
    },
    
    "single_tx_exception": {  # 仅在极端情况发单笔
        "min_amount": 50_000_000,  # 单笔 >= 5000万美元
        "rare_tokens": ["WBTC", "stETH"],  # 或稀有大额代币
        "unusual_counterparty": True  # 且对手方不是常见做市商
    },
    
    "ignore_patterns": [
        "known_market_makers",  # Wintermute, Jump, Alameda 遗产等
        "internal_transfers",   # 交易所内部钱包互转
        "regular_settlement"    # 每日固定时间的结算流水
    ]
}
```

**具体实现：**
- 每5分钟采集，但每1小时聚合一次判断是否发布
- 发布时说明："过去1小时 Binance 热钱包净流入 2500万 USDT"
- 不要说"Binance 转出 1000万 USDT"（单笔无意义）


## 4. Hyperliquid 大仓位发布策略

**应该发的：**
```python
HYPERLIQUID_PUBLISH = {
    "position_open": {
        "min_size_usd": 5_000_000,  # 新开仓 >= 500万
        "leverage": ">= 5x",         # 且杠杆 >= 5倍
        "tokens": ["BTC", "ETH", "SOL", "major_alts"]  # 主流币
    },
    
    "position_close": {
        "min_size_usd": 10_000_000,  # 平仓 >= 1000万
        "pnl_threshold": ">= 500k or <= -500k"  # 且盈亏显著
    },
    
    "position_liquidation": {
        "min_size_usd": 2_000_000,  # 清算 >= 200万（风险信号）
        "always_publish": True
    },
    
    "aggregated_flow": {  # 聚合信号
        "net_long_short_change": {
            "1h_window": True,
            "min_change_usd": 20_000_000,  # 1小时内多空净变化 >= 2000万
            "description": "过去1小时 Hyperliquid BTC 多头净增 2500万美元"
        }
    }
}
```

**只记录不发的：**
- 小于500万美元的仓位
- 低杠杆（<3x）的现货型仓位
- 山寨币（市值排名 >50）的仓位
- 已知做市商/套利账户的仓位

**发布格式：**
```
🔍 Hyperliquid 大仓位观察

• 类型：新开多仓
• 标的：BTC-PERP
• 规模：$8,500,000（8.5M）
• 杠杆：10x
• 入场价：$67,234
• 时间：2024-01-15 14:23 UTC

⚠️ 观察要点：
- 高杠杆大额多仓，可能预期短期上涨
- 需关注后续是否有跟随仓位
- 清算价约 $60,800（-9.6%）

🔗 复核：[Hyperliquid Explorer链接]

⚡️ 强度：中 | 置信：75%
```


## 5. 稳定币 Treasury 事件解释

**当前误导风险：**
- Mint ≠ 看涨，Burn ≠ 看跌
- Treasury 操作领先市场需求 1-7 天

**正确解释框架：**

```python
TREASURY_INTERPRETATION = {
    "USDT_mint": {
        "title": "USDT Treasury 增发",
        "interpretation": [
            "✅ Tether 向授权地址增发 USDT",
            "⏱ 通常领先市场需求 1-3 天",
            "📊 历史上与后续 CEX 充值、市场流动性增加相关",
            "⚠️ 不代表立即流入市场，可能在 Treasury 停留数日"
        ],
        "avoid_saying": [
            "❌ 市场即将上涨",
            "❌ 大量资金入场",
            "❌ 利好信号"
        ],
        "correct_tone": "观察到 Tether 增发 5000万 USDT，通常预示未来数日市场流动性需求增加，但不代表立即影响价格。"
    },
    
    "USDT_burn": {
        "interpretation": [
            "✅ Tether 销毁 USDT（通常因赎回或合规）",
            "📊 可能反映机构赎回或市场流动性需求下降",
            "⚠️ 也可能是常规库存管理，需结合其他信号"
        ],
        "correct_tone": "观察到 Tether 销毁 3000万 USDT，可能反映近期赎回需求或流动性调整，需持续观察后续市场表现。"
    },
    
    "USDC_mint": {
        "interpretation": [
            "✅ Circle 增发 USDC",
            "📊 USDC 增发通常更直接反映机构需求（相比 USDT）",
            "⏱ 从 mint 到流入 CEX 通常 <24h"
        ]
    }
}
```

**发布模板：**
```
💵 USDT Treasury 增发观察

• 金额：$50,000,000
• 操作：Mint（增发）
• 地址：0x5754...（Tether Treasury）
• 时间：2024-01-15 10:30 UTC

📊 历史规律：
- USDT 增发通常领先 CEX 充值 1-3 天
- 过去 30 天内 5 次增发，3 次后 48h 内 BTC 上涨
- 不代表立即影响价格

⚠️ 观察要点：
- 关注后续是否转入交易所
- 结合 CEX 净流入数据判断
- 单一信号不构成交易依据

🔗 复核：[Etherscan链接]

⚡️ 强度：低 | 置信：60% | 类型：流动性先导
```


## 6. 一手信号与二手新闻的分发策略

**不要放在同一个群。**

**推荐架构：**

```
Telegram 频道结构：

1. 📰 【主频道】Crypto Event Intelligence
   - 二手快讯（已筛选的高质量新闻）
   - 发布频率：5-10 条/天
   - 受众：所有订阅者

2. 🔍 【子频道】On-Chain Signals (Alpha)
   - 一手链上信号
   - 发布频率：3-8 条/天
   - 受众：进阶用户
   - 标注：实验性质，需自行判断

3. 📊 【子频道】Market Structure Alerts
   - CEX 深度、funding rate、清算等
   - 发布频率：5-15 条/天
   - 受众：交易员

4. 🧪 【私有频道】Signal Lab (Internal)
   - 所有候选事件（包括未通过 gate 的）
   - 用于回测和规则调优
   - 仅团队可见
```

**为什么要分开：**
- 二手新闻 = 已确认事件，用户期望高准确性
- 一手信号 = 领先指标，假阳性率天然更高
- 混在一起会降低主频道的可信度
- 分层可以让用户自选信息密度

**标签系统（如果一定要合并）：**
```
每条消息带标签：
📰 [二手新闻] - 已确认事件
🔍 [链上观察] - 一手信号，待验证
📊 [市场结构] - 交易数据
⚠️ [风险提示] - 清算、异常波动
```


## 7. 当前最大残留风险（按严重程度）

### 🔴 严重（会毁掉产品）

1. **AI 生成交易建议泄漏**
   - 风险：LLM 在总结时自动生成"建议买入"类表述
   - 后果：法律风险 + 用户亏损后追责
   - 缓解：硬编码正则表达式拦截 + LLM system prompt 强约束 + 人工抽查前100条

2. **低质量信号污染群导致用户流失**
   - 风险：当前 71% 通过率太高，用户会认为是垃圾信息
   - 后果：7天内取关率 >50%
   - 缓解：立即实施严格 gate（目标通过率 20-30%）

3. **交易所热钱包日常流水刷屏**
   - 风险：Binance 热钱包每小时几十笔，会淹没真实信号
   - 后果：用户关闭通知 → 错过重要信息
   - 缓解：立即改为净流量聚合，单笔阈值提高到5000万美元

### 🟡 中等（会拖累进度）

4. **缺少回测验证机制**
   - 风险：发了几百条信号，不知道哪些有效
   - 后果：无法迭代优化，盲目调参
   - 缓解：v0.8 必须实现 1h/4h/24h 价格回填和异常收益计算

5. **事件去重逻辑缺失**
   - 风险：同一个大额转账，Etherscan、自有节点、第三方 API 各报一次
   - 后果：重复发送 3 次同一事件
   - 缓解：基于 (tx_hash, event_type, amount) 的 6 小时去重窗口

6. **没有人工复核流程**
   - 风险：完全依赖 AI/规则，边界 case 无人处理
   - 后果：误发或漏发关键事件
   - 缓解：Tier 2 事件进入 Notion/Airtable 待复核队列

### 🟢 低（可以忍受）

7. **Hyperliquid 仓位数据延迟**
   - 风险：API 可能有 1-5 分钟延迟
   - 后果：信号略微滞后，但仍有价值
   - 缓解：标注"数据延迟约 2-5 分钟"

8. **缺少 Web 界面查看历史**
   - 风险：用户只能在 TG 翻聊天记录
   - 后果：用户体验差，但不影响核心功能
   - 缓解：v0.9 或更晚再做


## 8. 未来 7 天行动清单

### ✅ 必须做（不做会出严重问题）

1. **实施严格 Production Gate**
   - 将 ERC20 转账阈值提高到 50 万美元
   - 增加每日配额上限（15 条/天）
   - 增加 6 小时去重窗口
   - **deadline: 2 天内**

2. **交易所热钱包改为净流量聚合**
   - 停止发送单笔转账
   - 改为 1h/4h 净流入流出
   - 阈值：1h >= 2000 万美元
   - **deadline: 3 天内**

3. **硬编码交易建议拦截器**
   - 正则表达式拦截 50+ 个交易建议词汇
   - 包括中英文、变体、emoji 组合
   - 拦截后直接 FAIL + 告警
   - **deadline: 1 天内（最高优先级）**

4. **建立 Tier 2 人工复核队列**
   - 不确定的事件进入 Notion database
   - 每天花 15 分钟复核
   - 积累边界 case 用于优化规则
   - **deadline: 3 天内**

### 🟢 应该做（提升质量）

5. **接入 CEX 深度异常监控**
   - Binance BTC/ETH 前 3 档深度变化 >30%
   - 这是最直接的市场结构信号
   - **deadline: 7 天内**

6. **实现基础回测框架**
   - 发布后 1h/4h/24h 价格回填
   - 计算 abnormal return（已有 BTC/ETH 基准）
   - 存入数据库，不需要立即可视化
   - **deadline: 7 天内**

7. **优化 Hyperliquid 仓位筛选**
   - 实施本文第 4 节的分级发布规则
   - 增加已知做市商黑名单
   - **deadline: 5 天内**

### ❌ 不要做（看起来酷但会分散精力）

8. **不要做 Web Dashboard**
   - 现在用户只有你自己和几个测试者
   - TG 频道足够，Web 界面是过早优化
   - **至少等到 v0.9 或有 100+ 真实用户**

9. **不要接入 Twitter/X 监控**
   - 噪音极大，需要复杂 NLP
   - 与"一手信号"定位冲突
   - **至少等到二手新闻和链上信号都稳定后**

10. **不要做实时 Alert 推送（除了 TG）**
    - 不要做 Discord bot、Email、SMS
    - 一个渠道做好就够了
    - **至少等到 v1.0**

11. **不要做复杂的 AI 模型训练**
    - 现在数据量不够（<1000 条标注）
    - 规则 + GPT-4 已经够用
    - **至少等到积累 5000+ 条标注数据**


## 9. 哪些功能看起来很酷但现在不该做

### 🚫 诱人但危险的功能

1. **"AI 预测价格涨跌"**
   - 看起来：用户最想要的功能
   - 实际：法律风险 + 技术上不可能准确 + 毁掉产品定位
   - 为什么不做：你是 intelligence，不是 trading signal

2. **"社交功能：用户评论、点赞、分享观点"**
   - 看起来：增加用户粘性
   - 实际：变成低质量论坛，需要审核团队
   - 为什么不做：你不是 TradingView 或 CT（Crypto Twitter）

3. **"接入 100+ 数据源"**
   - 看起来：数据越多越好
   - 实际：每个源都需要维护、去噪、调参
   - 为什么不做：5 个高质量源 > 50 个低质量源

4. **"实时语音播报"**
   - 看起来：很科幻
   - 实际：用户不会听，TTS 质量差
   - 为什么不做：TG 通知已经够实时了

5. **"区块链上存证"**
   - 看起来：去中心化、不可篡改
   - 实际：Gas 费、延迟、没有实际需求
   - 为什么不做：PostgreSQL 已经够用

6. **"多语言支持（英文、韩文、日文）"**
   - 看起来：扩大用户群
   - 实际：翻译质量难保证，维护成本高
   - 为什么不做：先把中文做到极致，再考虑英文

### ✅ 真正有价值但要延后的功能

7. **回测可视化 Dashboard**（v0.9）
   - 有价值，但现在数据量不够
   - 等积累 500+ 条已发布事件再做

8. **用户自定义 watchlist**（v1.0）
   - 有价值，但现在用户太少
   - 等有 50+ 付费用户再做

9. **API 接口给量化团队**（v1.1）
   - 有价值，但现在数据质量不稳定
   - 等回测验证有效后再开放


## 10. v0.8 验收标准（项目经理视角）

### 🎯 核心指标（必须达成）

1. **信号质量**
   - 每日发布事件数：8-15 条（不能更多）
   - 误报率（人工判断无价值）：<10%
   - 重复事件率：<5%
   - 包含交易建议的事件数：0 条（零容忍）

2. **系统稳定性**
   - Watcher 服务 uptime：>99%（7天内宕机 <2 小时）
   - 数据采集延迟：<5 分钟（P95）
   - TG 发送成功率：>99.5%

3. **回测能力**
   - 100% 的已发布事件有 1h/4h/24h 价格回填
   - 能计算 abnormal return（相对 BTC/ETH）
   - 数据存储在 PostgreSQL，可导出 CSV

### 📋 功能清单（必须完成）

4. **Production Gate 已实施**
   - [ ] ERC20 转账阈值 >= 50 万美元
   - [ ] 交易所净流量阈值 >= 2000 万美元（1h）
   - [ ] Hyperliquid 仓位阈值 >= 500 万美元
   - [ ] 每日配额上限 15 条
   - [ ] 6 小时去重窗口
   - [ ] 交易建议词汇硬拦截（50+ 词）

5. **数据源优化**
   - [ ] 交易所热钱包改为净流量聚合
   - [ ] Hyperliquid 仓位分级发布规则
   - [ ] 稳定币 Treasury 事件标准化解释模板
   - [ ] 已接入 CEX 深度异常监控（Binance BTC/ETH）

6. **回测框架**
   - [ ] 自动回填 1h/4h/24h 价格
   - [ ] 计算 abnormal return
   - [ ] 数据存储在 `event_performance` 表
   - [ ] 可导出 CSV 用于分析

7. **人工复核流程**
   - [ ] Tier 2 事件进入 Notion/Airtable
   - [ ] 每日复核 SOP 文档
   - [ ] 边界 case 记录在案

### 🧪 测试标准（验收前必须通过）

8. **72 小时生产环境测试**
   - 在真实服务器运行 72 小时
   - 记录所有发布的事件
   - 人工评审每一条，标注：
     - ✅ 有价值
     - ⚠️ 边界 case
     - ❌ 误报
   - 要求：✅ >= 85%，❌ <= 10%

9. **压力测试**
   - 模拟 Binance 热钱包 1 小时内 100 笔转账
   - 验证只发送 1 条聚合消息
   - 模拟同一事件从 3 个源重复上报
   - 验证去重逻辑生效

10. **回测验证**
    - 随机抽取 20 条已发布事件
    - 人工验证价格回填准确性（误差 <1%）
    - 验证 abnormal return 计算逻辑正确

### 📊 文档交付（必须完成）

11. **运维文档**
    - [ ] Watcher 服务部署 SOP
    - [ ] 常见故障排查手册
    - [ ] 数据库 schema 文档
    - [ ] API 接口文档（内部使用）

12. **产品文档**
    - [ ] 事件类型定义和解释标准
    - [ ] Gate 规则说明文档
    - [ ] 用户指南（如何解读不同类型信号）

### 🚫 验收不通过条件（任一触发）

- 72 小时测试期间发送任何包含交易建议的消息
- 单日发送事件数 >20 条（刷屏）
- 误报率 >15%
- Watcher 服务宕机 >4 小时且无告警
- 回测数据缺失率 >5%

---

## 最后的直接建议

你现在最大的风险不是功能不够，而是**质量控制不够严格**。

71% 的通过率意味着你在用"宁可错发，不要漏发"的策略，这对 intelligence 产品是致命的。用户宁可每天只收到 5 条高质量信号，也不要 15 条里有 5 条是噪音。

**立即行动（今天就做）：**
1. 把所有阈值提高 2-5 倍
2. 加上每日配额上限
3. 硬编码交易建议拦截器

**7 天内必须完成：**
- 严格 gate + 净流量聚合 + 回测框架

**不要做：**
- Web dashboard
- 多语言
- 社交功能
- 任何"AI 预测"相关的功能

你的产品定位是对的（intelligence 不是 trading signal），但执行上需要更克制。记住：**少即是多，质量压倒一切**。