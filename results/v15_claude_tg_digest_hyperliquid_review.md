# Claude Response

- generated_at: 2026-05-29 12:09:56 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_NEXT_PROMPT.md
- prompt_sha256_16: 4975a77292a159ff

# 直接评审与改版方案

## 一、当前问题直接判断

### 1. "今日最值得关注"层级混乱 ✓ 确认
**问题**：SOL/XRP 的负费率分位 + DOGE 的市场结构项混在一起，用户无法快速区分"价格异常"和"结构风险"。

**立刻改**：
- 拆成两个独立区块：
  - **价格与费率异常**（funding 极端 + 价格确认）
  - **持仓结构风险**（长短比集中、清算风险）
- 每个区块最多 3 条，超过进背景。

---

### 2. 负费率表达 ✓ 需要统一口径
**当前问题**：
- "空头拥挤仍在延续" vs "空头成本偏高" 混用
- 用户看不懂"拥挤"和"成本"的区别

**统一为**：
```
负费率高分位（90.7%）+ 价格下跌 → "空头持仓成本偏高，若反弹可能触发空头平仓"
负费率高分位 + 价格上涨 → "空头持仓成本偏高且价格反向，空头可能被迫平仓"
```
**删除**："拥挤"这个模糊词，改用"成本 + 方向 + 可能后果"。

---

### 3. 长短账户比列 5 个 ✗ 不可读
**立刻删减**：
- 只保留 **Top 2 最极端**（大户多空比 > 2.0 或 < 0.5）
- 其余进"背景-市场结构"，不要在首屏/关注区重复

---

### 4. ETF 首屏重复 ✓ 确认冗余
**当前**：
```
• 今日市场异常：BTC ETF 净流出 7.33 亿美元；ETF 资金流达到90日极端分位 98.9%。
• BTC 现货 ETF：27 May 2026 净流 -7.33 亿美元（90日分位 98.9%，极端）
```
**合并为一行**：
```
• BTC 现货 ETF 净流出 7.33 亿美元（90日分位 98.9%，极端流出）
```
删除"今日市场异常"这个泛化标签，直接说事实。

---

### 5. 1h 价格变化 ✓ 必须补
**当前卡点**：盘中雷达无法触发"funding ≥95 + 1h 跌幅 >2%"。

**优先级 P0**：
- 补 1h 价格变化（Binance Kline 1h）
- 补 1h 成交量变化（用于确认异常是否有成交支撑）
- 1h OI 变化可以暂缓（4h OI 已有）

---

### 6. CEX 净流入基线 ✗ 样本不足，暂时隐藏
**当前问题**：样本少 + 基线不稳定 = 误报率高。

**立刻做**：
- 从早晚报首屏删除
- 保留在"背景-链上与交易所"，标注"样本积累中，仅供参考"
- 等样本 ≥30 天后再评估是否提到关注区

---

### 7. Hyperliquid 静态大仓位 ✓ 重复且无用
**当前问题**：每次报同一批大仓位，用户无法判断"这是新的还是老的"。

**立刻改**：
- 静态大仓位只在早报出现一次（"当前市场大仓位背景"）
- 盘中雷达只报：
  - 新增大仓位（24h 内新开）
  - 仓位变化 >20%
  - 接近清算（距离清算价 <5%）
  - 已清算事件

---

### 8. LLM 编辑 ✗ 现在不需要
**原因**：
- 当前卡片已经是结构化规则生成，逻辑清晰
- LLM 容易改事实、加主观判断、降低可信度
- 如果未来需要，只能用于：
  - 去重（同一资产多条信号合并）
  - 压缩（超长背景裁剪）
  - 中文流畅性（被动语态 → 主动语态）

**现在不做**，等卡片稳定后再评估。

---

## 二、Hyperliquid 一手结构情报接入方案

### 核心判断
Hyperliquid 的价值在于：
1. **高杠杆 + 低流动性** → 清算连锁反应比 CEX 更剧烈
2. **链上透明** → 可以追踪真实大户地址，不依赖 CEX 的"大户账户比"（可能被做市商污染）
3. **资金费率更极端** → 小市场容易出现单边拥挤

但风险在于：
- 清算热力图多为估算（基于公开仓位 + 假设杠杆分布）
- 官方 API 只能查指定地址，无法直接拿"全市场清算地图"
- 第三方数据源质量参差不齐

---

### 接入优先级与实现路径

#### P0：官方 API 基础数据（立刻做）
| 数据 | API | 用途 | 雷达/早晚报 |
|------|-----|------|-------------|
| 资金费率 | `metaAndAssetCtxs` | 计算历史分位，识别极端费率 | 盘中雷达（≥95 分位） + 早晚报背景 |
| OI 变化 | `metaAndAssetCtxs` | 4h/24h OI 变化分位 | 盘中雷达（OI 突增 + 价格确认） |
| 标记价格 | `metaAndAssetCtxs` | 1h/4h 价格变化 | 盘中雷达（价格 + funding 组合） |
| 24h 成交量 | `metaAndAssetCtxs` | 成交量分位，确认异常有效性 | 早晚报背景 |

