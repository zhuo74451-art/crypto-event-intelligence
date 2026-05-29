# Claude Response

- generated_at: 2026-05-29 12:52:15 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_NEXT_PROMPT.md
- prompt_sha256_16: 825af2ca0fc0608a

# 外部顾问评审意见：清算墙、巨鲸仓位、链上监控与快讯信息流整合方案

## 一、方向判断：70分，有三个根本性问题

### 1.1 当前方向的正确部分 ✓

- **不做交易机器人，做情报系统**：正确。市场上交易机器人已经饱和，但高质量情报筛选是真需求。
- **历史回测验证信号质量**：非常正确。这是你们和快讯搬运工的本质区别。
- **去掉"中性/偏高/偏低"标签，只保留分位数**：正确。绝对判断容易误导，相对位置更客观。
- **设置阈值过滤噪音**：正确方向，但阈值设置有问题(后面详述)。

### 1.2 当前最大的三个根本性问题 ✗

#### 问题1：**你们在用"监控样本"做"市场推断"**

**现状**：
- 监控 3.52 亿美元仓位
- 占 Hyperliquid 总 OI 5.21%
- 用这 5% 生成"清算墙"

**问题**：
这不是清算墙，这是"你监控的几个地址的清算价位置"。

真实的清算墙是：**全市场在某个价格区间的清算密集度**。

**类比**：
就像你在北京三环监控了 20 个路口的车流，然后说"北京不堵车"。你监控的样本可能确实不堵，但不代表全市场。

**后果**：
- 当前显示"近 10% 清算仓位：0"，但实际市场可能在某个价位有巨大清算墙
- 用户会误以为"没有清算风险"
- 真正的清算瀑布来临时，你的系统毫无预警

**解决方向**：
1. **明确区分两类数据**：
   - **监控地址清算风险**：这是"巨鲸追踪"，不是"市场清算墙"
   - **全市场清算热力图**：需要接第三方数据源

2. **卡片命名要诚实**：
   - ❌ "清算墙分析"
   - ✓ "监控地址清算风险"
   - ✓ "市场清算密集区(第三方数据)"

#### 问题2：**信息层级混乱，没有清晰的"决策树"**

**现状**：
- 盘中雷达
- 单条快讯
- 早午晚报
- 大户仓位卡
- 清算墙卡
- 链上资金流卡

**问题**：
这些卡片之间没有清晰的**触发逻辑**和**优先级关系**。

**用户视角的真实场景**：

```
08:30 收到早报
09:15 收到 BTC 大户加仓卡
09:20 收到 BTC 链上大额转账卡
09:25 收到 BTC 快讯：某交易所充值增加
09:30 收到盘中雷达：BTC 资金费率异常

用户：？？？这四条到底是一件事还是四件事？
```

**根本原因**：
你们在用"数据源"组织信息，而不是用"事件"组织信息。

**解决方向**：
需要一个**事件聚合引擎**：
1. 同一资产、同一时间窗口(30分钟)的多个信号 → 合并成一个"资产动态卡"
2. 按信号强度排序：一手数据 > 二手快讯
3. 按时效性分流：
   - **即时打断**(盘中雷达)：清算触发、巨鲸突变、黑天鹅
   - **定时摘要**(早午晚报)：趋势变化、结构风险、背景信息
   - **不发送**(仅记录)：低质量快讯、重复信息

#### 问题3：**回测方法论有致命缺陷**

**现状**：
- 快讯 → 候选 → 事件样本 → 价格回填 → abnormal return

**问题**：
这套方法只能验证"事件发生后价格是否变化"，但不能验证：

1. **信号是否提前于价格**：
   - 如果快讯发布时价格已经涨了 5%，abnormal return 还有意义吗？
   - 链上转账发生在 T0，但你 T0+30min 才推送，这时价格已经反应了

