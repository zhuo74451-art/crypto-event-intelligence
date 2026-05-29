# Claude Response

- generated_at: 2026-05-28 22:35:17 UTC+8
- model: anthropic/claude-sonnet-4.5
- prompt: docs\CLAUDE_NEXT_PROMPT.md
- prompt_sha256_16: 4c5b0b0a5b356efe

# Crypto Event Intelligence 项目审查报告

## 一、当前 TG 早午晚报/盘中雷达的 10 个最大真实问题（按优先级）

### P0 级别（立即修复）

**1. 市场状态首屏信息密度过高，普通用户看不懂**
- 问题：7个合约的聚合数据对用户没有意义，"持仓合计147.19亿美元"这个数字用户无法判断是多是少
- 影响：用户打开就懵，直接跳过首屏
- 验收标准：非专业用户能在10秒内理解"今天市场是什么状态"

**2. "焦点资产"选择逻辑不清晰，HYPE 不应该和 BTC/ETH 并列**
- 问题：HYPE 价格-4.16%、持仓+5.40% 对大部分用户没有参考价值，市值和流动性差距太大
- 影响：稀释真正重要的信息（BTC/ETH/主流币）
- 验收标准：焦点资产必须是市值 Top 10 或当日异常幅度超过阈值

**3. 缺少"今天和昨天相比发生了什么变化"的对比视角**
- 问题：只有当前快照，用户不知道"持仓147亿"是比昨天多了还是少了
- 影响：无法判断趋势，只能看到静态数字
- 验收标准：关键指标必须有 24h 变化量和方向

### P1 级别（本周完成）

**4. "多空拥挤"这个术语普通用户不理解**
- 问题："多空拥挤 3 个（SOL;XRP;DOGE）"，用户不知道这意味着什么风险
- 影响：专业术语堆砌，用户无法转化为决策参考
- 验收标准：改为"多头/空头过度集中"并附带一句话解释风险

**5. 缺少"为什么今天要关注这些事件"的优先级说明**
- 问题：早午晚报里事件平铺，用户不知道哪条最重要
- 影响：用户要么全看（累），要么全不看（失去价值）
- 验收标准：每期报告最多 3 条"今日最值得关注"，其余归入"其他动态"

**6. ETF 流入流出数据没有接入日报首屏**
- 问题：你已经有 Farside 历史数据和 90 日分位，但没有出现在市场状态里
- 影响：错过美股时段最重要的资金流向信号
- 验收标准：早报必须包含"昨日 BTC/ETH ETF 净流入及历史分位"

**7. 事件卡片的"强度/置信"字段对用户没有意义**
- 问题："强度 0.65、置信 0.72"，用户不知道 0.65 是高还是低
- 影响：看起来很专业，实际没有传递信息
- 验收标准：改为"高/中/低"三档，或直接去掉

### P2 级别（两周内完成）

**8. 缺少"本周/本月累积视角"**
- 问题：每天看日报，但不知道"这周 ETF 累计流入多少""本月 BTC 持仓变化趋势"
- 影响：用户只能看到碎片，看不到结构
- 验收标准：周日晚报增加"本周市场结构回顾"，月末增加"本月资金流向总结"

**9. 合约持仓变化没有和价格变化做交叉验证**
- 问题："价格下跌但持仓上升"只是描述，没有说明这是看涨信号还是看跌信号
- 影响：用户不知道这个组合意味着什么
- 验收标准：增加"价格-持仓"四象限分类（上涨+增仓/上涨+减仓/下跌+增仓/下跌+减仓）及典型含义

**10. 盘中雷达的"高质量项"标准不透明**
- 问题：用户不知道为什么有些事件进盘中雷达，有些进日报
- 影响：用户对盘中推送的信任度不稳定
- 验收标准：在项目文档和 TG 置顶消息里明确"盘中雷达准入标准"

---

## 二、市场状态首屏具体修改意见

### 当前版本问题诊断

```text
## 市场状态
- 市场概览｜覆盖 7/7 个合约，BTC 24h -2.57%，ETH 24h -3.29%，持仓合计 147.19 亿美元，24h成交 302.87 亿美元。
- 波动最大｜HYPE 24h -4.16%；持仓变化最高 HYPE +5.40%。
- 结构偏离｜资金费率偏离 0 个（-）；多空拥挤 3 个（SOL;XRP;DOGE）。
- 焦点资产｜HYPE：价格 -4.16%，持仓 +5.40%，资金费率 0.0050%；价格下跌但持仓上升；24小时成交额较高
- 焦点资产｜ETH：价格 -3.29%，持仓 +4.02%，资金费率 0.0011%；价格下跌但持仓上升；24小时成交额较高
- 焦点资产｜SOL：价格 -2.81%，持仓 +2.64%，资金费率 -0.0070%；多头账户/仓位拥挤；24小时成交额较高
```

