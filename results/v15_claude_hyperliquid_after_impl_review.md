# Claude Response

- generated_at: 2026-05-29 12:20:52 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_NEXT_PROMPT.md
- prompt_sha256_16: 83a6893dd1d86696

# 直接指出的问题与立即可执行的修改任务

## 一、首屏资金费率"中性 vs 极端分位"矛盾 ⚠️

**问题本质**：你在同一行里既说"中性"又说"98.9%分位极端"，这是自相矛盾的表述。

**立即修改**：
```text
// 错误示范
• 资金费率：BTC 0.0100%（中性）
• 费率异常：BTC 资金费率处于90日 98.9% 分位

// 正确做法：合并成一行，优先历史分位判断
• BTC 资金费率 0.0100%（90日分位 98.9%，多头持仓成本处于历史高位）
• ETH 资金费率 0.0088%（90日分位 89.6%，多头持仓成本偏高）
```

**工程任务**：
1. 删除"中性/偏高/偏低"的绝对值判断逻辑
2. 只保留分位判断：>90% 才出现在首屏
3. 首屏只显示分位 >90% 的币种，<90% 不显示

---

## 二、Hyperliquid 资金费率 0.0007% 的误导性 ⚠️

**问题**：Hyperliquid 的资金费率是 **8小时结算一次**，你直接显示 0.0007% 会让用户以为和 Binance 的 8小时费率（0.01% = 年化 10.95%）可比，但实际：
- Binance 0.01% × 3次/天 = 年化 10.95%
- Hyperliquid 0.0007% × 3次/天 = 年化 0.77%

**立即修改**：
```python
# 在 Hyperliquid 卡片中统一换算成年化
funding_rate_annualized = funding_rate_8h * 3 * 365

# 显示格式
- BTC｜资金费率 0.0007%/8h（年化 0.77%）｜OI 23.00亿
- HYPE｜资金费率 0.0013%/8h（年化 1.42%）｜OI 13.45亿
```

**工程任务**：
- `generate_market_meta_card.py` 新增 `funding_rate_annualized` 列
- 卡片显示改为"年化 X.XX%"，方便跨交易所对比

---

## 三、HYPE 的静态热度不应该反复推送 ✅

**问题**：HYPE 每天都是 OI/成交前三，这是静态事实，不是动态信号。

**立即修改**：
```text
// 删除这种静态排名
成交活跃：
- BTC｜24h成交 25.54 亿美元
- HYPE｜24h成交 9.13 亿美元  // ❌ 删除

// 改为只显示异常变化
持仓异动（24h OI 变化 >5%）：
- HYPE｜OI +6.24%｜当前 13.45 亿美元
- VIRTUAL｜OI +12.3%｜当前 0.82 亿美元

成交异动（24h 成交量变化 >50%）：
- PENGU｜成交量 +87%｜当前 1.2 亿美元
```

**工程任务**：
1. 删除"成交活跃"静态排名
2. 新增"持仓异动"：24h OI 变化 >5% 才显示
3. 新增"成交异动"：24h 成交量变化 >50% 才显示
4. HYPE 只在异动时出现，不再每天刷屏

---

## 四、大户清算距离 <10% 为 0 时不应发独立卡片 ✅

**问题**：当前清算风险为 0，单独发一张卡片说"没有风险"是浪费用户注意力。

**立即修改**：
```python
# 在 generate_hyperliquid_snapshot_card.py 中
def should_send_card(positions):
    """只有满足以下条件之一才发卡片"""
    # 1. 有清算距离 <10% 的仓位
    if any(p['liquidation_distance_pct'] < 10 for p in positions):
        return True
    
    # 2. 监控仓位总规模变化 >10%
    if abs(total_value_change_pct) > 10:
        return True
    
    # 3. 单个大户仓位变化 >20%
    if any(p['position_change_24h_pct'] > 20 for p in positions):
        return True
    
    return False

# 不满足条件时
if not should_send_card(positions):
    # 只输出到 results/hyperliquid_snapshot_card.md
    # 不发 Telegram
    # 在早报中用一行概括："Hyperliquid 大户持仓无异常"
```

**工程任务**：
- 新增 `should_send_card()` 判断逻辑
- 无异常时不发 TG，只在早报中一行带过
- 有异常时才发独立卡片

---

## 五、清算墙 vs 清算热力图的优先级 🎯

**你的问题**：先做已知大户清算墙，还是直接接第三方热力图？

**我的建议**：**先做已知大户清算墙**，原因：

1. **第三方热力图的问题**：
   - Coinglass/Binance 清算地图是 **已发生清算**，不是 **未来清算价**
   - Hyperliquid 没有公开的清算热力图 API
   - 自己爬全市场持仓数据不现实

2. **已知大户清算墙的价值**：
   - 你已经有 5 个地址，总规模 3.52 亿美元（占 Hyperliquid 总持仓 5.2%）
   - 这些大户的清算价是 **确定性风险点**
   - 可以直接计算"价格到 X 会触发 Y 亿美元清算"