2. **信号是否独立于噪音**：
   - 市场每天有 100 条快讯，你回测了 20 条"有效"的
   - 但用户实时收到的是全部 100 条，其中 80 条是噪音
   - 回测结果无法反映真实使用体验

3. **信号组合效应**：
   - 单独看"资金费率异常"可能没用
   - 但"资金费率异常 + 大户加仓 + 链上充值"组合可能很强
   - 你的回测框架无法验证组合信号

**解决方向**：
需要**前瞻性回测**(forward-looking backtest)：
1. 在历史时间点 T，用当时可获得的数据，生成信号
2. 检查信号发出时，价格是否已经 price-in
3. 统计信号发出后的 hit rate 和 false positive rate
4. 按市场状态(trending/ranging/volatile)分组验证

---

## 二、完整架构方案

### 2.1 数据分层架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户界面层                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │盘中雷达  │  │资产动态卡│  │早午晚报  │  │专题深度卡│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                      事件聚合引擎                              │
│  • 时间窗口合并(30min)                                         │
│  • 资产维度聚合                                                │
│  • 信号强度评分                                                │
│  • 去重与优先级排序                                            │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                      信号标准化层                              │
│  • 统一时间戳                                                  │
│  • 统一资产标识                                                │
│  • 统一信号强度(0-100)                                         │
│  • 统一置信度(0-1)                                             │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                      原始数据采集层                            │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 一手数据源   │  │ 二手数据源   │  │ 市场基础数据 │         │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤         │
│  │• 链上监控    │  │• 快讯源      │  │• 价格/成交   │         │
│  │• 巨鲸仓位    │  │• 社交媒体    │  │• 资金费率    │         │
│  │• 清算热力图  │  │• 公告        │  │• 持仓量      │         │
│  │• CEX充提     │  │              │  │• 波动率      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据表设计

#### 表1: `raw_signals` (原始信号表)

```sql
CREATE TABLE raw_signals (
    signal_id TEXT PRIMARY KEY,
    source_type TEXT,  -- 'onchain', 'whale_position', 'liquidation', 'news', 'market'
    source_name TEXT,  -- 'etherscan', 'hyperliquid', 'coinglass', 'cryptopanic'
    timestamp_utc TIMESTAMP,
    asset TEXT,  -- 标准化资产代码: BTC, ETH, SOL
    signal_category TEXT,  -- 'transfer', 'position_change', 'liquidation_risk', 'funding_rate'
    
    -- 原始数据(JSON)
    raw_data JSON,
    
    -- 标准化字段
    direction TEXT,  -- 'long', 'short', 'neutral', 'inflow', 'outflow'
    magnitude REAL,  -- 标准化幅度(0-100)
    confidence REAL,  -- 置信度(0-1)
    
    -- 元数据
    is_first_hand BOOLEAN,  -- 是否一手数据
    latency_seconds INTEGER,  -- 从事件发生到采集的延迟
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_time_asset ON raw_signals(timestamp_utc, asset);
CREATE INDEX idx_signals_source ON raw_signals(source_type, source_name);
```

#### 表2: `aggregated_events` (聚合事件表)