**实现**：
```python
# scripts/hyperliquid/fetch_market_meta.py
def fetch_hl_market_meta():
    # 拿所有永续合约的 funding/OI/price/volume
    # 存入 data/hyperliquid/market_meta_{timestamp}.json
    # 计算 90 日历史分位（funding 8h 一个点，OI 4h 一个点）
```

**雷达触发规则**：
```python
# 盘中雷达：Hyperliquid 资金费率极端
if funding_percentile >= 95 and abs(price_change_1h) > 1.5:
    alert = f"{symbol}｜HL 资金费率 {funding:.4f}%（{funding_percentile:.1f}分位）｜1h {price_change_1h:+.2f}%｜{'多头' if funding > 0 else '空头'}成本偏高"
```

---

#### P1：追踪已知大户地址（2 周内完成）
**数据源**：
- 手动收集：Hyperliquid 排行榜前 50 地址
- 第三方：Hyblock Capital / Kiyotaka 公开的"鲸鱼地址"
- 自己积累：从历史大额成交/清算事件提取

**追踪内容**：
| 字段 | API | 用途 |
|------|-----|------|
| 账户净值 | `clearinghouseState` | 识别大户资金变化 |
| 持仓明细 | `clearinghouseState.assetPositions` | 追踪大户做多/做空哪些币 |
| 清算价 | 计算：`accountValue / (1 - 1/leverage)` | 估算大户清算风险 |
| 未实现盈亏 | `clearinghouseState.marginSummary.unrealizedPnl` | 判断大户是否浮亏 |

**雷达触发规则**：
```python
# 盘中雷达：大户接近清算
if abs(mark_price - liquidation_price) / mark_price < 0.05:
    alert = f"{symbol}｜大户地址 {address[:6]}... 持仓 {position_size} 接近清算（清算价 {liq_price}，当前 {mark_price}）"

# 盘中雷达：大户新开大仓
if position_change_24h > 1_000_000:  # 100 万美元
    alert = f"{symbol}｜大户地址 {address[:6]}... 24h 新增 {position_change_24h/1e6:.1f}M 美元{'多头' if position > 0 else '空头'}仓位"
```

**早晚报**：
- 汇总前 10 大户的总持仓方向（多头 vs 空头）
- 标注"Hyperliquid 大户净多头 3.2M 美元（追踪 50 个地址）"

---

#### P2：历史清算事件（1 个月内完成）
**数据源**：
- 官方 API 无直接清算历史接口
- 需要自己监听：
  - `userFills` 中 `closedPnl` 为负且仓位归零 → 可能是清算
  - 或接第三方：The Graph Hyperliquid subgraph（有 `Liquidation` 事件）

**用途**：
- 统计过去 24h 清算总金额
- 识别"清算潮"（1h 内清算 >10 笔且总金额 >500 万美元）

**雷达触发规则**：
```python
# 盘中雷达：清算潮
if liquidation_count_1h > 10 and liquidation_volume_1h > 5_000_000:
    alert = f"Hyperliquid 1h 内发生 {liquidation_count_1h} 笔清算，总金额 {liquidation_volume_1h/1e6:.1f}M 美元，主要集中在 {top_symbol}"
```

---

#### P3：清算热力图（第三方数据，3 个月内评估）
**问题**：
- 清算热力图是估算（基于公开仓位 + 假设杠杆分布），不是真实订单簿
- 不同平台算法不同，可能差异很大

**如果接入，优先选择**：
1. **Hyblock Capital**（有 API，数据更新快）
2. **Coinglass**（覆盖多平台，但 Hyperliquid 数据可能不全）

**接入字段**：
- `liquidation_clusters`：清算密集价格区间
- `long_liquidation_threshold` / `short_liquidation_threshold`：多空清算分界线
- `estimated_liquidation_volume`：估算清算量

**表达可信度**：
```python
alert = f"{symbol}｜清算密集区 {cluster_price}（估算，基于公开仓位分布）｜若价格触及，可能触发 {estimated_volume/1e6:.1f}M 美元清算"
```
**必须标注"估算"**，不能说"将会清算"。

---

### 与现有数据结合的卡片示例

#### 场景 1：Hyperliquid 资金费率极端 + CEX 持仓增加
```
• SOL｜HL 资金费率 -0.05%（95.2 分位，空头成本偏高）｜Binance 持仓 24h +8.3%｜1h -2.1%
  → 解读：Hyperliquid 空头拥挤，CEX 持仓同步增加，若价格反弹可能触发 HL 空头平仓 + CEX 多头止损共振
```

#### 场景 2：大户接近清算 + 价格接近清算密集区
```
• ETH｜大户地址 0x1a2b... 持 500 ETH 多头，清算价 $2,850（当前 $2,920，距离 2.4%）｜清算密集区 $2,840-$2,860（估算）
  → 解读：若价格跌破 $2,860，可能触发大户清算 + 连锁清算，需关注成交量放大
```