**立即可执行的工程任务**：

```python
# scripts/hyperliquid/generate_liquidation_wall.py

def generate_liquidation_wall(positions):
    """
    生成清算墙：按清算价分组，计算每个价格档位的清算规模
    """
    walls = []
    
    for pos in positions:
        walls.append({
            'symbol': pos['symbol'],
            'side': pos['side'],
            'liquidation_price': pos['liquidation_price'],
            'position_value_usd': pos['position_value_usd'],
            'distance_pct': pos['liquidation_distance_pct']
        })
    
    # 按币种分组
    by_symbol = {}
    for w in walls:
        symbol = w['symbol']
        if symbol not in by_symbol:
            by_symbol[symbol] = {'long': [], 'short': []}
        by_symbol[symbol][w['side']].append(w)
    
    # 生成卡片
    output = []
    for symbol, sides in by_symbol.items():
        current_price = get_current_price(symbol)
        
        # 多头清算墙（价格下跌触发）
        long_walls = sorted(sides['long'], key=lambda x: x['liquidation_price'], reverse=True)
        if long_walls:
            output.append(f"\n{symbol} 多头清算墙（价格下跌触发）：")
            for w in long_walls[:3]:  # 只显示最近的3个
                output.append(
                    f"  ${w['liquidation_price']:.2f}（-{w['distance_pct']:.1f}%）"
                    f"｜{w['position_value_usd']/1e6:.1f}M"
                )
        
        # 空头清算墙（价格上涨触发）
        short_walls = sorted(sides['short'], key=lambda x: x['liquidation_price'])
        if short_walls:
            output.append(f"\n{symbol} 空头清算墙（价格上涨触发）：")
            for w in short_walls[:3]:
                output.append(
                    f"  ${w['liquidation_price']:.2f}（+{w['distance_pct']:.1f}%）"
                    f"｜{w['position_value_usd']/1e6:.1f}M"
                )
    
    return "\n".join(output)
```

**输出示例**：
```text
BTC 多头清算墙（价格下跌触发）：
  $92,341（-7.8%）｜80.0M｜Matrixport Related
  $89,120（-10.9%）｜45.2M｜Unknown Whale

HYPE 空头清算墙（价格上涨触发）：
  $28.50（+49.8%）｜106.0M｜loraclexyz
  $32.10（+68.7%）｜23.5M｜Unknown Whale
```

**触发逻辑**：
- 价格距离任一清算墙 <5%：发盘中雷达
- 价格距离任一清算墙 <10%：进入早晚报"持仓结构风险"
- 价格距离所有清算墙 >10%：不显示

---

## 六、1h OI velocity 的优先级 ⚠️

**你的问题**：是否需要自己积累 1h OI 变化？

**我的建议**：**暂时不做**，原因：

1. **Hyperliquid API 限制**：
   - `metaAndAssetCtxs` 没有历史数据
   - 你需要每小时跑一次快照，积累至少 24 小时才能算 1h velocity
   - 这需要 1 天冷启动时间

2. **当前已有的 24h OI 变化已经够用**：
   - HYPE +6.24% 已经是明显信号
   - 1h OI 变化的噪音更大，容易误报

3. **更优先的任务**：
   - 先把清算墙做出来（上面第五点）
   - 先把资金费率年化换算做对（上面第二点）

**如果一定要做 1h OI velocity**，工程任务：
```bash
# 1. 新增定时任务（每小时运行）
# crontab
0 * * * * /path/to/fetch_hyperliquid_oi_snapshot.py

# 2. 积累历史数据
# data/hyperliquid/oi_snapshots/2025-05-27_14-00.csv
# data/hyperliquid/oi_snapshots/2025-05-27_15-00.csv

# 3. 计算 1h velocity
oi_velocity_1h = (oi_current - oi_1h_ago) / oi_1h_ago * 100

# 4. 触发条件
if abs(oi_velocity_1h) > 3%:  # 1小时 OI 变化 >3%
    send_alert()
```

**但我建议先不做**，等清算墙上线后再评估是否需要。

---

## 七、TG 卡片继续删减建议 ✂️

**当前问题**：早晚报仍然太长，用户需要滑动 2-3 屏才能看完。

**立即删除的段落**：

### 1. 删除"其他动态"整个段落
```text
## 其他动态  // ❌ 整段删除
- 无
```
**原因**：90% 的时候都是"无"，浪费空间。有内容时直接合并到"事件关注"。