```sql
CREATE TABLE aggregated_events (
    event_id TEXT PRIMARY KEY,
    asset TEXT,
    event_start_time TIMESTAMP,
    event_end_time TIMESTAMP,
    
    -- 聚合的信号
    signal_ids TEXT,  -- JSON array of signal_ids
    signal_count INTEGER,
    first_hand_count INTEGER,
    
    -- 综合评分
    overall_strength REAL,  -- 0-100
    overall_confidence REAL,  -- 0-1
    novelty_score REAL,  -- 新颖度(0-1), 是否是新变化
    
    -- 分类
    event_type TEXT,  -- 'whale_accumulation', 'liquidation_cascade', 'funding_squeeze'
    urgency TEXT,  -- 'immediate', 'digest', 'background'
    
    -- 发送状态
    sent_to_telegram BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP,
    card_type TEXT,  -- 'radar', 'asset_card', 'digest'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 表3: `signal_backtest` (回测表)

```sql
CREATE TABLE signal_backtest (
    backtest_id TEXT PRIMARY KEY,
    signal_id TEXT,
    event_id TEXT,
    
    -- 回测时间点
    signal_time TIMESTAMP,
    
    -- 价格数据
    price_at_signal REAL,
    price_15m_before REAL,
    price_15m_after REAL,
    price_1h_after REAL,
    price_4h_after REAL,
    price_24h_after REAL,
    
    -- 收益率
    return_15m REAL,
    return_1h REAL,
    return_4h REAL,
    return_24h REAL,
    
    -- 市场状态
    market_regime TEXT,  -- 'trending_up', 'trending_down', 'ranging', 'volatile'
    volatility_percentile REAL,
    volume_percentile REAL,
    
    -- 是否已经price-in
    is_priced_in BOOLEAN,  -- 信号发出前15分钟涨跌幅>2%
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 三、清算墙：分层实现方案

### 3.1 明确区分两类清算数据

#### 类型A：监控地址清算风险(已有)

**数据来源**：你监控的 Hyperliquid 地址
**覆盖范围**：~5% 市场
**用途**：追踪特定巨鲸的风险暴露
**卡片命名**：`监控地址清算风险`

**字段设计**：

```python
# data/liquidation_risk_monitored.json
{
    "snapshot_time": "2025-01-15T10:30:00Z",
    "total_monitored_value_usd": 352000000,
    "market_coverage_pct": 5.21,
    
    "by_distance": {
        "within_5pct": {
            "count": 0,
            "total_value_usd": 0,
            "positions": []
        },
        "within_10pct": {
            "count": 0,
            "total_value_usd": 0,
            "positions": []
        }
    },
    
    "by_asset": {
        "BTC": {
            "long_at_risk_usd": 0,
            "short_at_risk_usd": 0,
            "nearest_liquidation_pct": 15.2
        }
    }
}
```

**发送规则**：
- **盘中雷达**：任一监控地址进入 5% 清算距离
- **早晚报**：汇总 10% 内地址数量和规模
- **不发送**：全部地址都在 10% 以外

#### 类型B：全市场清算热力图(需新增)

**数据来源**：第三方聚合数据
**覆盖范围**：全市场
**用途**：识别价格可能被清算墙吸引/推动的区域

**推荐数据源优先级**：

1. **Coinglass** (首选)
   - 覆盖：Binance, Bybit, OKX, Bitget 等主流 CEX
   - 更新频率：5-15分钟
   - 可靠性：★★★★☆
   - API：有,但免费版限流
   - 成本：$99-299/月
   - **优点**：数据最全,可视化好
   - **缺点**：不包含 Hyperliquid, dYdX 等去中心化衍生品

2. **Glassnode** (备选)
   - 覆盖：主要 CEX
   - 更新频率：10分钟
   - 可靠性：★★★★★
   - API：有,专业版
   - 成本：$799/月起
   - **优点**：数据质量高,历史数据完整
   - **缺点**：贵,更新频率略慢

3. **自建爬虫** (不推荐)
   - 从各交易所公开清算数据聚合
   - **问题**：
     - 各交易所数据格式不统一
     - 很多交易所不公开清算数据
     - 维护成本高
     - 容易被封IP

**推荐方案**：
- **第一阶段**：接入 Coinglass API,只取 BTC/ETH 的清算热力图
- **第二阶段**：如果验证有效,再扩展到更多资产
- **第三阶段**：考虑补充 Hyperliquid 链上清算数据(如果 Coinglass 不覆盖)

**字段设计**：

```python
# data/liquidation_heatmap_market.json
{
    "snapshot_time": "2025-01-15T10:30:00Z",
    "source": "coinglass",
    "asset": "BTC",
    "current_price": 49500,
    
    "liquidation_clusters": [
        {
            "price_level": 48000,
            "distance_pct": -3.03,
            "side": "long",
            "estimated_volume_usd": 450000000,
            "exchange_breakdown": {
                "binance": 200000000,
                "bybit": 150000000,
                "okx": 100000000
            },
            "density_score": 85  # 0-100, 相对于历史
        },
        {
            "price_level": 51000,
            "distance_pct": 3.03,
            "side": "short",
            "estimated_volume_usd": 320000000,
            "density_score": 62
        }
    ],
    
    "nearest_major_wall": {
        "price": 48000,
        "distance_pct": -3.03,
        "side": "long",
        "volume_usd": 450000000,
        "density_score": 85
    }
}
```

**发送规则**：

```python
def should_send_liquidation_heatmap(data):
    """
    决定是否发送清算热力图卡片
    """
    nearest_wall = data['nearest_major_wall']
    
    # 规则1: 距离当前价格3%内,且规模>2亿美元,且密度分位>80
    if (abs(nearest_wall['distance_pct']) < 3.0 
        and nearest_wall['volume_usd'] > 200_000_000
        and nearest_wall['density_score'] > 80):
        return 'radar'  # 盘中雷达
    
    # 规则2: 距离5%内,且规模>1亿美元,且密度分位>70
    if (abs(nearest_wall['distance_pct']) < 5.0
        and nearest_wall['volume_usd'] > 100_000_000
        and nearest_wall['density_score'] > 70):
        return 'digest'  # 进早晚报
    
    # 规则3: 其他情况不发送
    return 'hidden'
```

### 3.2 清算墙的组合信号

**单独的清算墙数据价值有限,需要和其他信号组合**：

#### 组合1: 清算墙 + 价格逼近

```python
# 场景: 价格正在向清算墙移动
if (price_moving_towards_wall 
    and wall_distance_pct < 5.0
    and price_momentum_1h > 2.0):  # 1小时涨跌幅>2%
    
    urgency = 'immediate'
    message = f"⚠️ {asset} 价格快速逼近 {wall_side} 清算墙"
```

#### 组合2: 清算墙 + 资金费率异常

```python
# 场景: 多头清算墙 + 资金费率极高 → 空头挤压风险
if (wall_side == 'long'
    and funding_rate_percentile > 95
    and wall_distance_pct < 5.0):
    
    urgency = 'immediate'
    message = f"🔥 {asset} 多头清算墙 + 资金费率极高,警惕空头挤压"
```

#### 组合3: 清算墙 + 巨鲸反向加仓

```python
# 场景: 多头清算墙 + 巨鲸加空仓 → 可能故意触发清算
if (wall_side == 'long'
    and whale_position_change_side == 'short'
    and whale_position_change_pct > 20):
    
    urgency = 'immediate'
    message = f"⚡ {asset} 监控巨鲸加空仓,可能瞄准下方多头清算墙"
```

### 3.3 清算墙回测方法

**回测逻辑**：

```python
def backtest_liquidation_wall_signal(historical_data):
    """
    回测清算墙信号的有效性
    """
    results = []
    
    for snapshot in historical_data:
        wall = snapshot['nearest_major_wall']
        current_price = snapshot['current_price']
        wall_price = wall['price']
        
        # 只回测"价格逼近清算墙"的场景
        if abs(wall['distance_pct']) > 5.0:
            continue
        
        # 检查后续价格是否触及清算墙
        future_prices = get_future_prices(snapshot['time'], windows=['15m', '1h', '4h'])
        
        wall_triggered = any(
            (wall['side'] == 'long' and p < wall_price) or
            (wall['side'] == 'short' and p > wall_price)
            for p in future_prices
        )
        
        # 检查触发后是否发生瀑布
        if wall_triggered:
            price_cascade = check_price_cascade(
                snapshot['time'],
                wall['side'],
                threshold=3.0  # 触发后继续单向移动>3%
            )
        else:
            price
