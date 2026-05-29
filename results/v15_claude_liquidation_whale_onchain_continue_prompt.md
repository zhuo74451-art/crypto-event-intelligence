你刚才的回答在“3.3 清算墙回测方法”中途截断了。请从那里继续，不要重复前文。

必须继续覆盖：
1. Hyperliquid 大户仓位 watchlist 如何扩展。
2. 链上一手监控数据源优先级。
3. 如何和现有快讯信息流合并、去重、聚合成资产卡。
4. 用户视角下盘中雷达、单条事件卡、早午晚报、清算墙卡、链上资金流卡如何设计。
5. 历史回测怎么验证这些实时信号。
6. 接下来 7 天具体开发顺序。

以下是你已输出的末尾上下文：

, dYdX 等去中心化衍生品

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