#### 场景 3：Hyperliquid OI 突增 + CEX 资金费率中性
```
• DOGE｜HL 持仓 24h +45%｜Binance 资金费率 0.01%（中性）｜价格 24h +3.2%
  → 解读：Hyperliquid 新增大量多头，但 CEX 费率未跟随，可能是 HL 独立行情或套利，需确认 CEX 是否跟随
```

---

## 三、立刻删/改/补的具体操作

### 立刻删除
1. ❌ 首屏"今日市场异常"标签（冗余，直接说 ETF 净流）
2. ❌ 长短账户比超过 Top 2 的资产（移到背景）
3. ❌ CEX 净流入基线（样本不足，移到背景标注"积累中"）
4. ❌ Hyperliquid 静态大仓位重复报送（只保留早报一次）

### 立刻合并
1. ✅ ETF 两行合并为一行
2. ✅ "今日最值得关注"拆成"价格与费率异常"+"持仓结构风险"两个区块

### 立刻补充
1. ✅ 1h 价格变化（Binance Kline 1h）
2. ✅ 1h 成交量变化（用于确认异常有效性）
3. ✅ Hyperliquid 资金费率历史分位（90 日，8h 一个点）
4. ✅ Hyperliquid OI 变化分位（90 日，4h 一个点）

### 立刻统一口径
1. ✅ 负费率表达：统一为"空头持仓成本偏高 + 方向 + 可能后果"
2. ✅ 删除"拥挤"改为"成本偏高"
3. ✅ 清算热力图必须标注"估算"

---

## 四、下一批工程任务（按优先级排序）

### P0（本周完成）
1. **补 1h 价格变化**
   - `scripts/binance/fetch_kline_1h.py`
   - 存入 `data/binance/kline_1h_{symbol}_{date}.json`
   - 计算 1h 涨跌幅

2. **补 1h 成交量变化**
   - 从 Kline 1h 提取 volume
   - 计算 1h 成交量 vs 24h 平均成交量比值

3. **Hyperliquid 资金费率接入**
   - `scripts/hyperliquid/fetch_market_meta.py`
   - 计算 90 日历史分位
   - 生成盘中雷达触发规则

4. **Hyperliquid OI 变化接入**
   - 从 `metaAndAssetCtxs` 提取 `openInterest`
   - 计算 4h/24h 变化分位

5. **拆分"今日最值得关注"为两个区块**
   - `scripts/market/generate_watchlist.py`
   - 输出 `price_funding_alerts` 和 `structure_risk_alerts`

---

### P1（2 周内完成）
6. **Hyperliquid 大户地址追踪**
   - 手动收集前 50 地址
   - `scripts/hyperliquid/fetch_whale_positions.py`
   - 存入 `data/hyperliquid/whale_positions_{timestamp}.json`

7. **大户清算价计算**
   - 从 `clearinghouseState` 提取 `accountValue` 和 `assetPositions`
   - 估算清算价（需要假设杠杆，可以用 `marginUsed / accountValue` 反推）

8. **盘中雷达：大户接近清算**
   - 触发条件：`abs(mark_price - liq_price) / mark_price < 0.05`
   - 输出：地址前 6 位 + 仓位 + 清算价

---

### P2（1 个月内完成）
9. **Hyperliquid 历史清算事件**
   - 接 The Graph Hyperliquid subgraph 或自己解析 `userFills`
   - 统计 24h 清算总金额和笔数

10. **清算潮雷达**
    - 触发条件：1h 内清算 >10 笔且总金额 >500 万美元
    - 输出：清算笔数 + 总金额 + 主要币种

---

### P3（3 个月内评估）
11. **接入第三方清算热力图**
    - 优先 Hyblock Capital API
    - 提取 `liquidation_clusters` 和 `estimated_liquidation_volume`
    - **必须标注"估算"**

12. **Hyperliquid 与 CEX 数据联动卡片**
    - 场景：HL 资金费率极端 + CEX 持仓增加
    - 场景：HL OI 突增 + CEX 费率中性
    - 场景：大户接近清算 + 清算密集区

---

## 五、最终判断

### 当前系统最大问题
1. **首屏信息密度过高**：ETF 重复、长短比列太多、异常标签泛化
2. **缺少 1h 数据**：无法做盘中快速确认
3. **Hyperliquid 数据缺失**：错过高杠杆市场的一手结构情报

### 下一阶段目标
1. **首屏只放 3-5 条真正异常**（ETF 极端 + 主流币价格 + 资金费率极端）
2. **关注区拆成价格异常和结构风险两个区块**
3. **补齐 1h 数据 + Hyperliquid 基础数据**
4. **2 周内上线大户追踪，1 个月内上线清算事件监控**

### 不要做的事
1. ❌ 不要用 LLM 改写卡片（现在逻辑已经够清晰）
2. ❌ 不要把清算热力图当作"真实清算订单"
3. ❌ 不要在首屏放超过 5 条信息
4. ❌ 不要把 CEX 净流入基线提前到首屏（样本不足）

---

**总结**：立刻删首屏冗余、补 1h 数据、接 Hyperliquid 基础 API，2 周内上线大户追踪。清算热力图 3 个月后再评估，现在不要碰。