### 2. 删除"日频背景"中的静态信息
```text
## 日频背景
- 24h 涨幅 Top3：PENGU +15.2%, VIRTUAL +12.3%, AI16Z +8.9%  // ❌ 删除
- 24h 跌幅 Top3：MOVE -8.2%, APT -6.5%, SUI -5.1%  // ❌ 删除
- 24h 成交量 Top3：BTC 25.5B, ETH 8.1B, SOL 3.2B  // ❌ 删除

// 只保留异常信息
- BTC 现货 ETF 净流出 -7.33 亿美元（90日分位 98.9%）  // ✅ 保留
- ETH 持仓量 24h -1.74%（90日分位 5.2%）  // ✅ 保留
```

### 3. 合并"市场状态"和"价格与费率异常"
```text
// 当前
## 市场状态
• BTC +0.03%（持仓 +3.12%），ETH +0.77%（持仓 -1.74%）
• BTC 资金费率 0.0100%（90日分位 98.9%）

## 价格与费率异常
- BTC｜资金费率分位 98.9%｜1h -0.09%｜24h +0.03%

// 改为
## 市场异常
- BTC｜资金费率 90日分位 98.9%（多头持仓成本历史高位）｜24h +0.03%｜持仓 +3.12%
- ETH｜持仓量 90日分位 5.2%（持仓量异常低）｜24h +0.77%｜持仓 -1.74%
- BTC ETF｜净流出 -7.33亿（90日分位 98.9%）
```

**最终早报结构**：
```text
## 市场异常（只显示分位 >90% 或 <10% 的）
- ...

## 持仓结构风险（只显示极端 Top2）
- ...

## 事件关注（有内容才显示）
- ...

## 结构信号（只显示极端 Top2）
- ...
```

**预期效果**：从当前 40-50 行压缩到 20-25 行，用户一屏看完。

---

## 八、Hyperliquid 盘中雷达的组合逻辑 🎯

**你的核心问题**：清算地图/大户持仓/资金费率/OI 速度如何组合成真正有用的盘中雷达？

**我的建议**：**分层触发，优先级明确**

### 第一优先级：清算风险（立即触发）
```python
# 触发条件
if liquidation_distance < 5%:
    send_alert("🚨 清算风险")
    
# 卡片内容
"""
🚨 BTC 大户清算风险

Matrixport Related 多头仓位 8000万美元
清算价：$92,341（当前价格 -4.2%）

若 BTC 跌破 $92,341：
- 触发 8000万美元多头清算
- 可能引发连锁清算
"""
```

### 第二优先级：持仓结构异常（每小时检查）
```python
# 触发条件
if oi_change_1h > 5% or funding_rate_percentile > 95:
    send_alert("⚠️ 持仓异常")

# 卡片内容
"""
⚠️ HYPE 持仓异常

1h OI +8.2%（当前 13.45亿美元）
资金费率 0.0013%/8h（年化 1.42%，90日分位 92%）

大户动向：
- loraclexyz 空头 +1200万美元
- Unknown Whale 多头 +800万美元
"""
```

### 第三优先级：价格异动（每 15 分钟检查）
```python
# 触发条件
if price_change_15m > 2% and volume_change_15m > 50%:
    send_alert("📊 价格异动")

# 卡片内容
"""
📊 BTC 价格异动

15分钟 +2.3%（成交量 +87%）

关联风险：
- 距离 Matrixport 多头清算价 -6.5%
- 资金费率 90日分位 98.9%（多头成本高）
"""
```

**工程任务**：
```python
# scripts/hyperliquid/intraday_radar.py

def check_liquidation_risk():
    """每 5 分钟检查一次"""
    pass

def check_position_anomaly():
    """每 1 小时检查一次"""
    pass

def check_price_movement():
    """每 15 分钟检查一次"""
    pass

# 主循环
while True:
    if minute % 5 == 0:
        check_liquidation_risk()
    if minute == 0:
        check_position_anomaly()
    if minute % 15 == 0:
        check_price_movement()
    
    time.sleep(60)
```

---

## 立即可执行的任务清单（按优先级排序）

### P0（本周完成）
1. ✅ 修复首屏资金费率"中性 vs 极端分位"矛盾（第一点）
2. ✅ Hyperliquid 资金费率改为年化显示（第二点）
3. ✅ 删除 HYPE 静态排名，改为异动触发（第三点）
4. ✅ 大户清算距离无异常时不发独立卡片（第四点）

### P1（下周完成）
5. ✅ 实现已知大户清算墙（第五点）
6. ✅ 早晚报删减至一屏（第七点）
7. ✅ 实现清算风险盘中雷达（第八点第一优先级）

### P2（两周后）
8. ⏸️ 实现持仓异常盘中雷达（第八点第二优先级）
9. ⏸️ 实现价格异动盘中雷达（第八点第三优先级）
10. ⏸️ 评估是否需要 1h OI velocity（第六点）

---

**最后一个建议**：你现在的问题不是功能不够，而是 **信息过载**。用户每天收到 3-4 张卡片，每张 40-50 行，根本看不过来。**先做减法，再做加法**。把当前的早晚报压缩到一屏，把 Hyperliquid 卡片改为异常触发，然后再考虑新增盘中雷达。