**核心问题：**
1. 信息密度过高，一屏塞了 6 条
2. "覆盖 7/7 个合约"对用户无意义
3. "持仓合计 147.19 亿美元"没有参考系
4. HYPE 不应该作为焦点资产
5. 术语太多（资金费率偏离、多空拥挤）

### 建议修改版本（早报）

```text
## 📊 市场状态（北京时间 08:00）

**主要资产 24h 表现**
• BTC -2.57%，ETH -3.29%，主流币普遍回调

**合约市场结构**
• BTC 合约持仓 +1.2%（续增），资金费率 0.01%（中性）
• ETH 合约持仓 +4.0%（明显增加），资金费率 0.001%（偏低）
• 多头集中度：SOL/XRP/DOGE 多头账户占比超 60%，短期拥挤

**资金流向（美股时段）**
• BTC 现货 ETF 净流入 1.2 亿美元（近 30 日 65 分位，中等偏上）
• ETH 现货 ETF 净流出 0.3 亿美元（近 30 日 40 分位，偏弱）

**今日关注**
价格回调但持仓增加，可能是：①抄底资金入场 ②空头加仓，需观察后续资金费率和现货 ETF 流向
```

### 建议修改版本（午报/晚报）

```text
## 📊 市场状态（北京时间 20:00）

**今日变化**
• BTC -2.57%（持仓 +1.2%），ETH -3.29%（持仓 +4.0%）
• 价格回调但持仓增加，市场分歧加大

**合约结构**
• 资金费率：BTC 0.01%、ETH 0.001%，均处于中性区间
• 多头集中：SOL/XRP/DOGE 多头账户占比超 60%，需警惕集中平仓风险

**24h 资金流**
• BTC 现货 ETF 净流入 1.2 亿美元（近 30 日 65 分位）
• 合约成交额 302 亿美元（较昨日 +5%）

**解读**
价格下跌但持仓和成交量上升，通常意味着市场分歧加大，短期波动可能增加
```

### 具体修改清单

| 当前内容 | 问题 | 修改方案 | 优先级 |
|---------|------|---------|--------|
| "覆盖 7/7 个合约" | 对用户无意义 | **删除** | P0 |
| "持仓合计 147.19 亿美元" | 没有参考系 | 改为"BTC 持仓 +1.2%"（24h 变化） | P0 |
| "波动最大｜HYPE" | 小市值币不应该突出 | 只保留市值 Top 10 或异常幅度 >10% | P0 |
| "资金费率偏离 0 个" | 术语不清晰 | 改为"资金费率：BTC 0.01%（中性）" | P1 |
| "多空拥挤 3 个" | 术语不清晰 | 改为"多头集中：SOL/XRP/DOGE 多头账户占比超 60%，需警惕集中平仓风险" | P1 |
| "焦点资产｜HYPE" | 不应该和 BTC/ETH 并列 | **删除**，或归入"小市值异动" | P0 |
| 缺少 ETF 数据 | 重要信号缺失 | **新增** "BTC/ETH 现货 ETF 净流入及历史分位" | P0 |
| 缺少"今日变化"对比 | 只有快照，没有趋势 | **新增** "较昨日"对比 | P0 |
| "强度 0.65、置信 0.72" | 用户看不懂 | 改为"高/中/低"或删除 | P1 |

---

## 三、下一批 P0/P1/P2 工程任务清单

### P0 任务（本周必须完成）

#### P0-1：重构市场状态首屏输出逻辑

**目标：** 让非专业用户能在 10 秒内理解市场状态

**输入：**
- `data/market/binance_market_snapshot_YYYYMMDD_HH.json`（当前快照）
- `data/market/binance_market_snapshot_YYYYMMDD-1_HH.json`（昨日同时段快照）
- `data/etf/farside_daily_YYYYMMDD.csv`（ETF 流入流出）

**输出：**
- `reports/market_state_summary_YYYYMMDD_HH.md`（新格式首屏）

**脚本：**
- 新增 `scripts/reporting/generate_market_state_summary.py`
- 修改 `scripts/telegram/send_daily_report.py`（调用新脚本）

**核心逻辑：**
1. 只保留 BTC/ETH/SOL/BNB 四个主要资产（市值 Top 5）
2. 所有指标必须有"较昨日"对比（+1.2% / -0.5%）
3. 资金费率/多空比转换为"中性/偏多/偏空/极端"四档
4. ETF 数据必须包含"历史分位"（30日/90日）
5. 增加"今日关注"一句话总结

**验收标准：**
- [ ] 首屏不超过 8 行
- [ ] 所有数字都有"较昨日"对比
- [ ] 术语不超过 2 个，且有解释
- [ ] ETF 数据出现在早报首屏
- [ ] 非专业用户测试：能在 10 秒内说出"今天市场是涨是跌、资金是流入还是流出"

---

#### P0-2：建立"焦点资产"筛选规则

**目标：** 避免 HYPE 这种小市值币污染首屏

**输入：**
- `data/market/binance_market_snapshot_YYYYMMDD_HH.json`
- `config/asset_tiers.yaml`（新增：资产分层配置）

**输出：**
- `data/market/focus_assets_YYYYMMDD_HH.json`

**脚本：**
- 新增 `scripts/market/select_focus_assets.py`
- 新增 `config/asset_tiers.yaml`

**核心逻辑：**
```yaml
# config/asset_tiers.yaml
tier_1:  # 必须出现在首屏
  - BTC
  - ETH
tier_2:  # 市值 Top 10，异常时出现
  - BNB
  - SOL
  - XRP
  - DOGE
  - ADA
tier_3:  # 只有极端异常时出现（24h 波动 >15% 或持仓变化 >20%）
  - HYPE
  - others

focus_rules:
  tier_1: always  # 总是显示
  tier_2: if abs(price_change_24h) > 5% or abs(oi_change_24h) > 10%
  tier_3: if abs(price_change_24h) > 15% or abs(oi_change_24h) > 20%
  max_focus_assets: 4  # 最多显示 4 个焦点资产
```

**验收标准：**
- [ ] BTC/ETH 必须出现
- [ ] HYPE 只有在 24h 波动 >15% 时才出现
- [ ] 焦点资产不超过 4 个
- [ ] 配置文件可以手动调整阈值

---

#### P0-3：ETF 数据接入日报首屏

**目标：** 早报必须包含"昨日 BTC/ETH ETF 净流入及历史分位"

**输入：**
- `data/etf/farside_daily_YYYYMMDD.csv`（已有）
- `data/etf/farside_historical_percentiles.json`（已有）

**输出：**
- `reports/etf_summary_YYYYMMDD.md`

**脚本：**
- 新增 `scripts/reporting/generate_etf_summary.py`
- 修改 `scripts/telegram/send_daily_report.py`

**核心逻辑：**
```python
# 示例输出
"""
**资金流向（美股时段）**
• BTC 现货 ETF 净流入 1.2 亿美元（近 30 日 65 分位，中等偏上）
• ETH 现货 ETF 净流出 0.3 亿美元（近 30 日 40 分位，偏弱）
• 解读：BTC 资金流入处于近期中上水平，ETH 持续流出需关注
"""

def generate_etf_summary(date):
    btc_flow = get_btc_etf_flow(date)
    eth_flow = get_eth_etf_flow(date)
    btc_percentile = get_percentile(btc_flow, window=30)
    eth_percentile = get_percentile(eth_flow, window=30)
    
    btc_label = percentile_to_label(btc_percentile)  # "强劲/中等偏上/中性/偏弱/极弱"
    eth_label = percentile_to_label(eth_percentile)
    
    return format_etf_summary(btc_flow, btc_label, eth_flow, eth_label)
```

**验收标准：**
- [ ] 早报首屏必须包含 ETF 数据
- [ ] 必须有"历史分位"和"强劲/中等/偏弱"标签
- [ ] 如果 ETF 数据缺失（周末/节假日），显示"美股休市，无 ETF 数据"

---

### P1 任务（两周内完成）

#### P1-1：术语白话化改造

**目标：** "多空拥挤"改为"多头集中度过高，需警惕集中平仓风险"

**输入：**
- `data/market/binance_trader_metrics_YYYYMMDD.json`（大户多空比）

**输出：**
- `reports/market_structure_risks_YYYYMMDD.md`

**脚本：**
- 新增 `scripts/reporting/translate_market_terms.py`
- 新增 `config/term_translations.yaml`

**核心逻辑：**
```yaml
# config/term_translations.yaml
terms:
  long_crowding:
    original: "多空拥挤"
    translated: "多头集中度过高"
    explanation: "超过 60% 的大户持有多头仓位，如果价格下跌可能引发集中平仓"
    risk_level: "中"
  
  funding_rate_extreme:
    original: "资金费率偏离"
    translated: "资金费率异常"
    explanation: "多头/空头支付的持仓成本过高，通常预示短期反转"
    risk_level: "高"
  
  oi_price_divergence:
    original: "价格下跌但持仓上升"
    translated: "价格回调但持仓增加"
    explanation: "可能是抄底资金入场，也可能是空头加仓，需观察后续资金费率"
    risk_level: "中"
```

**验收标准：**
- [ ] 所有专业术语都有白话翻译
- [ ] 每个术语都有一句话风险解释
- [ ] 配置文件可以手动调整翻译

---

#### P1-2：增加"今日最值得关注"优先级标记

**目标：** 每期报告最多 3 条"今日最值得关注"，其余归入"其他动态"

**输入：**
- `data/events/candidate_events_YYYYMMDD.json`（候选事件）
- `data/events/event_scores_YYYYMMDD.json`（事件评分）

**输出：**
- `reports/daily_report_YYYYMMDD_prioritized.md`

**脚本：**
- 修改 `scripts/reporting/generate_daily_report.py`
- 新增 `scripts/events/prioritize_events.py`

**核心逻辑：**
```python
def prioritize_events(events, max_top=3):
    """
    优先级规则：
    1. 事件类型：ETF 流入/大额转账/合约清算 > 项目公告/市场数据
    2. 资产重要性：BTC/ETH > 其他
    3. 异常回报：abs(abnormal_return) > 2%
    4. 来源可信度：source_basis >= 0.8
    """
    scored_events = []
    for event in events:
        score = 0
        if event['type'] in ['etf_flow', 'large_transfer', 'liquidation']:
            score += 10
        if event['asset'] in ['BTC', 'ETH']:
            score += 5
        if abs(event.get('abnormal_return', 0)) > 0.02:
            score += 3
        if event.get('source_basis', 0) >= 0.8:
            score += 2
        scored_events.append((score, event))
    
    scored_events.sort(reverse=True)
    top_events = [e for s, e in scored_events[:max_top]]
    other_events = [e for s, e in scored_events[max_top:]]
    
    return top_events, other_events
```

**输出格式：**
```markdown
## 🔥 今日最值得关注

1. **BTC 现货 ETF 单日净流入 5 亿美元，创近 30 日新高**
   - 时间：2025-01-15 美股收盘
   - 解读：机构资金持续流入，近期 BTC 价格可能受支撑
   
2. **某巨鲸地址转出 10,000 BTC 至交易所**
   - 时间：2025-01-15 14:23（北京时间）
   - 解读：大额转入交易所通常意味着潜在抛压，需关注后续价格走势

3. **ETH 合约持仓 24h 增加 15%，但资金费率仍为负**
   - 时间：2025-01-15 20:00（北京时间）
   - 解读：持仓增加但资金费率为负，可能是空头加仓，短期偏空

---

## 📋 其他动态

- Hyperliquid 总持仓突破 30 亿美元（+8%）
- Coinbase 宣布上线某新币（对主流币影响有限）
- ...
```

**验收标准：**
- [ ] 每期报告"今日最值得关注"不超过 3 条
- [ ] 优先级规则可配置
- [ ] "其他动态"折叠显示（TG 支持折叠）

---

#### P1-3：建立"价格-持仓"四象限分类

**目标：** "价格下跌但持仓上升"要说明这是看涨还是看跌信号

**输入：**
- `data/market/binance_market_snapshot_YYYYMMDD_HH.json`

**输出：**
- `data/market/price_oi_quadrant_YYYYMMDD_HH.json`

**脚本：**
- 新增 `scripts/market/classify_price_oi_quadrant.py`

**核心逻辑：**
```python
def classify_price_oi_quadrant(price_change, oi_change, funding_rate):
    """
    四象限分类：
    
    Q1: 价格上涨 + 持仓增加
        - 如果 funding_rate > 0.01%: "多头主导上涨，但需警惕过热"
        - 如果 funding_rate < 0.01%: "健康上涨，多空均衡"
    
    Q2: 价格上涨 + 持仓减少
        - "空头止损/多头获利了结，上涨动能可能减弱"
    
    Q3: 价格下跌 + 持仓减少
        - "多头止损/空头获利了结，下跌动能可能减弱"
    
    Q4: 价格下跌 + 持仓增加
        - 如果 funding_rate > 0: "抄底资金入场，可能是底部信号"
        - 如果 funding_rate < 0: "空头加仓，短期偏空"
    """
    if price_change > 0 and oi_change > 0:
        if funding_rate > 0.01:
            return "Q1_overheated", "多头主导上涨，但资金费率偏高，需警惕过热回调"
        else:
            return "Q1_healthy", "健康上涨，多空相对均衡"
    elif price_change > 0 and oi_change < 0:
        return "Q2", "空头止损或多头获利了结，上涨动能可能减弱"
    elif price_change < 0 and oi_change < 0:
        return "Q3", "多头止损或空头获利了结，下跌动能可能减弱"
    elif price_change < 0 and oi_change > 0:
        if funding_rate > 0:
            return "Q4_bullish", "价格回调但持仓增加，可能是抄底资金入场"
        else:
            return "Q4_bearish", "价格回调且空头加仓（资金费率为负），短期偏空"
    else:
        return "neutral", "价格和持仓变化不明显"
```

**验收标准：**
- [ ] 所有"价格-持仓"组合都有明确分类
- [ ] 每个分类都
